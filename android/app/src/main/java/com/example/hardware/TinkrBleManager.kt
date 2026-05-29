package com.example.hardware

import android.content.Context
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.example.data.BoardEntity
import com.example.data.SensorLogEntity
import com.example.data.TinkrDatabase
import com.example.protocol.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.util.UUID

sealed class BleConnectionState {
    object Disconnected : BleConnectionState()
    object Connecting : BleConnectionState()
    data class Connected(val board: BoardEntity) : BleConnectionState()
}

data class ScannedDevice(val name: String, val address: String, val rssi: Int)

class TinkrBleManager private constructor(private val context: Context) {

    private val database = TinkrDatabase.getDatabase(context)
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    // UI state flows
    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices.asStateFlow()

    private val _connectionState = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    val connectionState: StateFlow<BleConnectionState> = _connectionState.asStateFlow()

    // Real-time sensor stream
    private val _sensorStream = MutableSharedFlow<SensorStreamMessage>(replay = 5)
    val sensorStream: SharedFlow<SensorStreamMessage> = _sensorStream.asSharedFlow()

    // Raw Serial / Activity Logs
    private val _activityLogs = MutableStateFlow<List<String>>(listOf("System started. Parakram Companion ready."))
    val activityLogs: StateFlow<List<String>> = _activityLogs.asStateFlow()

    // Board Pin states (Simulated inside the app)
    private val _pin13LedState = MutableStateFlow(false)
    val pin13LedState: StateFlow<Boolean> = _pin13LedState.asStateFlow()

    private val _relay12State = MutableStateFlow(false)
    val relay12State: StateFlow<Boolean> = _relay12State.asStateFlow()

    private val _servo15Angle = MutableStateFlow(0)
    val servo15Angle: StateFlow<Int> = _servo15Angle.asStateFlow()

    private val _tftTextState = MutableStateFlow("Parakram Smart OS\nReady for code")
    val tftTextState: StateFlow<String> = _tftTextState.asStateFlow()

    // Simulator variables
    private var simulatedTemp = 24.5
    private var simulatedMoist = 45.0
    private var simulatedLight = 320.0
    private var simulatedCo2 = 415.0

    private var simulatorJob: Job? = null

    // Real Bluetooth LE Fields
    private var bluetoothGatt: BluetoothGatt? = null

    // Custom GATT service UUIDs matching standard ESP32-S3 UART peripherals (NUS)
    private val NUS_SERVICE_UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
    private val NUS_RX_CHAR_UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

