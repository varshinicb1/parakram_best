# Parakram API Reference & Code Contracts 📖

This document provides a detailed API reference for the publicly exposed classes, interfaces, and methods within Parakram's **Data** and **Domain/Protocol** layers. Maintainers should refer to this documentation to ensure type safety and API consistency when extending the platform.

---

## 1. Data Layer APIs (`com.example.data`)

This package is responsible for managing all local storage, relational database tables via Room DB, and key-value user settings via DataStore Preferences.

### 1.1 TinkrDatabase

The central coordination database class. Integrates SQLite persistence via a Room wrapper with thread-safe singleton initialization.

*   **Inherits From**: `RoomDatabase`
*   **Annotations**:
    *   `@Database(entities = [BoardEntity::class, ProjectEntity::class, SensorLogEntity::class, AIChatEntity::class], version = 1, exportSchema = false)`
*   **Public Accessors**:
    *   `abstract fun boardDao(): BoardDao`
    *   `abstract fun projectDao(): ProjectDao`
    *   `abstract fun sensorLogDao(): SensorLogDao`
    *   `abstract fun aiChatDao(): AIChatDao`
*   **Companion Object Methods**:
    *   `fun getDatabase(context: Context): TinkrDatabase`
        *   Returns the synchronized, thread-safe database instance. It uses destructive fallback migration mappings during schema updates.
        *   *Thread Safety*: Fully thread-safe through a volatile instance and double-checked synchronization block.

---

### 1.2 Board Entities & BoardDao

Manages hardware properties, paired microcontrollers, and registered development boards.

#### `BoardEntity` (Data Class)
*   **Properties**:
    *   `val address: String` (Primary Key - MAC address or simulated board ID string)
    *   `val name: String` (User-friendly name of the board, e.g., "Parakram-ESP32-SmartGarden")
    *   `val colorHex: String` (Graphic color accent, encoded as a Hex string)
    *   `val firmwareVersion: String` (Standard SemVer string, defaults to `"1.0.0"`)
    *   `val manifestJson: String` (Serialized `HardwareManifest` JSON schema describing pinouts and sensors, defaults to `"{}"`)
    *   `val isConnected: Boolean` (Active Bluetooth connection status, defaults to `false`)
    *   `val lastSyncTime: Long` (Epoch millisecond timestamp of last connection sync, defaults to `System.currentTimeMillis()`)

#### `BoardDao` (Interface)
*   **Methods**:
    *   `fun getAllBoards(): Flow<List<BoardEntity>>`
        *   Stream containing all scanned and registered boards in the database, ordered by `lastSyncTime` descending.
    *   `fun getActiveBoard(): Flow<BoardEntity?>`
        *   Stream returning the currently active or connected board, if one exists.
    *   `suspend fun insertBoard(board: BoardEntity): Unit`
        *   Inserts or updates (using `OnConflictStrategy.REPLACE`) a configuration board.
    *   `suspend fun updateBoard(board: BoardEntity): Unit`
        *   Updates active properties of a board.
    *   `suspend fun disconnectAllBoards(): Unit`
        *   Batch operation setting `isConnected = 0` across all registered devices. Typically triggered on core disconnect or boot.
    *   `suspend fun setActiveBoard(address: String): Unit`
        *   Flags a specific board as connected (`isConnected = 1`) by its MAC address.
    *   `suspend fun deleteBoard(board: BoardEntity): Unit`
        *   Removes a board from the local database.

---

### 1.3 Project Entities & ProjectDao

Manages sandbox workspaces, templates, blockly sketches, and physical computing source codes.

#### `ProjectEntity` (Data Class)
*   **Properties**:
    *   `val id: Int` (Primary Key - auto-generated, defaults to `0`)
    *   `val name: String` (The title of the project files sandbox)
    *   `val description: String` (Explanatory notes or assistant generation details)
    *   `val codeContent: String` (Arduino/C++ or Python microcontroller script contents, defaults to `""`)
    *   `val blocklyXml: String` (XML layout configuration for Blockly visual nodes, defaults to `""`)
    *   `val configJson: String` (Secondary JSON schema mapping project properties, defaults to `"{}"`)
    *   `val templateType: String` (Workspace design template category, e.g., `"SmartPlanter"`, `"WeatherStation"`, or `"Custom"`)
    *   `val isLocal: Boolean` (If stored local-only or synced, defaults to `true`)
    *   `val createdAt: Long` (Timestamp, defaults to `System.currentTimeMillis()`)
    *   `val lastModifiedAt: Long` (Timestamp, defaults to `System.currentTimeMillis()`)

