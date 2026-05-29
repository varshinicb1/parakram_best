package com.example.data

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

// --- Health ---
@JsonClass(generateAdapter = true)
data class HealthResponse(
    val status: String,
    val version: String,
    val database: String,
    @Json(name = "llm_available") val llmAvailable: Boolean,
    @Json(name = "registered_drivers") val registeredDrivers: Int
)

// --- Driver Registry ---
@JsonClass(generateAdapter = true)
data class DriverInfo(
    val name: String,
    @Json(name = "display_name") val displayName: String = "",
    val description: String = "",
    @Json(name = "driver_type") val driverType: String = "",
    @Json(name = "bus_types") val busTypes: List<String> = emptyList(),
    val capabilities: List<String> = emptyList()
)

// --- Driver List Wrapper ---
@JsonClass(generateAdapter = true)
data class DriversResponse(
    val drivers: List<DriverInfo> = emptyList(),
    val total: Int = 0
)

// --- Board Registry ---
@JsonClass(generateAdapter = true)
data class BoardInfo(
    val sku: String = "",
    val name: String = "",
    val soc: String = "",
    @Json(name = "flash_mb") val flashMb: Int = 0,
    @Json(name = "psram_mb") val psramMb: Int = 0
)

// --- Board List Wrapper ---
@JsonClass(generateAdapter = true)
data class BoardsResponse(
    val boards: List<BoardInfo> = emptyList()
)

// --- LLM Intent ---
@JsonClass(generateAdapter = true)
data class IntentRequest(
    val description: String,
    @Json(name = "board_id") val boardId: String = "VDYT-S3-R1",
    @Json(name = "device_id") val deviceId: String? = null,
    val context: String? = null
)

@JsonClass(generateAdapter = true)
data class IntentResponse(
    val feasible: Boolean,
    val ir: Any? = null,
    @Json(name = "ir_preview") val irPreview: IRPreview? = null,
    val validation: Any? = null,
    val reason: String? = null,
    val clarifications: List<String>? = null,
    val suggestions: List<String>? = null,
    @Json(name = "llm_model") val llmModel: String = "",
    @Json(name = "generation_time_ms") val generationTimeMs: Long = 0
)

@JsonClass(generateAdapter = true)
data class IRPreview(
    val summary: String = "",
    val triggers: List<TriggerPreview> = emptyList(),
    val actions: List<ActionPreview> = emptyList(),
    @Json(name = "sensors_used") val sensorsUsed: List<String> = emptyList(),
    @Json(name = "actuators_used") val actuatorsUsed: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class TriggerPreview(
    val description: String = "",
    val interval: String = ""
)

@JsonClass(generateAdapter = true)
data class ActionPreview(
    val condition: String = "",
    val action: String = ""
)

// --- IR Compile ---
@JsonClass(generateAdapter = true)
data class CompileRequest(
    val version: String = "1.0",
    @Json(name = "program_id") val programId: String = "default",
    @Json(name = "board_id") val boardId: String = "VDYT-S3-R1",
    @Json(name = "created_at") val createdAt: String = "",
    val devices: List<Any> = emptyList(),
    val state: Map<String, Any> = emptyMap(),
    val triggers: List<Any> = emptyList(),
    val pipelines: List<Any> = emptyList(),
    val constraints: Map<String, Any> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class CompileResponse(
    val success: Boolean = false,
    @Json(name = "bytecode_hex") val bytecodeHex: String? = null,
    @Json(name = "bytecode_size") val bytecodeSize: Int? = null,
    val signature: String? = null,
    val errors: List<String>? = null
)

// --- Auth ---
@JsonClass(generateAdapter = true)
data class LoginRequest(
    val username: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String? = null
)

@JsonClass(generateAdapter = true)
data class AuthResponse(
    val token: String = "",
    @Json(name = "user_id") val userId: String = "",
    val message: String? = null
)

// --- System Config ---
@JsonClass(generateAdapter = true)
data class SystemConfig(
    @Json(name = "max_projects_per_user") val maxProjectsPerUser: Int = 0,
    @Json(name = "max_devices_per_user") val maxDevicesPerUser: Int = 0,
    @Json(name = "llm_model") val llmModel: String = "",
    @Json(name = "llm_rate_limit_per_minute") val llmRateLimitPerMinute: Int = 0,
    @Json(name = "ir_schema_version") val irSchemaVersion: String = "",
    @Json(name = "bytecode_version") val bytecodeVersion: Int = 0
)

// --- Retrofit API Interface ---
interface ParakramApi {
    // System
    @GET("api/system/health")
    suspend fun health(): Response<HealthResponse>

    @GET("api/system/config")
    suspend fun config(): Response<SystemConfig>

    // Drivers (no auth required)
    @GET("api/drivers")
    suspend fun listDrivers(): Response<DriversResponse>

    @GET("api/drivers/{name}")
    suspend fun getDriver(@Path("name") name: String): Response<DriverInfo>

    // Boards (no auth required)
    @GET("api/boards")
    suspend fun listBoards(): Response<BoardsResponse>

    // Auth
    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    // LLM Intent (auth required)
    @POST("api/llm/intent")
    suspend fun processIntent(
        @Header("Authorization") auth: String,
        @Body request: IntentRequest
    ): Response<IntentResponse>

    // IR Compile (auth required)
    @POST("api/ir/compile")
    suspend fun compileIR(
        @Header("Authorization") auth: String,
        @Body request: CompileRequest
    ): Response<CompileResponse>

    // IR Validate (auth required)
    @POST("api/ir/validate")
    suspend fun validateIR(
        @Header("Authorization") auth: String,
        @Body ir: CompileRequest
    ): Response<Any>
}

/**
 * Singleton API client for the Parakram backend.
 * Connects to the Rust axum backend (default: localhost:8400 for dev, configurable for prod).
 */
object ParakramApiClient {
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8400/"

    private var baseUrl: String = DEFAULT_BASE_URL
    private var api: ParakramApi? = null
    private var authToken: String? = null

    private val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    fun configure(url: String = DEFAULT_BASE_URL) {
        baseUrl = if (url.endsWith("/")) url else "$url/"
        api = null
    }

    fun setAuthToken(token: String?) {
        authToken = token
    }

    fun getAuthHeader(): String = "Bearer ${authToken ?: ""}"

    fun getApi(): ParakramApi {
        return api ?: run {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            val client = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .build()

            retrofit.create(ParakramApi::class.java).also { api = it }
        }
    }
}
