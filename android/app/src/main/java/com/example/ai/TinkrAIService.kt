package com.example.ai

import android.content.Context
import android.util.Log
import com.example.BuildConfig
import com.example.data.AIChatEntity
import com.example.data.ProjectEntity
import com.example.data.TinkrDatabase
import com.example.hardware.TinkrBleManager
import com.example.protocol.CommandMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class Tool(val name: String, val description: String)

@Target(AnnotationTarget.VALUE_PARAMETER)
@Retention(AnnotationRetention.RUNTIME)
annotation class ToolParam(val name: String, val description: String, val required: Boolean = true)

interface ToolSet

interface HardwareTools : ToolSet {
    @Tool("writeGPIO", "Writes digital level 0 or 1 to a physical microcontroller GPIO pin.")
    fun writeGPIO(
        @ToolParam("pin", "GPIO pin number") pin: Int,
        @ToolParam("value", "Digital state: 0 or 1") value: Int
    )

    @Tool("updateDisplay", "Renders text to the ST7789 TFT LCD panel buffer.")
    fun updateDisplay(
        @ToolParam("text", "Text content to display") text: String
    )

    @Tool("triggerWatering", "Pulse Pin 12 relay to activate the water pump.")
    fun triggerWatering()

    @Tool("createProject", "Generates a project template inside Parakram storage.")
    fun createProject(
        @ToolParam("name", "Project name") name: String,
        @ToolParam("templateType", "Template category") templateType: String
    )

    @Tool("playBuzzer", "Emits a buzzer audio pulse at a specified frequency.")
    fun playBuzzer(
        @ToolParam("frequency", "Frequency in Hertz") frequency: Int
    )
}

data class AgentAction(
    val toolName: String,
    val description: String,
    val payloadJson: String
)

data class AIResponse(
    val message: String,
    val explanation: String,
    val actions: List<AgentAction>,
    val codePreview: String = "",
    val modelSource: String = "Local Gemma 4 E2B (Simulated)"
)

class TinkrAIService private constructor(private val context: Context) : HardwareTools {

    private val bleManager = TinkrBleManager.getInstance(context)
    private val database = TinkrDatabase.getDatabase(context)
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _aiUpdates = MutableSharedFlow<AIResponse>(replay = 1)
    val aiUpdates: SharedFlow<AIResponse> = _aiUpdates.asSharedFlow()

    private val toolSchemas: List<JSONObject> by lazy { buildToolSchemas() }

    companion object {
        private const val TAG = "TinkrAI"

        @Volatile
        private var INSTANCE: TinkrAIService? = null

        fun getInstance(context: Context): TinkrAIService {
            return INSTANCE ?: synchronized(this) {
                val instance = TinkrAIService(context.applicationContext)
                INSTANCE = instance
                instance
            }
        }
    }

    // --- Reflective tool schema generation from annotations ---
    private fun buildToolSchemas(): List<JSONObject> {
        val schemas = mutableListOf<JSONObject>()
        for (method in HardwareTools::class.java.declaredMethods) {
            val toolAnnotation = method.getAnnotation(Tool::class.java) ?: continue
            val params = JSONObject()
            for ((index, param) in method.parameters.withIndex()) {
                val paramAnnotation = param.getAnnotation(ToolParam::class.java)
                if (paramAnnotation != null) {
                    params.put(paramAnnotation.name, JSONObject().apply {
                        put("description", paramAnnotation.description)
                        put("required", paramAnnotation.required)
                        put("type", when (param.type) {
                            Int::class.java, java.lang.Integer::class.java -> "integer"
                            String::class.java -> "string"
                            Boolean::class.java, java.lang.Boolean::class.java -> "boolean"
                            Double::class.java, java.lang.Double::class.java -> "number"
                            else -> "string"
                        })
                    })
                }
            }
            schemas.add(JSONObject().apply {
                put("name", toolAnnotation.name)
                put("description", toolAnnotation.description)
                put("parameters", params)
            })
        }
        return schemas
    }

    // --- Hardware tool implementations ---
    override fun writeGPIO(pin: Int, value: Int) {
        bleManager.processCommand(CommandMessage(cmd = "set_gpio", pin = pin, value = value))
    }

    override fun updateDisplay(text: String) {
        bleManager.processCommand(CommandMessage(cmd = "display", text = text))
    }

    override fun triggerWatering() {
        bleManager.triggerWatering()
    }

    override fun createProject(name: String, templateType: String) {
        scope.launch {
            val proj = ProjectEntity(
                name = name,
                description = "AI recommended setup for $templateType hardware config.",
                templateType = templateType,
                codeContent = "// Generated by Parakram AI\nvoid setup() {\n  pinMode(13, OUTPUT);\n}\nvoid loop() {\n  // Automated loops\n}"
            )
            database.projectDao().insertProject(proj)
        }
    }

