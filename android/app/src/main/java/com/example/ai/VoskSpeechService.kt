package com.example.ai

import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipInputStream

/**
 * Offline speech-to-text service using Vosk (alphacep/vosk-api).
 *
 * Provides real-time streaming transcription without requiring network access.
 * Model (~50MB) supports 20+ languages including Indian English.
 *
 * Usage:
 *   1. Call [initialize] with application context (downloads/extracts model once)
 *   2. Call [startListening] to begin transcription
 *   3. Collect [transcriptions] flow for partial + final results
 *   4. Call [stopListening] to stop
 *
 * The Vosk library AAR must be added to the project:
 *   implementation("com.alphacephei:vosk-android:0.3.47")
 *
 * Model is stored in app's internal files directory to avoid re-extraction.
 */
class VoskSpeechService private constructor(private val context: Context) {

    companion object {
        private const val TAG = "VoskSTT"
        private const val MODEL_DIR = "vosk-model"
        private const val MODEL_ASSET = "vosk-model-small-en-in-0.4.zip"
        private const val SAMPLE_RATE = 16000f

        @Volatile
        private var INSTANCE: VoskSpeechService? = null

        fun getInstance(context: Context): VoskSpeechService {
            return INSTANCE ?: synchronized(this) {
                val instance = VoskSpeechService(context.applicationContext)
                INSTANCE = instance
                instance
            }
        }
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val _state = MutableStateFlow(State.UNINITIALIZED)
    val state: StateFlow<State> = _state.asStateFlow()

    private val _transcriptions = MutableSharedFlow<TranscriptionResult>(extraBufferCapacity = 64)
    val transcriptions: SharedFlow<TranscriptionResult> = _transcriptions.asSharedFlow()

    private val _modelProgress = MutableStateFlow(0f)
    val modelProgress: StateFlow<Float> = _modelProgress.asStateFlow()

    // Vosk objects — loaded reflectively to avoid hard compile dependency
    private var recognizer: Any? = null
    private var model: Any? = null
    private var speechService: Any? = null

    enum class State {
        UNINITIALIZED, LOADING_MODEL, READY, LISTENING, ERROR
    }

    data class TranscriptionResult(
        val text: String,
        val isFinal: Boolean,
        val confidence: Float = 0f
    )

    /**
     * Initialize the Vosk model. Call once at app startup.
     * Extracts the model from assets if not already extracted.
     */
    fun initialize() {
        if (_state.value != State.UNINITIALIZED) return

        scope.launch {
            try {
                _state.value = State.LOADING_MODEL
                val modelPath = extractModelIfNeeded()

                if (modelPath != null) {
                    loadModel(modelPath)
                    _state.value = State.READY
                    Log.i(TAG, "Vosk model loaded from $modelPath")
                } else {
                    Log.w(TAG, "Model not available — Vosk AAR or model asset not bundled")
                    _state.value = State.READY
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize Vosk: ${e.message}")
                _state.value = State.ERROR
            }
        }
    }

    fun startListening() {
        if (_state.value != State.READY) {
            Log.w(TAG, "Cannot start listening in state ${_state.value}")
            return
        }

        scope.launch {
            try {
                _state.value = State.LISTENING
                startRecognition()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start listening: ${e.message}")
                _state.value = State.ERROR
            }
        }
    }

    fun stopListening() {
        scope.launch {
            try {
                stopRecognition()
                _state.value = State.READY
            } catch (e: Exception) {
                Log.e(TAG, "Failed to stop listening: ${e.message}")
            }
        }
    }

    fun processAudioBuffer(buffer: ShortArray, length: Int) {
        if (_state.value != State.LISTENING) return

        scope.launch {
            try {
                val rec = recognizer ?: return@launch
                val acceptMethod = rec.javaClass.getMethod("acceptWaveForm", ShortArray::class.java, Int::class.javaPrimitiveType)
                val accepted = acceptMethod.invoke(rec, buffer, length) as Boolean

                if (accepted) {
                    val resultMethod = rec.javaClass.getMethod("getResult")
                    val resultJson = resultMethod.invoke(rec) as String
                    val json = JSONObject(resultJson)
                    val text = json.optString("text", "")
                    if (text.isNotBlank()) {
                        _transcriptions.emit(TranscriptionResult(text, isFinal = true))
                    }
                } else {
                    val partialMethod = rec.javaClass.getMethod("getPartialResult")
                    val partialJson = partialMethod.invoke(rec) as String
                    val json = JSONObject(partialJson)
                    val text = json.optString("partial", "")
                    if (text.isNotBlank()) {
                        _transcriptions.emit(TranscriptionResult(text, isFinal = false))
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Audio processing error: ${e.message}")
            }
        }
    }

    private suspend fun extractModelIfNeeded(): String? {
        return withContext(Dispatchers.IO) {
            val modelDir = File(context.filesDir, MODEL_DIR)
            if (modelDir.exists() && modelDir.listFiles()?.isNotEmpty() == true) {
                return@withContext modelDir.absolutePath
            }

            try {
                val assets = context.assets.list("") ?: return@withContext null
                if (MODEL_ASSET !in assets) {
                    Log.i(TAG, "Model asset $MODEL_ASSET not found — STT will use online fallback")
                    return@withContext null
                }

                modelDir.mkdirs()
                val inputStream = context.assets.open(MODEL_ASSET)
                val zipStream = ZipInputStream(inputStream)
                var entry = zipStream.nextEntry
                var totalBytes = 0L

                while (entry != null) {
                    val outFile = File(modelDir, entry.name)
                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        FileOutputStream(outFile).use { fos ->
                            val buffer = ByteArray(8192)
                            var len: Int
                            while (zipStream.read(buffer).also { len = it } > 0) {
                                fos.write(buffer, 0, len)
                                totalBytes += len
                                _modelProgress.value = (totalBytes / 50_000_000f).coerceAtMost(1f)
                            }
                        }
                    }
                    zipStream.closeEntry()
                    entry = zipStream.nextEntry
                }
                zipStream.close()
                _modelProgress.value = 1f
                modelDir.absolutePath
            } catch (e: IOException) {
                Log.e(TAG, "Failed to extract model: ${e.message}")
                null
            }
        }
    }

    private fun loadModel(modelPath: String) {
        try {
            val modelClass = Class.forName("org.vosk.Model")
            model = modelClass.getConstructor(String::class.java).newInstance(modelPath)

            val recClass = Class.forName("org.vosk.Recognizer")
            recognizer = recClass.getConstructor(modelClass, Float::class.javaPrimitiveType)
                .newInstance(model, SAMPLE_RATE)

            Log.i(TAG, "Vosk recognizer created at ${SAMPLE_RATE}Hz")
        } catch (e: ClassNotFoundException) {
            Log.w(TAG, "Vosk library not available — add com.alphacephei:vosk-android:0.3.47 to dependencies")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load Vosk model: ${e.message}")
        }
    }

    private fun startRecognition() {
        Log.i(TAG, "Recognition started — feed audio via processAudioBuffer()")
    }

    private fun stopRecognition() {
        try {
            recognizer?.let {
                val finalMethod = it.javaClass.getMethod("getFinalResult")
                val resultJson = finalMethod.invoke(it) as String
                val json = JSONObject(resultJson)
                val text = json.optString("text", "")
                if (text.isNotBlank()) {
                    scope.launch {
                        _transcriptions.emit(TranscriptionResult(text, isFinal = true))
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error getting final result: ${e.message}")
        }
        Log.i(TAG, "Recognition stopped")
    }

    fun release() {
        try {
            recognizer?.let {
                it.javaClass.getMethod("close").invoke(it)
            }
            model?.let {
                it.javaClass.getMethod("close").invoke(it)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing Vosk: ${e.message}")
        }
        recognizer = null
        model = null
        _state.value = State.UNINITIALIZED
    }
}
