package com.example.protocol

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

// --- PROTOCOL PROTO TYPES ---

data class SensorStreamMessage(
    val t: Long,       // Timestamp
    val s: String,     // Sensor Key / Name (e.g. "temp_0", "light_0")
    val v: Double,     // Numeric Value
    val u: String      // Unit (e.g. "C", "lx", "%")
)

data class CommandMessage(
    val cmd: String,       // e.g., "set_gpio", "play_tone", "servo_angle", "display"
    val pin: Int? = null,
    val mode: String? = null, // "output", "input", "input_pullup"
    val value: Int? = null,   // 0 or 1, or pwm duty
    val text: String? = null, // text for display or logs
    val frequency: Int? = null // for buzzer/sound
)

data class HardwareSensorInfo(
    val key: String,
    val name: String,
    val type: String,
    val unit: String,
    val pin: Int
)

data class HardwareCapability(
    val name: String,
    val description: String,
    val type: String // e.g. "GPIO", "I2C", "ADC", "PWM", "TFT", "AUDIO"
)

data class HardwareManifest(
    val manifest_version: String,
    val firmware_version: String,
    val sensors: List<HardwareSensorInfo>,
    val capabilities: List<HardwareCapability>
)

object TinkrProtocol {
    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val sensorAdapter = moshi.adapter(SensorStreamMessage::class.java)
    private val commandAdapter = moshi.adapter(CommandMessage::class.java)
    private val manifestAdapter = moshi.adapter(HardwareManifest::class.java)

    fun parseSensorMsg(json: String): SensorStreamMessage? {
        return try {
            sensorAdapter.fromJson(json)
        } catch (e: Exception) {
            null
        }
    }

    fun serializeSensorMsg(msg: SensorStreamMessage): String {
        return sensorAdapter.toJson(msg)
    }

    fun parseCommand(json: String): CommandMessage? {
        return try {
            commandAdapter.fromJson(json)
        } catch (e: Exception) {
            null
        }
    }

    fun serializeCommand(msg: CommandMessage): String {
        return commandAdapter.toJson(msg)
    }

    fun parseManifest(json: String): HardwareManifest? {
        return try {
            manifestAdapter.fromJson(json)
        } catch (e: Exception) {
            null
        }
    }

    fun serializeManifest(manifest: HardwareManifest): String {
        return manifestAdapter.toJson(manifest)
    }

    // Default manifest for a standard Intelligent Board Setup (ESP32-S3 IoT Kit)
    fun getDefaultESP32S3Manifest(): HardwareManifest {
        return HardwareManifest(
            manifest_version = "1",
            firmware_version = "2.1.4",
            sensors = listOf(
                HardwareSensorInfo("temp_0", "Ambient Temperature", "Temperature", "°C", 4),
                HardwareSensorInfo("humid_0", "Relative Humidity", "Humidity", "%", 4),
                HardwareSensorInfo("light_0", "Lux Sensor", "Luminosity", "lx", 2),
                HardwareSensorInfo("moist_0", "Soil Moisture", "Moisture", "%", 32),
                HardwareSensorInfo("co2_0", "Air Quality (CO2)", "CO2", "ppm", 33)
            ),
            capabilities = listOf(
                HardwareCapability("GPIO_13_LED", "Onboard Debug Status LED", "GPIO"),
                HardwareCapability("RELAY_12", "High Voltage Relay Control Trigger", "GPIO"),
                HardwareCapability("PWM_SERVO_15", "Servo Motor Swivel Articulation", "PWM"),
                HardwareCapability("BUZZER_14", "Emergency Auditory Alarm Piezo", "AUDIO"),
                HardwareCapability("TFT_ST7789", "Color Status LCD Panel Stream", "TFT")
            )
        )
    }
}
