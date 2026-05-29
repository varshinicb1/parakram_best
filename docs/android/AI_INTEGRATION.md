# Parakram AI Agent Integration & Autonomous Tools 🤖

Parakram integrates a customizable generative system that acts as a real-time copilot for physical computing. The application translates natural language prompts into physical microchip behaviors using reflective tool definitions and an autonomous execution loop.

---

## 1. Structural Flow: Code and Tool Execution

```text
  ┌──────────────┐
  │ User Prompt  │  "Turn on LED 13 and update screen to 'Hi'"
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  AIService   ├───────────────────────────────┐
  └──────┬───────┘                               │
         ▼                                       ▼
   (Cloud Mode)                             (Local Fallback)
   POST googleapis/v1beta/gemini             Simulate Gemma response using
   MimeType: application/json                local keyword heuristics
         │                                       │
         └───────────────────┬───────────────────┘
                             ▼
  ┌──────────────────────────────────────────────┐
  │                  AIResponse                  │
  │ { message: String, explanation: String,      │
  │   actions: [AgentAction], codePreview: "" }  │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼ (Recursive Dispatcher Loop)
  ┌──────────────────────────────────────────────┐
  │       executeToolReflective(action)         │
  │ Loops and invokes matches:                   │
  │ -> writeGPIO(pin=13, value=1)                │
  │ -> delay(800ms) for physical settling        │
  │ -> updateDisplay("Hi")                       │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────┐
  │             Database Turn Logging            │
  │ Saved to AIChatDao for UI stream reloading   │
  └──────────────────────────────────────────────┘
```

---

## 2. Core Components Reference

### 2.1 Tool Annotations (`@Tool` & `@ToolParam`)
Parakram does not use fixed, hardcoded tool trees. Tools are registered dynamically using Kotlin annotations:

```kotlin
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class Tool(val name: String, val description: String)

@Target(AnnotationTarget.VALUE_PARAMETER)
@Retention(AnnotationRetention.RUNTIME)
annotation class ToolParam(val name: String, val description: String, val required: Boolean = true)
```

The system includes a declared interface `HardwareTools` that maps these annotations to physical capabilities:

```kotlin
interface HardwareTools : ToolSet {
    @Tool("writeGPIO", "Writes digital code level 0 or 1 to a physical microcontroller GPIO pin.")
    fun writeGPIO(pin: Int, value: Int)

    @Tool("updateDisplay", "Renders text messaging buffer directly to ST7789 TFT LCD panel.")
    fun updateDisplay(text: String)

    @Tool("triggerWatering", "Pulse Pin 12 relay to pump organic nutrients.")
    fun triggerWatering()

    @Tool("createProject", "Generates and launches a clean custom template project inside Parakram storage.")
    fun createProject(name: String, templateType: String)

    @Tool("playBuzzer", "Emits a warning buzzer acoustic audio pulse frequency.")
    fun playBuzzer(frequency: Int)
}
```

---

### 2.2 Deep Dive: TinkrAIService

`TinkrAIService` implements `HardwareTools` and coordinates tool executions.

#### Singleton Access
`TinkrAIService` is initialized through a thread-safe synchronized constructor:
```kotlin
val aiService = TinkrAIService.getInstance(context)
```

#### Run Prompt (`runPrompt`)
When an AI prompt executes:
1.  **Safety Log**: A message is added to the system logs layout: `AI Thinking Mode Activated...`
2.  **API Key Verification**: The service inspects `BuildConfig.GEMINI_API_KEY`.
3.  **Reflective Action Loops**: Iterates through the returned action list, calling the target functions on the active thread pool.
4.  **Database Updates**: Logs the request and response objects to local SQLite tables for historical re-hydration.
5.  **State Notification**: Emits updates to the reactive `aiUpdates` SharedFlow.

#### Database Transcript Schemas
The database schema stores conversational history. For example, when structured tools are executed, they are stored in the database as follows:
```json
{
  "sessionId": "default_session",
  "role": "assistant",
  "messageText": "LED turned on",
  "actionsJson": "[{\"toolName\":\"writeGPIO\",\"description\":\"Setting diagnostic Pin 13\",\"payloadJson\":\"{\\\"pin\\\":13,\\\"value\\\":1}\"}]"
}
```

