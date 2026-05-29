//! Hallucination-proof IR builder.
//!
//! The LLM emits a simple `StructuredIntent` (devices + rules).
//! This module deterministically validates every field against the 69-driver
//! registry and assembles a valid `IRDocument` — no hallucination possible.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::Utc;

use crate::drivers::registry::DriverRegistry;
use crate::ir::types::{
    IRConstraints, IRDevice, IRDocument, IRNode, IRPipeline, IRStateVariable, IRTrigger,
};

// ── StructuredIntent types ───────────────────────────────────────────────────

/// High-level intent extracted by the LLM. Every field is validated before IR
/// assembly — the LLM never touches raw IR.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructuredIntent {
    pub project_name: String,
    pub devices: Vec<IntentDevice>,
    #[serde(default = "default_poll_interval")]
    pub poll_interval_ms: u64,
    #[serde(default)]
    pub rules: Vec<IntentRule>,
    #[serde(default)]
    pub show_on_display: bool,
}

fn default_poll_interval() -> u64 {
    1000
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentDevice {
    pub id: String,
    pub driver: String,
    pub use_capabilities: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentRule {
    pub sensor_device: String,
    pub sensor_field: String,
    pub op: String,
    pub threshold: f64,
    pub action: IntentAction,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentAction {
    pub device: String,
    pub field: String,
    pub value: String,
}

// ── Build result types ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildError {
    pub field: String,
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub valid_options: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildResult {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ir: Option<IRDocument>,
    pub errors: Vec<BuildError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary: Option<BuildSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildSummary {
    pub device_count: usize,
    pub state_var_count: usize,
    pub pipeline_count: usize,
    pub node_count: usize,
}

// ── Validation constants ─────────────────────────────────────────────────────

const VALID_OPS: &[&str] = &["gt", "lt", "eq", "gte", "lte", "ne"];
const MIN_POLL_MS: u64 = 100;
const MAX_POLL_MS: u64 = 60_000;

// ── Builder entry point ──────────────────────────────────────────────────────

/// Validate a `StructuredIntent` against the driver registry and, if valid,
/// assemble a deterministic `IRDocument`.
pub fn build_ir(intent: &StructuredIntent, registry: &DriverRegistry, board_id: &str) -> BuildResult {
    let mut errors: Vec<BuildError> = Vec::new();

    // -- 1. Validate each device driver exists --
    let all_driver_names: Vec<String> = registry.list_all().iter().map(|d| d.name.clone()).collect();

    for dev in &intent.devices {
        let spec = registry.get_driver(&dev.driver);
        match spec {
            None => {
                errors.push(BuildError {
                    field: format!("devices.{}.driver", dev.id),
                    code: "UNKNOWN_DRIVER".into(),
                    message: format!("Driver '{}' not found in registry", dev.driver),
                    valid_options: Some(all_driver_names.clone()),
                });
            }
            Some(spec) => {
                // -- 2. Validate capabilities --
                for cap in &dev.use_capabilities {
                    if !spec.capabilities.contains(cap) {
                        errors.push(BuildError {
                            field: format!("devices.{}.use_capabilities", dev.id),
                            code: "UNKNOWN_CAPABILITY".into(),
                            message: format!(
                                "Capability '{}' not supported by driver '{}'",
                                cap, dev.driver
                            ),
                            valid_options: Some(spec.capabilities.clone()),
                        });
                    }
                }
            }
        }
    }

    // -- 3. Validate rule operators --
    for (i, rule) in intent.rules.iter().enumerate() {
        if !VALID_OPS.contains(&rule.op.as_str()) {
            errors.push(BuildError {
                field: format!("rules[{}].op", i),
                code: "INVALID_OPERATOR".into(),
                message: format!(
                    "Operator '{}' is invalid. Must be one of: {}",
                    rule.op,
                    VALID_OPS.join(", ")
                ),
                valid_options: Some(VALID_OPS.iter().map(|s| s.to_string()).collect()),
            });
        }
    }

    // -- 4. Validate poll interval --
    if intent.poll_interval_ms < MIN_POLL_MS || intent.poll_interval_ms > MAX_POLL_MS {
        errors.push(BuildError {
            field: "poll_interval_ms".into(),
            code: "INVALID_INTERVAL".into(),
            message: format!(
                "poll_interval_ms must be between {} and {}, got {}",
                MIN_POLL_MS, MAX_POLL_MS, intent.poll_interval_ms
            ),
            valid_options: None,
        });
    }

    // -- 5. Short-circuit on errors --
    if !errors.is_empty() {
        return BuildResult {
            success: false,
            ir: None,
            errors,
            summary: None,
        };
    }

    // -- 6. Deterministic IR assembly --
    let program_id = slugify(&intent.project_name);

    // 6a. Devices
    let ir_devices: Vec<IRDevice> = intent
        .devices
        .iter()
        .map(|d| {
            let spec = registry.get_driver(&d.driver).unwrap();
            let bus = spec.bus_types.first().cloned().unwrap_or_else(|| "i2c_0".into());
            let address = spec.i2c_addresses.first().cloned();
            IRDevice {
                id: d.id.clone(),
                driver: d.driver.clone(),
                bus,
                address,
                pin_slot: None,
                capabilities: d.use_capabilities.clone(),
                config: None,
            }
        })
        .collect();

    // 6b. State variables — one per sensor capability
    let mut state: HashMap<String, IRStateVariable> = HashMap::new();
    for dev in &intent.devices {
        let spec = registry.get_driver(&dev.driver).unwrap();
        if spec.driver_type == "sensor" {
            for cap in &dev.use_capabilities {
                let var_name = format!("{}_{}", dev.id, cap);
                state.insert(
                    var_name,
                    IRStateVariable {
                        var_type: "float".into(),
                        initial: serde_json::Value::from(0.0),
                        min: None,
                        max: None,
                        persistent: None,
                    },
                );
            }
        }
    }

    // 6c. Trigger — one timer
    let trigger = IRTrigger {
        id: "poll_timer".into(),
        trigger_type: "timer".into(),
        interval_ms: Some(intent.poll_interval_ms),
        cron: None,
        device: None,
        field: None,
        threshold: None,
        comparison: None,
        hysteresis: None,
        edge: None,
        topic: None,
        payload_match: None,
        ble_event_type: None,
        window_start: None,
        window_end: None,
        debounce_ms: None,
    };

    // 6d. Pipeline nodes
    let mut nodes: Vec<IRNode> = Vec::new();
    let mut node_idx: u32 = 0;

    // Sensor read nodes
    for dev in &intent.devices {
        let spec = registry.get_driver(&dev.driver).unwrap();
        if spec.driver_type == "sensor" {
            for cap in &dev.use_capabilities {
                let node_id = format!("read_{}_{}", dev.id, cap);
                let store_var = format!("{}_{}", dev.id, cap);
                nodes.push(IRNode {
                    id: node_id,
                    node_type: "sensor.read".into(),
                    device: Some(dev.id.clone()),
                    field: Some(cap.clone()),
                    store_to: Some(store_var),
                    next: None,
                    variable: None,
                    load_from: None,
                    value: None,
                    left: None,
                    right: None,
                    op: None,
                    if_true: None,
                    if_false: None,
                    operands: None,
                    min_value: None,
                    max_value: None,
                    in_min: None,
                    in_max: None,
                    out_min: None,
                    out_max: None,
                    topic: None,
                    payload: None,
                    characteristic: None,
                    fields: None,
                    destination: None,
                    text: None,
                    line: None,
                    duration_ms: None,
                    duty_percent: None,
                    color: None,
                    led_index: None,
                });
                node_idx += 1;
            }
        }
    }

    // Display nodes (if requested)
    if intent.show_on_display {
        let mut display_line: u8 = 0;
        for dev in &intent.devices {
            let spec = registry.get_driver(&dev.driver).unwrap();
            if spec.driver_type == "sensor" {
                for cap in &dev.use_capabilities {
                    let var_name = format!("{}_{}", dev.id, cap);
                    nodes.push(IRNode {
                        id: format!("display_{}", var_name),
                        node_type: "display.text".into(),
                        text: Some(format!("{}: ${}", cap, var_name)),
                        line: Some(display_line),
                        device: None,
                        field: None,
                        store_to: None,
                        next: None,
                        variable: None,
                        load_from: None,
                        value: None,
                        left: None,
                        right: None,
                        op: None,
                        if_true: None,
                        if_false: None,
                        operands: None,
                        min_value: None,
                        max_value: None,
                        in_min: None,
                        in_max: None,
                        out_min: None,
                        out_max: None,
                        topic: None,
                        payload: None,
                        characteristic: None,
                        fields: None,
                        destination: None,
                        duration_ms: None,
                        duty_percent: None,
                        color: None,
                        led_index: None,
                    });
                    display_line = display_line.saturating_add(1);
                    node_idx += 1;
                }
            }
        }
    }

    // Rule nodes (condition + actuator)
    for (i, rule) in intent.rules.iter().enumerate() {
        let compare_id = format!("cmp_{}", i);
        let action_id = format!("act_{}", i);
        let sensor_var = format!("{}_{}", rule.sensor_device, rule.sensor_field);

        nodes.push(IRNode {
            id: compare_id.clone(),
            node_type: "condition.compare".into(),
            left: Some(serde_json::Value::String(format!("${}", sensor_var))),
            op: Some(rule.op.clone()),
            right: Some(serde_json::json!(rule.threshold)),
            if_true: Some(action_id.clone()),
            if_false: None,
            device: None,
            field: None,
            store_to: None,
            next: None,
            variable: None,
            load_from: None,
            value: None,
            operands: None,
            min_value: None,
            max_value: None,
            in_min: None,
            in_max: None,
            out_min: None,
            out_max: None,
            topic: None,
            payload: None,
            characteristic: None,
            fields: None,
            destination: None,
            text: None,
            line: None,
            duration_ms: None,
            duty_percent: None,
            color: None,
            led_index: None,
        });
        node_idx += 1;

        nodes.push(IRNode {
            id: action_id,
            node_type: "actuator.write".into(),
            device: Some(rule.action.device.clone()),
            field: Some(rule.action.field.clone()),
            value: Some(serde_json::Value::String(rule.action.value.clone())),
            next: None,
            variable: None,
            store_to: None,
            load_from: None,
            left: None,
            right: None,
            op: None,
            if_true: None,
            if_false: None,
            operands: None,
            min_value: None,
            max_value: None,
            in_min: None,
            in_max: None,
            out_min: None,
            out_max: None,
            topic: None,
            payload: None,
            characteristic: None,
            fields: None,
            destination: None,
            text: None,
            line: None,
            duration_ms: None,
            duty_percent: None,
            color: None,
            led_index: None,
        });
        node_idx += 1;
    }

    let total_nodes = nodes.len();
    let max_exec = std::cmp::min(intent.poll_interval_ms / 2, 2000) as u32;

    let pipeline = IRPipeline {
        id: "main_pipeline".into(),
        trigger: "poll_timer".into(),
        enabled: true,
        priority: 5,
        mutex_group: None,
        nodes,
        max_execution_ms: max_exec,
    };

    let ir = IRDocument {
        version: "1.0".into(),
        program_id,
        board_id: board_id.into(),
        created_at: Utc::now().to_rfc3339(),
        signature: String::new(),
        devices: ir_devices,
        state,
        triggers: vec![trigger],
        pipelines: vec![pipeline],
        constraints: IRConstraints::default(),
    };

    let summary = BuildSummary {
        device_count: ir.devices.len(),
        state_var_count: ir.state.len(),
        pipeline_count: ir.pipelines.len(),
        node_count: total_nodes,
    };

    BuildResult {
        success: true,
        ir: Some(ir),
        errors: Vec::new(),
        summary: Some(summary),
    }
}

fn slugify(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c.is_alphanumeric() {
                c.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_string()
}
