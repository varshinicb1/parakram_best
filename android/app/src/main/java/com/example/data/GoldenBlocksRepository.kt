package com.example.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

data class GoldenBlock(
    val name: String,
    val displayName: String,
    val driverType: String,
    val busTypes: List<String>,
    val capabilities: List<String>,
    val description: String
)

data class BackendStatus(
    val connected: Boolean,
    val version: String = "",
    val driverCount: Int = 0,
    val llmAvailable: Boolean = false,
    val database: String = "unknown"
)

/**
 * Repository that fetches driver data from the Parakram backend
 * and exposes it as observable state for the UI.
 */
class GoldenBlocksRepository private constructor() {

    private val _blocks = MutableStateFlow<List<GoldenBlock>>(emptyList())
    val blocks: StateFlow<List<GoldenBlock>> = _blocks.asStateFlow()

    private val _backendStatus = MutableStateFlow(BackendStatus(connected = false))
    val backendStatus: StateFlow<BackendStatus> = _backendStatus.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    companion object {
        private const val TAG = "GoldenBlocks"

        @Volatile
        private var INSTANCE: GoldenBlocksRepository? = null

        fun getInstance(): GoldenBlocksRepository {
            return INSTANCE ?: synchronized(this) {
                GoldenBlocksRepository().also { INSTANCE = it }
            }
        }
    }

    suspend fun checkBackendHealth() = withContext(Dispatchers.IO) {
        try {
            val api = ParakramApiClient.getApi()
            val response = api.health()
            if (response.isSuccessful) {
                val health = response.body()!!
                _backendStatus.value = BackendStatus(
                    connected = true,
                    version = health.version,
                    driverCount = health.registeredDrivers,
                    llmAvailable = health.llmAvailable,
                    database = health.database
                )
                Log.i(TAG, "Backend connected: v${health.version}, ${health.registeredDrivers} drivers")
            } else {
                _backendStatus.value = BackendStatus(connected = false)
                Log.w(TAG, "Backend health check failed: ${response.code()}")
            }
        } catch (e: Exception) {
            _backendStatus.value = BackendStatus(connected = false)
            Log.d(TAG, "Backend unreachable: ${e.message}")
        }
    }

    suspend fun fetchDrivers() = withContext(Dispatchers.IO) {
        _isLoading.value = true
        try {
            val api = ParakramApiClient.getApi()
            val response = api.listDrivers()
            if (response.isSuccessful) {
                val drivers = response.body()?.drivers ?: emptyList()
                _blocks.value = drivers.map { driver ->
                    GoldenBlock(
                        name = driver.name,
                        displayName = driver.displayName.ifEmpty { driver.name },
                        driverType = driver.driverType,
                        busTypes = driver.busTypes,
                        capabilities = driver.capabilities,
                        description = driver.description
                    )
                }
                Log.i(TAG, "Loaded ${drivers.size} drivers from backend")
            } else {
                Log.w(TAG, "Failed to load drivers: ${response.code()}")
            }
        } catch (e: Exception) {
            Log.d(TAG, "Failed to fetch drivers: ${e.message}")
        } finally {
            _isLoading.value = false
        }
    }

    suspend fun refreshAll() {
        checkBackendHealth()
        fetchDrivers()
    }
}