#### `ProjectDao` (Interface)
*   **Methods**:
    *   `fun getAllProjects(): Flow<List<ProjectEntity>>`
        *   Stream returning all active projects, ordered by date modified.
    *   `suspend fun getProjectById(id: Int): ProjectEntity?`
        *   Retrieves a project definition by its database ID.
    *   `suspend fun insertProject(project: ProjectEntity): Long`
        *   Inserts a new project into SQLite, returning its auto-assigned ID.
    *   `suspend fun updateProject(project: ProjectEntity): Unit`
        *   Updates an existing workspace's code, structure, and metadata.
    *   `suspend fun deleteProject(project: ProjectEntity): Unit`
        *   Deletes a project.

---

### 1.4 SensorLog Entities & SensorLogDao

Maintains high-frequency telemetry logs streamed over BLE.

#### `SensorLogEntity` (Data Class)
*   **Properties**:
    *   `val id: Long` (Primary Key - auto-generated, defaults to `0`)
    *   `val boardAddress: String` (Foreign link mapping MAC or simulated board address)
    *   `val sensorKey: String` (The sensor key, e.g., `"temp_0"`, `"light_0"`)
    *   `val value: Double` (Numeric float data)
    *   `val timestamp: Long` (Defaults to system time)

#### `SensorLogDao` (Interface)
*   **Methods**:
    *   `fun getRecentLogs(boardAddress: String, sensorKey: String): Flow<List<SensorLogEntity>>`
        *   Returns up to the 50 most recent logs for a specific sensor, used to drive real-time instrumentation graphs.
    *   `suspend fun insertLog(log: SensorLogEntity): Unit`
        *   Inserts a telemetry log record.
    *   `suspend fun pruneOldLogs(cutoffTime: Long): Unit`
        *   Removes historical points recorded before the cutoff epoch to control database size.

---

### 1.5 AIChat Entities & AIChatDao

Stores chatbot conversations and associated agent metadata.

#### `AIChatEntity` (Data Class)
*   **Properties**:
    *   `val id: Long` (Primary Key - auto-generated)
    *   `val sessionId: String` (Unique dialogue thread ID, default `"default_session"`)
    *   `val role: String` (`"user"` or `"assistant"`)
    *   `val mode: String` (Active engine mode during chat prompt: `"Builder"`, `"Analyst"`, or `"Teacher"`)
    *   `val messageText: String` (Parsed conversation body)
    *   `val codeBlob: String` (Microcontroller source sketch generated by AI, defaults to `""`)
    *   `val actionsJson: String` (Serialized string list matching the dispatched action models, defaults to `"[]"`)
    *   `val timestamp: Long` (Defaults to current time)

#### `AIChatDao` (Interface)
*   **Methods**:
    *   `fun getChatsForSession(sessionId: String): Flow<List<AIChatEntity>>`
        *   Returns active dialogue steps for a given session, sorted chronologically.
    *   `suspend fun insertChat(chat: AIChatEntity): Unit`
        *   Saves a conversational turn.
    *   `suspend fun clearSession(sessionId: String): Unit`
        *   Deletes conversation history, typically on workspace reset.

---

### 1.6 SettingsRepository

The central class managing application preferences via androidx.datastore.

*   **Public Accessor Fields**:
    *   `val languageFlow: Flow<String>` (Emitter for localization codes, defaults to `"en"`)
    *   `val personaFlow: Flow<String>` (Emitter for active AI agent personas: `"engineer"`, `"analyst"`, etc.)
    *   `val activeBoardFlow: Flow<String>` (MAC address of the connected board)
    *   `val isSimulatorModeFlow: Flow<Boolean>` (Simulator mode toggle, defaults to `true`)
    *   `val isLocalModelDownloadedFlow: Flow<Boolean>` (If local offline weights are cached, defaults to `false`)
    *   `val isOnboardingCompletedFlow: Flow<Boolean>` (If tutorial onboarding has been completed, defaults to `false`)