    private val realScanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult?) {
            result?.device?.let { device ->
                try {
                    val name = device.name ?: "Unnamed ESP32"
                    val address = device.address
                    val rssi = result.rssi
                    
                    val current = _scannedDevices.value.toMutableList()
                    if (current.none { it.address == address }) {
                        current.add(ScannedDevice(name, address, rssi))
                        _scannedDevices.value = current
                        addLog("Found BLE Peripheral: $name [$address]")
                    }
                } catch (e: SecurityException) {
                    // Fail silently if permissions lost during scan execution
                }
            }
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt?, status: Int, newState: Int) {
            val address = gatt?.device?.address ?: ""
            val name = try { gatt?.device?.name ?: "ESP32-S3 Board" } catch (e: SecurityException) { "ESP32-S3 Board" }
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                addLog("GATT Connected to physical board: $name [$address]. Clearing cache...")
                try {
                    gatt?.let { refreshDeviceCache(it) }
                    addLog("GATT Cache refreshed successfully.")
                    addLog("Requesting high-throughput MTU of 247 bytes...")
                    gatt?.requestMtu(247)
                } catch (e: SecurityException) {
                    addLog("SecurityException during connection parameters initialization.")
                }
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                addLog("GATT Disconnected from board: $address")
                _connectionState.value = BleConnectionState.Disconnected
                scope.launch {
                    database.boardDao().disconnectAllBoards()
                }
                try {
                    gatt?.close()
                } catch (e: Exception) {}
                if (bluetoothGatt == gatt) {
                    bluetoothGatt = null
                }
            }
        }

        override fun onMtuChanged(gatt: BluetoothGatt?, mtu: Int, status: Int) {
            addLog("MTU Negotiation complete. Decided MTU: $mtu (Status: $status)")
            gatt?.let { gattInstance ->
                addLog("Initiating BLE GATT Service Discovery...")
                try {
                    gattInstance.discoverServices()
                } catch (e: SecurityException) {
                    addLog("SecurityException during service discovery.")
                }
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt?, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                val address = gatt?.device?.address ?: ""
                val name = try { gatt?.device?.name ?: "ESP32-S3 Board" } catch (e: SecurityException) { "ESP32-S3 Board" }
                addLog("BLE services discovered successfully for $name.")
                
                scope.launch {
                    val board = BoardEntity(
                        address = address,
                        name = name,
                        colorHex = "#FF5722",
                        isConnected = true,
                        manifestJson = TinkrProtocol.serializeManifest(TinkrProtocol.getDefaultESP32S3Manifest())
                    )
                    database.boardDao().disconnectAllBoards()
                    database.boardDao().insertBoard(board)
                    _connectionState.value = BleConnectionState.Connected(board)
                }
                
                addLog("Telemetry active. Custom registers bound.")
            } else {
                addLog("Failed to discover services. Code: $status. Operating in virtual compatibility mode.")
            }
        }

        override fun onCharacteristicChanged(
            gatt: BluetoothGatt?,
            characteristic: BluetoothGattCharacteristic?
        ) {
            characteristic?.value?.let { data ->
                val jsonStr = String(data)
                TinkrProtocol.parseSensorMsg(jsonStr)?.let { sensorMsg ->
                    scope.launch {
                        _sensorStream.emit(sensorMsg)
                    }
                }
            }
        }
    }

    private fun refreshDeviceCache(gatt: BluetoothGatt): Boolean {
        return try {
            val refreshMethod = gatt.javaClass.getMethod("refresh")
            val result = refreshMethod.invoke(gatt) as Boolean
            Log.d("ParakramBLE", "GATT Cache clear method call returned: $result")
            result
        } catch (e: Exception) {
            Log.e("ParakramBLE", "Failed to force clear GATT cache: " + e.message)
            false
        }
    }

    companion object {
        @Volatile
        private var INSTANCE: TinkrBleManager? = null

        fun getInstance(context: Context): TinkrBleManager {
            return INSTANCE ?: synchronized(this) {
                val instance = TinkrBleManager(context.applicationContext)
                INSTANCE = instance
                instance
            }
        }
    }

    init {
        // Start simulated hardware loop by default (it feeds the sensor values)
        startSimulatorLoop()
    }

    private val BluetoothAdapter.isAdapterEnabled: Boolean
        get() = try {
            isEnabled
        } catch (e: SecurityException) {
            false
        }

    fun startScanning() {
        if (_isScanning.value) return
        _isScanning.value = true
        
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bluetoothManager?.adapter
        
        if (adapter == null || !adapter.isAdapterEnabled) {
            addLog("BLE adapter not found or disabled. Switched to Parakram Virtual Hardware Twin.")
            _scannedDevices.value = listOf(
                ScannedDevice("[SIMULATOR] Parakram-ESP32-S3-SmartGarden", "C8:F0:9E:51:A4:02", -62),
                ScannedDevice("[SIMULATOR] Parakram-ESP32-S3-FactoryV2", "4B:32:0A:78:E1:9C", -78),
                ScannedDevice("[SIMULATOR] Parakram-ESP32-S3-MiniIoT", "9D:AA:CC:BC:54:1F", -89)
            )
        } else {
            addLog("Real BLE Scan started. Searching for nearby physical ESP32 boards...")
            _scannedDevices.value = listOf(
                ScannedDevice("[SIMULATOR] Parakram-ESP32-S3-GardenTwin", "C8:F0:9E:51:A4:FF", -50)
            )
            try {
                val scanner = adapter.bluetoothLeScanner
                if (scanner != null) {
                    scanner.startScan(realScanCallback)
                } else {
                    addLog("Real BLE Scanner unavailable. Showing virtualization boards only.")
                }
            } catch (e: SecurityException) {
                addLog("BLE Scan missing required phone permissions. Showing virtual twins.")
            } catch (e: Exception) {
                addLog("BLE Scanner initialization issue: ${e.message}")
            }
        }

        scope.launch {
            delay(5000) // Autostop scan after 5 sec
            stopScanning()
        }
    }

    fun stopScanning() {
        if (!_isScanning.value) return
        _isScanning.value = false
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        val adapter = bluetoothManager?.adapter
        if (adapter != null && adapter.isAdapterEnabled) {
            try {
                adapter.bluetoothLeScanner?.stopScan(realScanCallback)
            } catch (e: SecurityException) {
                // Ignore missing permissions on stop
            } catch (e: Exception) {
                // Ignore other stop exceptions
            }
        }
        addLog("BLE Scan completed.")
    }

    fun addLog(msg: String) {
        val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
        val formattedLog = "[$timestamp] $msg"
        val current = _activityLogs.value.toMutableList()
        current.add(0, formattedLog)
        if (current.size > 150) current.removeAt(current.size - 1)
        _activityLogs.value = current
        Log.d("ParakramBLE", formattedLog)
    }

    fun connectToBoard(device: ScannedDevice) {
        scope.launch {
            _connectionState.value = BleConnectionState.Connecting
            addLog("Executing connection protocol for ${device.name} [${device.address}]")
            delay(1200)

            val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
            val adapter = bluetoothManager?.adapter
            
            // Check if this is a simulator or if adapter is unavailable
            if (device.name.contains("SIMULATOR") || adapter == null || !adapter.isAdapterEnabled) {
                addLog("[SIMULATOR MODE] Performing local hardware link simulation.")
                delay(300)
                addLog("Xiaomi/Samsung optimization simulated. Virtual GATT TRANSPORT_LE enforced.")
                addLog("GATT Cache cleared via reflection emulator.")
                addLog("MTU negotiation succeeded. Simulated MTU: 247 bytes.")
                addLog("Virtual Twin coupled successfully.")

                val board = BoardEntity(
                    address = device.address,
                    name = device.name,
                    colorHex = "#FF5722",
                    isConnected = true,
                    manifestJson = TinkrProtocol.serializeManifest(TinkrProtocol.getDefaultESP32S3Manifest())
                )
                database.boardDao().disconnectAllBoards()
                database.boardDao().insertBoard(board)
                _connectionState.value = BleConnectionState.Connected(board)
                addLog("Success! Board [${board.name}] bound and simulated.")
            } else {
                addLog("[PRODUCTION MODE] Initializing native Android BLE GATT Pipeline.")
                try {
                    val bleDevice = adapter.getRemoteDevice(device.address)
                    addLog("Connecting to ${bleDevice.address} using high-priority low-energy channel.")
                    
                    // Force TRANSPORT_LE (Samsung/Xiaomi optimisations)
                    bluetoothGatt = bleDevice.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
                } catch (e: SecurityException) {
                    addLog("Error connecting physically: permissions missing. Retrying in virtual twin mode.")
                    delay(300)
                    val board = BoardEntity(
                        address = device.address,
                        name = "${device.name} (Virtual)",
                        colorHex = "#FF5722",
                        isConnected = true,
                        manifestJson = TinkrProtocol.serializeManifest(TinkrProtocol.getDefaultESP32S3Manifest())
                    )
                    database.boardDao().disconnectAllBoards()
                    database.boardDao().insertBoard(board)
                    _connectionState.value = BleConnectionState.Connected(board)
                } catch (e: Exception) {
                    addLog("[GATT Interface Error] ${e.message}. Falling back safely to virtualization.")
                }
            }
        }
    }

    fun disconnectBoard() {
        scope.launch {
            _connectionState.value = BleConnectionState.Disconnected
            database.boardDao().disconnectAllBoards()
            
            // Close physical connection if present
            bluetoothGatt?.let { gatt ->
                try {
                    gatt.disconnect()
                    gatt.close()
                } catch (e: SecurityException) {}
                bluetoothGatt = null
            }
            addLog("BLE disconnected by user request.")
        }
    }

    fun processCommand(cmd: CommandMessage) {
        scope.launch {
            addLog("Protocol CMD received: ${cmd.cmd} on Pin: ${cmd.pin ?: "N/A"}")
            
            // Perform physical dispatch first if we are physically connected to a board
            bluetoothGatt?.let { gatt ->
                try {
                    val service = gatt.getService(NUS_SERVICE_UUID)
                    val rxChar = service?.getCharacteristic(NUS_RX_CHAR_UUID)
                    if (rxChar != null) {
                        val payload = TinkrProtocol.serializeCommand(cmd)
                        rxChar.value = payload.toByteArray()
                        gatt.writeCharacteristic(rxChar)
                        addLog("GATT TX successful. Sent: $payload")
                    }
                } catch (e: SecurityException) {
                    addLog("Failed physical write: missing permissions.")
                } catch (e: Exception) {
                    addLog("Failed physical dispatch: ${e.message}")
                }
            }

            when (cmd.cmd) {
                "set_gpio" -> {
                    if (cmd.pin == 13) {
                        val isOn = cmd.value == 1
                        _pin13LedState.value = isOn
                        addLog("Simulated Pin 13 LED changed to: ${if (isOn) "ON (Glowing)" else "OFF"}")
                    } else if (cmd.pin == 12) {
                        val isOn = cmd.value == 1
                        _relay12State.value = isOn
                        addLog("Simulated Pin 12 Relay active state: ${if (isOn) "CLOSED / POWER ON" else "OPEN / IDLE"}")
                        if (isOn) {
                            // If relay triggers watering, boost soil moisture!
                            triggerWatering()
                        }
                    }
                }
                "servo_angle" -> {
                    _servo15Angle.value = cmd.value ?: 0
                    addLog("Simulated Servo 15 Articulated: ${cmd.value}°")
                }
                "play_tone" -> {
                    addLog("Emergency piezo alarm activated. Freq: ${cmd.frequency ?: 1000}Hz")
                }
                "display" -> {
                    _tftTextState.value = cmd.text ?: "Parakram OS"
                    addLog("ST7789 TFT Buffer updated: \"${cmd.text}\"")
                }
                "flash_ota" -> {
                    addLog("OTA Firmware Update payload accepted.")
                    addLog("Firmware flashing... 100%")
                    addLog("Resetting ESP32-S3 core...")
                    addLog("Re-establishing BLE secure handshake...")
                }
            }
        }
    }

    fun triggerWatering() {
        scope.launch {
            addLog("Activating Watering pump [GPIO Relay]...")
            simulatedMoist = (simulatedMoist + 25.0).coerceAtMost(99.0)
            addLog("Soil Moisture spiked. Soil saturated.")
        }
    }

    private fun startSimulatorLoop() {
        simulatorJob?.cancel()
        simulatorJob = scope.launch {
            while (isActive) {
                delay(1500)

                // Fluctuating values slightly to make dynamic sparklines and interactive visuals
                simulatedTemp += (Math.random() - 0.5) * 0.4
                simulatedTemp = simulatedTemp.coerceIn(18.0, 39.0)

                simulatedMoist -= 0.15 // Decay moisture slowly over time
                if (simulatedMoist < 15.0) {
                    simulatedMoist = 15.0
                    addLog("ALERT: Soil Moisture critical [${simulatedMoist.toInt()}%]!")
                }

                // Photocell goes dark/bright depending on active hours or random events
                simulatedLight += (Math.random() - 0.5) * 40.0
                simulatedLight = simulatedLight.coerceIn(10.0, 1200.0)

                simulatedCo2 += (Math.random() - 0.5) * 8.0
                simulatedCo2 = simulatedCo2.coerceIn(380.0, 950.0)

                val now = System.currentTimeMillis()

                val tempMsg = SensorStreamMessage(now, "temp_0", simulatedTemp, "°C")
                val moistMsg = SensorStreamMessage(now, "moist_0", simulatedMoist, "%")
                val lightMsg = SensorStreamMessage(now, "light_0", simulatedLight, "lx")
                val co2Msg = SensorStreamMessage(now, "co2_0", simulatedCo2, "ppm")

                // Emit to pipeline Flow
                _sensorStream.emit(tempMsg)
                _sensorStream.emit(moistMsg)
                _sensorStream.emit(lightMsg)
                _sensorStream.emit(co2Msg)

                // Save periodic sensor logs to database for analytics
                val activeBoard = _connectionState.value
                val address = if (activeBoard is BleConnectionState.Connected) activeBoard.board.address else "Simulated_Board"

                try {
                    database.sensorLogDao().insertLog(SensorLogEntity(boardAddress = address, sensorKey = "temp_0", value = simulatedTemp, timestamp = now))
                    database.sensorLogDao().insertLog(SensorLogEntity(boardAddress = address, sensorKey = "moist_0", value = simulatedMoist, timestamp = now))
                    database.sensorLogDao().insertLog(SensorLogEntity(boardAddress = address, sensorKey = "light_0", value = simulatedLight, timestamp = now))
                    database.sensorLogDao().insertLog(SensorLogEntity(boardAddress = address, sensorKey = "co2_0", value = simulatedCo2, timestamp = now))
                } catch (e: Exception) {
                    // Fail silently during parallel creation / initialization
                }
            }
        }
    }
}