---

## 3. Communication and Fallback Engines

### 3.1 Cloud Integration (Gemini 3.5 Flash)
In cloud mode, `TinkrAIService` makes direct REST calls to the Gemini API (`/v1beta/models/gemini-3.5-flash:generateContent`).

*   **System Instructions (Instruction Guard)**: Sets instructions forcing the language model to behave as the Parakram Companion OS. It profiles available tool registers and mandates that responses match a strict JSON scheme:
    ```javascript
    {
      "message": "User-facing summary",
      "explanation": "Logical breakdown",
      "codePreview": "Arduino C++ boilerplate or output schema files (optional)",
      "actions": [
         { "toolName": "name", "description": "desc", "payloadJson": "{...}" }
      ]
    }
    ```
*   **JSON Enforcement**: Instructs OkHttp/Moshi to request responses in JSON format:
    ```kotlin
    .put("generationConfig", JSONObject().put("responseMimeType", "application/json"))
    ```

### 3.2 Offline Fallback (Local Simulation Gemma Heuristics)
To ensure the application is functional when offline, Parakram contains an offline heuristics engine:
*   Matches triggers (e.g., `"led"`, `"watering"`, `"alarm"`, `"scaffold"`) using pattern parsing.
*   Enforces correct tool definitions programmatically.
*   Acts as a deterministic mockup, responding instantly without network lag.

---

## 4. Maintenance Guide: How to Extend the AI Toolset 🛠

Follow this step-by-step developer tutorial to add a new physical tool (e.g., controlling a Servo Sweep at Pin 15) to Parakram's AI systems.

### Step 1: Update the Interface Contract
Open `TinkrAIService.kt` and locate `interface HardwareTools`. Add the annotated function model representing your new hardware capability:

```kotlin
interface HardwareTools : ToolSet {
    // ... Pre-existing Tools ...

    @Tool("sweepServo", "Rotates high-accuracy articulation servo motor on Pin 15 to a target degree angle.")
    fun sweepServo(
        @ToolParam("angle", "Target angle in degrees, from 0 to 180.", required = true)
        angle: Int
    )
}
```

### Step 2: Implement the Physical Action Handler
Still inside `TinkrAIService.kt`, add the concrete implementation to the `TinkrAIService` class body. This directs commands to the Bluetooth Low Energy thread pool:

```kotlin
override fun sweepServo(angle: Int) {
    // Forward the structural mapped packet over to BLE Bluetooth controllers
    bleManager.processCommand(CommandMessage(cmd = "servo_angle", pin = 15, value = angle))
}
```

### Step 3: Map the Reflective JSON Dispatcher
Scroll down to `executeToolReflective` in `TinkrAIService.kt`. Add a mapping block in the `when` dispatcher to parse incoming payloads from the AI model:

```kotlin
private fun executeToolReflective(toolName: String, payloadJson: String) {
    try {
        val json = JSONObject(payloadJson)
        when (toolName) {
            // ... Pre-existing Tool dispatchers ...

            "sweepServo" -> {
                val angle = json.optInt("angle", 90) // Default to center 90 degrees
                sweepServo(angle)
            }
        }
    } catch (e: Exception) {
        Log.e("AIService", "Reflective sweepServo tool call failed: ${e.message}")
    }
}
```

### Step 4: Register Offline Code Preview Fallbacks (Optional)
If you want the offline AI generator to support this tool without an active Internet connection, add a matcher block to `generateLocalResponse`:

```kotlin
query.contains("servo") || query.contains("rotate") || query.contains("sweep") -> {
    message = "Adjusting physical servo arm articulation joint."
    explanation = "Adjusting high-precision servo controller matching requested coordinates."
    actions.add(
        AgentAction(
            "sweepServo",
            "Setting servo articulation angle to 135 degrees",
            "{\"angle\": 135}"
        )
    )
    codePreview = "// Servo controller integration\n#include <Servo.h>\n..."
}
```

### Step 5: Verify Your Implementation
Rebuild the application using Gradle and run tests to ensure your changes didn't introduce compile issues:
```bash
gradle compileDebugKotlin
```

Your new hardware tool is now fully integrated! Parakram's AI is ready to orchestrate this new capability across physical BLE links.
