/**
 * @file vm_test.c
 * @brief Host-side test harness for the Parakram bytecode VM.
 *
 * Compiles with gcc on x86 — no ESP-IDF required.
 * Tests the actual VM execution engine with mock drivers.
 *
 * Build: gcc -o vm_test vm_test.c mock_subsystems.c ../main/runtime/vm.c \
 *        -I. -I../main/include -DHOST_TEST -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "esp_mock.h"
#include "system_config.h"
#include "vm.h"
#include "state_store.h"
#include "driver_registry.h"
#include "event_bus.h"
#include "safety.h"

/* Defined in mock_subsystems.c */
extern void mock_register_default_drivers(void);

/* Helper: Build a single 8-byte instruction */
static void emit_instr(uint8_t *buf, int idx, uint8_t opcode, uint8_t a, uint8_t b,
                        uint8_t r, uint32_t imm) {
    uint8_t *p = &buf[idx * SYS_INSTRUCTION_SIZE];
    p[0] = opcode;
    p[1] = a;
    p[2] = b;
    p[3] = r;
    p[4] = (uint8_t)(imm & 0xFF);
    p[5] = (uint8_t)((imm >> 8) & 0xFF);
    p[6] = (uint8_t)((imm >> 16) & 0xFF);
    p[7] = (uint8_t)((imm >> 24) & 0xFF);
}

static void emit_float(uint8_t *buf, int idx, uint8_t opcode, uint8_t a, uint8_t b,
                        uint8_t r, float fval) {
    uint32_t imm;
    memcpy(&imm, &fval, sizeof(imm));
    emit_instr(buf, idx, opcode, a, b, r, imm);
}

/* ============================================================
 * Test 1: Integer arithmetic
 *   LOAD_IMM_I 10; LOAD_IMM_I 20; ADD_I; STORE_VAR 0; HALT
 * ============================================================ */
