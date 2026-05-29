package com.example.protocol

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

@JsonClass(generateAdapter = true)
data class SensorStreamMessage(
    @Json(name = "t") val t: Long,
    @Json(name = "s") val s: String,
    @Json(name = "v") val v: Double,
    @Json(name = "u") val u: String
)

@JsonClass(generateAdapter = true)
data class CommandMessage(
    @Json(name = "cmd") val cmd: String,
    @Json(name = "pin") val pin: Int? = null,
    @Json(name = "mode") val mode: String? = null,
    @Json(name = "value") val value: Int? = null,
    @Json(name = "text") val text: String? = null,
    @Json(name = "frequency") val frequency: Int? = null
)

@JsonClass(generateAdapter = true)
data class HardwareSensorInfo(
    @Json(name = "key") val key: String,
    @Json(name = "name") val name: String,
    @Json(name = "type") val type: String,
    @Json(name = "unit") val unit: String,
    @Json(name = "pin") val pin: Int
)

@JsonClass(generateAdapter = true)
data class HardwareCapability(
    @Json(name = "name") val name: String,
    @Json(name = "description") val description: String,
    @Json(name = "type") val type: String
)

@JsonClass(generateAdapter = true)
data class HardwareManifest(
    @Json(name = "manifest_version") val manifest_version: String,
    @Json(name = "firmware_version") val firmware_version: String,
    @Json(name = "sensors") val sensors: List<HardwareSensorInfo>,
    @Json(name = "capabilities") val capabilities: List<HardwareCapability>
)

object TinkrProtocol {
    private val moshi: Moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val sensorAdapter = moshi.adapter(SensorStreamMessage::class.java)
    private val commandAdapter = moshi.adapter(CommandMessage::class.java)
    private val manifestAdapter = moshi.adapter(HardwareManifest::class.java)

    fun parseSensorMsg(json: String): SensorStreamMessage? {
        return try {
            sensorAdapter.fromJson(json)
        } catch (_: Exception) {
            null
        }
    }

    fun serializeSensorMsg(msg: SensorStreamMessage): String {
        return sensorAdapter.toJson(msg)
    }

    fun parseCommand(json: String): CommandMessage? {
        return try {
            commandAdapter.fromJson(json)
        } catch (_: Exception) {
            null
        }
    }

    fun serializeCommand(msg: CommandMessage): String {
        return commandAdapter.toJson(msg)
    }

    fun parseManifest(json: String): HardwareManifest? {
        return try {
            manifestAdapter.fromJson(json)
        } catch (_: Exception) {
            null
        }
    }

    fun serializeManifest(manifest: HardwareManifest): String {
        return manifestAdapter.toJson(manifest)
    }

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