    override fun playBuzzer(frequency: Int) {
        bleManager.processCommand(CommandMessage(cmd = "play_tone", frequency = frequency))
    }

    // --- Recursive autonomous agent loop ---
    suspend fun runPrompt(prompt: String, mode: String = "Builder"): AIResponse = withContext(Dispatchers.IO) {
        bleManager.addLog("AI Thinking... Routing: \"$prompt\"")
        delay(2000)

        val apiKey = BuildConfig.GEMINI_API_KEY
        val hasCloudApiKey = apiKey.isNotEmpty() && apiKey != "MY_GEMINI_API_KEY"

        val aiResponse = if (hasCloudApiKey) {
            callCloudGemini(prompt, mode, apiKey)
        } else {
            generateLocalResponse(prompt, mode)
        }

        // Autonomous recursive action execution
        aiResponse.actions.forEach { action ->
            bleManager.addLog("Agent executing: `${action.toolName}` - ${action.description}")
            executeToolReflective(action.toolName, action.payloadJson)
            delay(800)
        }

        // Record transaction to database
        try {
            database.aiChatDao().insertChat(
                AIChatEntity(
                    sessionId = "default_session",
                    role = "user",
                    mode = mode,
                    messageText = prompt
                )
            )
            database.aiChatDao().insertChat(
                AIChatEntity(
                    sessionId = "default_session",
                    role = "assistant",
                    mode = mode,
                    messageText = "${aiResponse.message}\n\n${aiResponse.explanation}",
                    codeBlob = aiResponse.codePreview,
                    actionsJson = JSONArray(aiResponse.actions.map {
                        JSONObject().apply {
                            put("toolName", it.toolName)
                            put("description", it.description)
                            put("payloadJson", it.payloadJson)
                        }
                    }).toString()
                )
            )
        } catch (_: Exception) {}

        _aiUpdates.emit(aiResponse)
        bleManager.addLog("AI Task Completed: Response generated.")
        aiResponse
    }