*   **Modifier Methods**:
    *   `suspend fun setLanguage(languageCode: String): Unit`
    *   `suspend fun setPersona(personaId: String): Unit`
    *   `suspend fun setActiveBoardAddress(address: String): Unit`
    *   `suspend fun setSimulatorMode(enabled: Boolean): Unit`
    *   `suspend fun setLocalModelDownloaded(downloaded: Boolean): Unit`
    *   `suspend fun setOnboardingCompleted(completed: Boolean): Unit`

---

## 2. Domain & Protocol APIs (`com.example.protocol`)

Handles hardware messaging data shapes, Bluetooth Low Energy packet serializations, and device manifests.

### 2.1 SensorStreamMessage (Data Class)
Lower-level serialized packet structure for streaming high-frequency sensor readings.
*   **Properties**:
    *   `val t: Long` (Unix millisecond timestamp)
    *   `val s: String` (The sensor key, e.g., `"temp_0"`, `"moist_0"`)
    *   `val v: Double` (Numeric telemetry value)
    *   `val u: String` (The measurement unit output, e.g., `"°C"`, `"lx"`, `"%"` or `"ppm"`)

### 2.2 CommandMessage (Data Class)
Uniform physical output instruction wrapper sent from Android to the microcontroller or emulator.
*   **Properties**:
    *   `val cmd: String` (Identifier command category: `"set_gpio"`, `"play_tone"`, `"servo_angle"`, `"display"`, or `"flash_ota"`)
    *   `val pin: Int?` (Target physical microcontroller register pin number, optional)
    *   `val mode: String?` (Pin initialization direction: `"output"`, `"input"`, or `"input_pullup"`, optional)
    *   `val value: Int?` (Digital state value: `0`/`1` or PWM duty cycles, optional)
    *   `val text: String?` (Text for the ST7789 display screen buffer or diagnostic outputs, optional)
    *   `val frequency: Int?` (Buzzer alarm frequency, in Hertz, optional)

### 2.3 Hardware Sensor & Capabilities Modifiers
Allows the application to parse connected profiles dynamically.

#### `HardwareSensorInfo` (Data Class)
Describes an available sensor on the active board.
*   **Properties**:
    *   `val key: String`, `val name: String`, `val type: String`, `val unit: String`, `val pin: Int`

#### `HardwareCapability` (Data Class)
Catalogs physical interface peripherals connected to the microcontroller.
*   **Properties**:
    *   `val name: String`, `val description: String`, `val type: String` (e.g., `"GPIO"`, `"I2C"`, `"ADC"`, `"PWM"`, `"TFT"`, `"AUDIO"`)

#### `HardwareManifest` (Data Class)
The complete hardware specification template.
*   **Properties**:
    *   `val manifest_version: String`, `val firmware_version: String`, `val sensors: List<HardwareSensorInfo>`, `val capabilities: List<HardwareCapability>`

---

### 2.4 TinkrProtocol (Object Helper)

A high-performance formatting and parsing utility using Moshi handles.

*   **Public Serialization & Parsing Functions**:
    *   `fun parseSensorMsg(json: String): SensorStreamMessage?`
    *   `fun serializeSensorMsg(msg: SensorStreamMessage): String`
    *   `fun parseCommand(json: String): CommandMessage?`
    *   `fun serializeCommand(msg: CommandMessage): String`
    *   `fun parseManifest(json: String): HardwareManifest?`
    *   `fun serializeManifest(manifest: HardwareManifest): String`
    *   `fun getDefaultESP32S3Manifest(): HardwareManifest`
        *   Returns a standard manifest matching the default hardware layout (ESP32-S3 IoT kit with temperature, ambient lux, soil hydration probe, relay water pump, servo articulation, active sirens, and ST7789 TFT screens).