static int test_integer_arithmetic(void) {
    printf("\n=== TEST 1: Integer Arithmetic (10 + 20 = 30) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_instr(program, 0, OP_LOAD_IMM_I, 0, 0, 0, 10);
    emit_instr(program, 1, OP_LOAD_IMM_I, 0, 0, 0, 20);
    emit_instr(program, 2, OP_ADD_I, 0, 0, 0, 0);
    emit_instr(program, 3, OP_STORE_VAR, 0, 0, 0, 0);
    emit_instr(program, 4, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {1};
    vm_load_program(program, 5, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t result;
    state_store_get(0, &result);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Result: %d (expected 30)\n", result.i);
    printf("  Instructions executed: %u\n", ctx.instructions_executed);

    int pass = (status == VM_HALTED && result.i == 30);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 2: Float arithmetic
 *   LOAD_IMM_F 3.14; LOAD_IMM_F 2.0; MUL_F; STORE_VAR 1; HALT
 * ============================================================ */
static int test_float_arithmetic(void) {
    printf("\n=== TEST 2: Float Arithmetic (3.14 * 2.0 = 6.28) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_float(program, 0, OP_LOAD_IMM_F, 0, 0, 0, 3.14f);
    emit_float(program, 1, OP_LOAD_IMM_F, 0, 0, 0, 2.0f);
    emit_instr(program, 2, OP_MUL_F, 0, 0, 0, 0);
    emit_instr(program, 3, OP_STORE_VAR, 1, 0, 0, 0);
    emit_instr(program, 4, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {2};
    vm_load_program(program, 5, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t result;
    state_store_get(1, &result);

    float expected = 3.14f * 2.0f;
    float diff = fabsf(result.f - expected);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Result: %.4f (expected %.4f, diff=%.6f)\n", result.f, expected, diff);

    int pass = (status == VM_HALTED && diff < 0.001f);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 3: Conditional branching
 *   LOAD_IMM_I 50; LOAD_IMM_I 30; CMP_GT; JMP_IF 5; LOAD_IMM_I -1; HALT; LOAD_IMM_I 1; STORE_VAR 2; HALT
 *   Should jump to instruction 6 (since 50 > 30 is true), store 1
 * ============================================================ */
static int test_conditional_branching(void) {
    printf("\n=== TEST 3: Conditional Branch (50 > 30 → store 1) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_instr(program, 0, OP_LOAD_IMM_I, 0, 0, 0, 50);
    emit_instr(program, 1, OP_LOAD_IMM_I, 0, 0, 0, 30);
    emit_instr(program, 2, OP_CMP_GT, 0, 0, 0, 0);
    emit_instr(program, 3, OP_JMP_IF, 0, 0, 0, 6);  /* Jump to instr 6 if true */
    emit_instr(program, 4, OP_LOAD_IMM_I, 0, 0, 0, (uint32_t)-1);  /* fallthrough: -1 */
    emit_instr(program, 5, OP_HALT, 0, 0, 0, 0);
    emit_instr(program, 6, OP_LOAD_IMM_I, 0, 0, 0, 1);   /* jump target: 1 */
    emit_instr(program, 7, OP_STORE_VAR, 2, 0, 0, 0);
    emit_instr(program, 8, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {3};
    vm_load_program(program, 9, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t result;
    state_store_get(2, &result);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Result: %d (expected 1)\n", result.i);

    int pass = (status == VM_HALTED && result.i == 1);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 4: Driver read (mock sensor)
 *   DRV_READ driver=0 cap=TEMPERATURE; STORE_VAR 3; HALT
 * ============================================================ */
static int test_driver_read(void) {
    printf("\n=== TEST 4: Driver Read (mock BME280 temperature) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_instr(program, 0, OP_DRV_READ, 0, CAP_TEMPERATURE, 0, 0);
    emit_instr(program, 1, OP_STORE_VAR, 3, 0, 0, 0);
    emit_instr(program, 2, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {4};
    vm_load_program(program, 3, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t result;
    state_store_get(3, &result);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Temperature: %.2f (expected 24.5)\n", result.f);

    int pass = (status == VM_HALTED && fabsf(result.f - 24.5f) < 0.01f);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 5: Driver write (mock actuator)
 *   LOAD_IMM_I 1; DRV_WRITE driver=1; HALT
 * ============================================================ */
static int test_driver_write(void) {
    printf("\n=== TEST 5: Driver Write (mock relay ON) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_instr(program, 0, OP_LOAD_IMM_I, 0, 0, 0, 1);
    emit_instr(program, 1, OP_DRV_WRITE, 1, 0, 0, 0);
    emit_instr(program, 2, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {5};
    vm_load_program(program, 3, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    printf("  Status: %d (expected HALTED=2)\n", status);

    int pass = (status == VM_HALTED);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 6: Smart Planter Pipeline
 *   DRV_READ soil_sensor cap=SOIL_MOISTURE
 *   DUP
 *   LOAD_IMM_F 35.0        (threshold)
 *   CMP_LT                 (moisture < 35.0?)
 *   JMP_IFNOT 9            (skip watering if soil is moist)
 *   LOAD_IMM_I 1
 *   DRV_WRITE relay         (turn on pump)
 *   STORE_VAR 5             (save moisture reading)
 *   HALT
 *   POP                     (discard moisture from stack)
 *   STORE_VAR 5
 *   HALT
 * ============================================================ */
static int test_smart_planter_pipeline(void) {
    printf("\n=== TEST 6: Smart Planter Pipeline (soil=45%%, threshold=35%%) ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    /* Read soil moisture from driver 2 */
    emit_instr(program, 0, OP_DRV_READ, 2, CAP_SOIL_MOISTURE, 0, 0);
    emit_instr(program, 1, OP_DUP, 0, 0, 0, 0);
    emit_float(program, 2, OP_LOAD_IMM_F, 0, 0, 0, 35.0f);
    emit_instr(program, 3, OP_CMP_LT, 0, 0, 0, 0);
    emit_instr(program, 4, OP_JMP_IFNOT, 0, 0, 0, 8);  /* skip watering */
    /* Watering path */
    emit_instr(program, 5, OP_LOAD_IMM_I, 0, 0, 0, 1);
    emit_instr(program, 6, OP_DRV_WRITE, 1, 0, 0, 0);  /* relay ON */
    emit_instr(program, 7, OP_STORE_VAR, 5, 0, 0, 0);
    /* Not reached in this test since 45 > 35 */
    /* Dry path (no watering needed) */
    emit_instr(program, 8, OP_STORE_VAR, 5, 0, 0, 0);
    emit_instr(program, 9, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {6};
    vm_load_program(program, 10, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t moisture;
    state_store_get(5, &moisture);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Stored moisture: %.2f (expected 45.0)\n", moisture.f);
    printf("  Pump should NOT fire (moisture 45%% > threshold 35%%)\n");

    /* 45 > 35, so JMP_IFNOT should take the skip path, no DRV_WRITE to relay */
    int pass = (status == VM_HALTED && fabsf(moisture.f - 45.0f) < 0.01f);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 7: Stack overflow protection
 *   Push 20 values onto a stack of depth 16 → should error
 * ============================================================ */
static int test_stack_overflow(void) {
    printf("\n=== TEST 7: Stack Overflow Protection ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    /* Push 20 integers — stack is only 16 deep */
    for (int i = 0; i < 20; i++) {
        emit_instr(program, i, OP_LOAD_IMM_I, 0, 0, 0, i);
    }
    emit_instr(program, 20, OP_HALT, 0, 0, 0, 0);

    uint8_t prog_id[16] = {7};
    vm_load_program(program, 21, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    printf("  Status: %d (expected ERROR=3)\n", status);

    int pass = (status == VM_ERROR);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Test 8: Pipeline markers
 *   PIPELINE_START id=0, num=3, max_ms=1000
 *   LOAD_IMM_I 42; STORE_VAR 8
 *   PIPELINE_END
 * ============================================================ */
static int test_pipeline_markers(void) {
    printf("\n=== TEST 8: Pipeline Start/End Markers ===\n");

    uint8_t program[SYS_MAX_INSTRUCTIONS * SYS_INSTRUCTION_SIZE];
    memset(program, 0, sizeof(program));

    emit_instr(program, 0, OP_PIPELINE_START, 0, 3, 0, 1000);
    emit_instr(program, 1, OP_LOAD_IMM_I, 0, 0, 0, 42);
    emit_instr(program, 2, OP_STORE_VAR, 8, 0, 0, 0);
    emit_instr(program, 3, OP_PIPELINE_END, 0, 0, 0, 0);

    uint8_t prog_id[16] = {8};
    vm_load_program(program, 4, NULL, 0, prog_id);

    vm_context_t ctx = {0};
    ctx.sp = -1;
    ctx.max_execution_ms = 5000;
    vm_status_t status = vm_execute(&ctx, 5000);

    vm_value_t result;
    state_store_get(8, &result);

    printf("  Status: %d (expected HALTED=2)\n", status);
    printf("  Pipeline ID: %d (expected 0)\n", ctx.pipeline_id);
    printf("  Var[8]: %d (expected 42)\n", result.i);

    int pass = (status == VM_HALTED && ctx.pipeline_id == 0 && result.i == 42);
    printf("  %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

/* ============================================================
 * Main
 * ============================================================ */
int main(void) {
    printf("╔══════════════════════════════════════════╗\n");
    printf("║  Parakram VM Test Harness (Host x86)     ║\n");
    printf("║  Testing actual firmware VM on desktop    ║\n");
    printf("╚══════════════════════════════════════════╝\n");

    /* Initialize subsystems */
    fault_handler_init();
    event_bus_init();
    state_store_init();
    driver_registry_init();
    mock_register_default_drivers();
    vm_init();

    int passed = 0;
    int total = 8;

    passed += test_integer_arithmetic();
    state_store_reset();
    passed += test_float_arithmetic();
    state_store_reset();
    passed += test_conditional_branching();
    state_store_reset();
    passed += test_driver_read();
    state_store_reset();
    passed += test_driver_write();
    state_store_reset();
    passed += test_smart_planter_pipeline();
    state_store_reset();
    passed += test_stack_overflow();
    state_store_reset();
    passed += test_pipeline_markers();

    printf("\n╔══════════════════════════════════════════╗\n");
    printf("║  RESULTS: %d/%d tests passed              ║\n", passed, total);
    printf("╚══════════════════════════════════════════╝\n");

    return (passed == total) ? 0 : 1;
}
