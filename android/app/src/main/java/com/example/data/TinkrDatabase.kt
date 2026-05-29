package com.example.data

import androidx.room.*
import kotlinx.coroutines.flow.Flow

// --- 1. ENTITIES ---

@Entity(tableName = "boards")
data class BoardEntity(
    @PrimaryKey val address: String, // MAC or simulated ID
    val name: String,
    val colorHex: String,
    val firmwareVersion: String = "1.0.0",
    val manifestJson: String = "{}",
    val isConnected: Boolean = false,
    val lastSyncTime: Long = System.currentTimeMillis()
)

@Entity(tableName = "projects")
data class ProjectEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val name: String,
    val description: String,
    val codeContent: String = "",
    val blocklyXml: String = "",
    val configJson: String = "{}",
    val templateType: String = "Custom", // SmartPlanter, WeatherStation, etc.
    val isLocal: Boolean = true,
    val createdAt: Long = System.currentTimeMillis(),
    val lastModifiedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "sensor_logs")
data class SensorLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val boardAddress: String,
    val sensorKey: String, // e.g. "temperature", "light"
    val value: Double,
    val timestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "ai_chats")
data class AIChatEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sessionId: String, // "default_session"
    val role: String, // "user", "assistant"
    val mode: String, // "Builder", "Analyst", "Teacher"
    val messageText: String,
    val codeBlob: String = "",
    val actionsJson: String = "[]",
    val timestamp: Long = System.currentTimeMillis()
)

// --- 2. DAOS ---

@Dao
interface BoardDao {
    @Query("SELECT * FROM boards ORDER BY lastSyncTime DESC")
    fun getAllBoards(): Flow<List<BoardEntity>>

    @Query("SELECT * FROM boards WHERE isConnected = 1 LIMIT 1")
    fun getActiveBoard(): Flow<BoardEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBoard(board: BoardEntity)

    @Update
    suspend fun updateBoard(board: BoardEntity)

    @Query("UPDATE boards SET isConnected = 0")
    suspend fun disconnectAllBoards()

    @Query("UPDATE boards SET isConnected = 1 WHERE address = :address")
    suspend fun setActiveBoard(address: String)

    @Delete
    suspend fun deleteBoard(board: BoardEntity)
}

@Dao
interface ProjectDao {
    @Query("SELECT * FROM projects ORDER BY lastModifiedAt DESC")
    fun getAllProjects(): Flow<List<ProjectEntity>>

    @Query("SELECT * FROM projects WHERE id = :id")
    suspend fun getProjectById(id: Int): ProjectEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProject(project: ProjectEntity): Long

    @Update
    suspend fun updateProject(project: ProjectEntity)

    @Delete
    suspend fun deleteProject(project: ProjectEntity)
}

@Dao
interface SensorLogDao {
    @Query("SELECT * FROM sensor_logs WHERE boardAddress = :boardAddress AND sensorKey = :sensorKey ORDER BY timestamp DESC LIMIT 50")
    fun getRecentLogs(boardAddress: String, sensorKey: String): Flow<List<SensorLogEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLog(log: SensorLogEntity)

    @Query("DELETE FROM sensor_logs WHERE timestamp < :cutoffTime")
    suspend fun pruneOldLogs(cutoffTime: Long)
}

@Dao
interface AIChatDao {
    @Query("SELECT * FROM ai_chats WHERE sessionId = :sessionId ORDER BY timestamp ASC")
    fun getChatsForSession(sessionId: String): Flow<List<AIChatEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChat(chat: AIChatEntity)

    @Query("DELETE FROM ai_chats WHERE sessionId = :sessionId")
    suspend fun clearSession(sessionId: String)
}

// --- 3. DATABASE ---

@Database(
    entities = [
        BoardEntity::class,
        ProjectEntity::class,
        SensorLogEntity::class,
        AIChatEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class TinkrDatabase : RoomDatabase() {
    abstract fun boardDao(): BoardDao
    abstract fun projectDao(): ProjectDao
    abstract fun sensorLogDao(): SensorLogDao
    abstract fun aiChatDao(): AIChatDao

    companion object {
        @Volatile
        private var INSTANCE: TinkrDatabase? = null

        fun getDatabase(context: android.content.Context): TinkrDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = androidx.room.Room.databaseBuilder(
                    context.applicationContext,
                    TinkrDatabase::class.java,
                    "tinkr_database"
                )
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