    private fun executeToolReflective(toolName: String, payloadJson: String) {
        try {
            val json = JSONObject(payloadJson)
            when (toolName) {
                "writeGPIO" -> writeGPIO(json.optInt("pin", 13), json.optInt("value", 1))
                "updateDisplay" -> updateDisplay(json.optString("text", "Running Parakram OS"))
                "triggerWatering" -> triggerWatering()
                "playBuzzer" -> playBuzzer(json.optInt("frequency", 800))
                "createProject" -> createProject(
                    json.optString("name", "Auto Smart Setup"),
                    json.optString("templateType", "Custom")
                )
                else -> Log.d(TAG, "Executing generic tool: $toolName")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Reflective tool call failed: ${e.message}")
        }
    }

    private fun callCloudGemini(prompt: String, mode: String, apiKey: String): AIResponse {
        val client = OkHttpClient()
        val url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$apiKey"

        val toolsJson = JSONArray(toolSchemas.map { it.toString() }).toString()
        val systemInstruction = """You are the Parakram Operating System AI Assistant running in $mode mode.
Available Hardware Tools: $toolsJson
Always respond in JSON: { "message":"Summary", "explanation":"Reasoning", "codePreview":"Arduino code or empty", "actions":[{"toolName":"tool", "description":"desc", "payloadJson":"JSON params"}] }"""

        val requestBodyJson = JSONObject()
            .put("contents", JSONArray().put(
                JSONObject().put("parts", JSONArray().put(
                    JSONObject().put("text", prompt)
                ))
            ))
            .put("systemInstruction", JSONObject().put("parts", JSONArray().put(
                JSONObject().put("text", systemInstruction)
            )))
            .put("generationConfig", JSONObject().put("responseMimeType", "application/json"))

        val mediaType = "application/json; charset=utf-8".toMediaType()
        val request = Request.Builder()
            .url(url)
            .post(requestBodyJson.toString().toRequestBody(mediaType))
            .build()

        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw Exception("HTTP ${response.code}")
                val bodyString = response.body?.string() ?: throw Exception("Empty response")

                val parsed = JSONObject(bodyString)
                val responseText = parsed.getJSONArray("candidates")
                    .getJSONObject(0)
                    .getJSONObject("content")
                    .getJSONArray("parts")
                    .getJSONObject(0)
                    .getString("text")

                val resJson = JSONObject(responseText)
                val actionsList = mutableListOf<AgentAction>()
                val actionsArr = resJson.optJSONArray("actions")
                if (actionsArr != null) {
                    for (i in 0 until actionsArr.length()) {
                        val actObj = actionsArr.getJSONObject(i)
                        actionsList.add(AgentAction(
                            toolName = actObj.getString("toolName"),
                            description = actObj.getString("description"),
                            payloadJson = actObj.optString("payloadJson", "{}")
                        ))
                    }
                }

                AIResponse(
                    message = resJson.optString("message", "Request completed."),
                    explanation = resJson.optString("explanation", ""),
                    actions = actionsList,
                    codePreview = resJson.optString("codePreview", ""),
                    modelSource = "Gemini 2.0 Flash (Cloud)"
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Cloud call failed: ${e.message}")
            generateLocalResponse(prompt, mode)
        }
    }

    private fun generateLocalResponse(prompt: String, mode: String): AIResponse {
        val query = prompt.lowercase()
        val actions = mutableListOf<AgentAction>()
        var message = "Acknowledged. Processing: \"$prompt\""
        var explanation = "Using local Gemma 4 E2B reasoning pipeline."
        var codePreview = ""

        when {
            query.contains("led") || query.contains("turn on") || query.contains("light") -> {
                val isOn = !query.contains("off")
                val value = if (isOn) 1 else 0
                message = "Configuring GPIO Pin 13 to ${if (isOn) "HIGH" else "LOW"}."
                explanation = "Status LED responds to GPIO command. Initiating direct write."
                actions.add(AgentAction("writeGPIO", "Setting Pin 13 to $value", "{\"pin\":13, \"value\":$value}"))
                actions.add(AgentAction("updateDisplay", "LCD update for LED state", "{\"text\":\"LED Pin13 -> ${if (isOn) "ON" else "OFF"}\"}"))
                codePreview = "void setup() {\n  pinMode(13, OUTPUT);\n}\nvoid loop() {\n  digitalWrite(13, ${if (isOn) "HIGH" else "LOW"});\n}"
            }
            query.contains("water") || query.contains("irrigate") || query.contains("soil") -> {
                message = "Activating soil moisture irrigation pulse."
                explanation = "Issuing relay command to GPIO Pin 12 for water pump activation."
                actions.add(AgentAction("writeGPIO", "Pin 12 Relay HIGH", "{\"pin\":12, \"value\":1}"))
                actions.add(AgentAction("updateDisplay", "LCD watering feedback", "{\"text\":\"ACTIVE: Watering\\nSoil Moisture -> 80%\"}"))
                actions.add(AgentAction("playBuzzer", "Feedback hum", "{\"frequency\":650}"))
                codePreview = "#define PUMP_RELAY 12\n#define SOIL_PIN 32\nvoid setup() {\n  pinMode(PUMP_RELAY, OUTPUT);\n}\nvoid loop() {\n  if (analogRead(SOIL_PIN) < 500) {\n    digitalWrite(PUMP_RELAY, HIGH);\n    delay(4000);\n    digitalWrite(PUMP_RELAY, LOW);\n  }\n}"
            }
            query.contains("alarm") || query.contains("buzz") || query.contains("siren") -> {
                message = "Triggering auditory alarm!"
                explanation = "Emergency acoustic program at Pin 14 piezo."
                actions.add(AgentAction("playBuzzer", "Pin 14 alarm", "{\"frequency\":1200}"))
                actions.add(AgentAction("updateDisplay", "Warning on TFT", "{\"text\":\"CRITICAL ALERT\\nEmergency siren!\"}"))
                codePreview = "#define PIEZO 14\nvoid setup() { pinMode(PIEZO, OUTPUT); }\nvoid loop() {\n  for(int f=800;f<1500;f+=10) { tone(PIEZO,f); delay(10); }\n  noTone(PIEZO);\n}"
            }
            query.contains("project") || query.contains("create") || query.contains("scaffold") -> {
                message = "Instantiating Project Sandbox..."
                explanation = "Generating hardware specifications and boilerplate for smart planter."
                actions.add(AgentAction("createProject", "SmartPlanter template", "{\"name\":\"Smart Garden Planter\", \"templateType\":\"SmartPlanter\"}"))
                actions.add(AgentAction("updateDisplay", "Workspace confirmed", "{\"text\":\"Workspace Configured\\nProject: Planter\"}"))
                codePreview = "{\n  \"project_name\": \"Smart Garden Planter\",\n  \"firmware\": \"ESP32-S3\",\n  \"autostart\": true,\n  \"sensors\": { \"moist_inlet\": 32, \"temp_sensor\": 4 }\n}"
            }
            else -> {
                message = "Parakram AI agent listening in **$mode Mode**."
                explanation = "Ready to compile code, parse sensor logs, or manage pins. Try:\n- 'Turn on the status LED'\n- 'Water the plant now'\n- 'Sound the emergency siren'"
                actions.add(AgentAction("updateDisplay", "Idle diagnostic", "{\"text\":\"AI Agent Standby\\nMode: $mode\"}"))
            }
        }

        return AIResponse(
            message = message,
            explanation = explanation,
            actions = actions,
            codePreview = codePreview,
            modelSource = "Local Gemma 4 E2B (Simulated)"
        )
    }
}
