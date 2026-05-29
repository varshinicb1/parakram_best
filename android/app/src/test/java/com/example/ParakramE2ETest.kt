package com.example

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.example.data.*
import com.example.hardware.TinkrBleManager
import com.example.hardware.ScannedDevice
import com.example.hardware.BleConnectionState
import com.example.protocol.*
import com.example.ui.TinkrTranslations
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.IOException

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ParakramE2ETest {

    private lateinit var db: TinkrDatabase
    private lateinit var projectDao: ProjectDao
    private lateinit var boardDao: BoardDao
    private lateinit var context: Context

    @Before
    fun createDb() {
        context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, TinkrDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        projectDao = db.projectDao()
        boardDao = db.boardDao()
    }

    @After
    @Throws(IOException::class)
    fun closeDb() {
        db.close()
    }

    @Test
    fun testDatabaseWriteAndReadProject() = runBlocking {
        val project = ProjectEntity(
            id = 1,
            name = "Smart Greenhouse Node",
            description = "E2E Test Scaffold",
            codeContent = "void setup() { pinMode(13, OUTPUT); }",
            templateType = "Greenhouse"
        )
        projectDao.insertProject(project)
        val allProjects = projectDao.getAllProjects().first()
        assertEquals(1, allProjects.size)
        assertEquals("Smart Greenhouse Node", allProjects[0].name)
        assertEquals("Greenhouse", allProjects[0].templateType)
    }

    @Test
    fun testTranslationsDictionary() {
        val appTabEn = TinkrTranslations.getString("home_tab", "en")
        val appTabHi = TinkrTranslations.getString("home_tab", "hi")
        val appTabTa = TinkrTranslations.getString("home_tab", "ta")

        assertEquals("Home", appTabEn)
        assertEquals("होम", appTabHi)
        assertEquals("முகப்பு", appTabTa)
    }

    @Test
    fun testProtocolCommandParsing() {
        val cmdJson = """{"cmd":"set_gpio","pin":13,"value":1}"""
        val parsed = TinkrProtocol.parseCommand(cmdJson)
        assertNotNull(parsed)
        assertEquals("set_gpio", parsed?.cmd)
        assertEquals(13, parsed?.pin)
        assertEquals(1, parsed?.value)
    }

    @Test
    fun testHardwareSimulatorTelemetryGeneration() {
        val defaultManifest = TinkrProtocol.getDefaultESP32S3Manifest()
        assertEquals("1", defaultManifest.manifest_version)
        assertTrue(defaultManifest.sensors.any { it.key == "temp_0" })
        assertTrue(defaultManifest.capabilities.any { it.type == "GPIO" })
    }

    @Test
    fun testLocalGemmaReasoningEngine() = runBlocking {
        val aiService = com.example.ai.TinkrAIService.getInstance(context)
        val response = aiService.runPrompt("Turn on status indicator LED 13")
        
        assertNotNull(response)
        assertTrue(response.message.contains("13") || response.message.lowercase().contains("gpio"))
        assertTrue(response.actions.isNotEmpty())
        assertEquals("writeGPIO", response.actions[0].toolName)
        assertTrue(response.codePreview.contains("pinMode") || response.codePreview.contains("void setup()"))
        assertEquals("Local Gemma 4 E2B (Simulated Local)", response.modelSource)
    }
}
