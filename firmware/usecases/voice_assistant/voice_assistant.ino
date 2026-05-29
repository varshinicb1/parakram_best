// ESP32-S3 Voice Assistant v12 — Pure PCM Streaming, No VAD
// Board   : ESP32-S3  (16 MB Flash / 8 MB PSRAM)
// MIC     : INMP441   WS=4  SCK=5  SD=7
// SPK     : MAX98357A WS=15 BCK=16 DOUT=17
//
// PIPELINES (server-selected via CMD:PIPELINE:xxx):
//   local    — local STT → Ollama LLM → local TTS  [DEFAULT]
//   sarvam   — Sarvam STT → Sarvam LLM → Sarvam TTS
//   gemini   — Gemini Live streaming pipeline
//
// ALL HARDWARE CONFIG IS DRIVEN BY HTTP /api/config  (JSON)
// Device polls /api/config at boot and every 60s.
// OTA available at esp32s3-va.local or by HTTP trigger.
//
// SERIAL COMMANDS:
//   TONE      — 440 Hz test beep
//   KARAOKE   — mic → speaker loopback
//   STOPK     — stop karaoke
//   STATUS    — print heap/psram/chunk/ring/pipeline stats
//   RECONFIG  — force re-fetch of config from server
//   <text>    — forward as TEXT: to server
//
// SERVER → DEVICE COMMANDS (over WS TEXT):
//   CMD:CHUNK_SIZE:640      — set mic packet size (bytes, even, 64–3200)
//   CMD:VOLUME:80           — playback volume 0–200 (100 = normal)
//   CMD:PIPELINE:local      — switch active pipeline
//   CMD:PIPELINE:sarvam
//   CMD:PIPELINE:gemini
//   CMD:SAMPLE_RATE:16000   — audio sample rate (8000/16000/22050/44100)
//   CMD:DMA_LEN:256         — DMA buffer length (64–512, power of 2)
//   CMD:GAIN_SHIFT:14       — mic gain right-shift (10–18)
//   CMD:HPF_ALPHA:31785     — HPF alpha in Q15 (0–32767)
//   CMD:CLIP:30000          — clip limit (1000–32767)
//   CMD:KARAOKE             — mic→speaker loopback
//   CMD:STOPK               — stop karaoke
//   CMD:TONE                — 440 Hz tone
//   CMD:WSLOOP_START        — WS echo mode
//   CMD:WSLOOP_STOP         — stop echo
//   CMD:OTA_URL:<url>       — trigger OTA from URL
//   CMD:REBOOT              — reboot device
//   END                     — end of TTS stream (ring drains naturally)
// ============================================================================

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <WebSocketsClient.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>
#include <esp_heap_caps.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <math.h>
#include <string.h>

// ── WIFI CREDENTIALS ─────────────────────────────────────────────────────────
// Override these via /api/config response; these are compile-time defaults.
#define WIFI_SSID        "V"
#define WIFI_PASSWORD    "varshu99"
#define WS_HOST_DEFAULT  "10.133.85.73"
#define WS_PORT_DEFAULT  8765
#define WS_PATH          "/"
#define HTTP_PORT_DEFAULT 8081
#define CONFIG_POLL_MS   60000UL   // re-fetch config every 60s

// ── I2S PINS (fixed by PCB, not runtime-configurable) ─────────────────────────
#define I2S_MIC    I2S_NUM_0
#define MIC_WS     GPIO_NUM_4
#define MIC_SCK    GPIO_NUM_5
#define MIC_SD     GPIO_NUM_7
#define I2S_SPK    I2S_NUM_1
#define SPK_WS     GPIO_NUM_15
#define SPK_BCK    GPIO_NUM_16
#define SPK_DOUT   GPIO_NUM_17

// ── RUNTIME-CONFIGURABLE AUDIO PARAMS (defaults, overridden by /api/config) ──
static volatile uint32_t g_sample_rate   = 16000;
static volatile uint32_t g_dma_len       = 256;    // samples per DMA buf
static volatile uint32_t g_chunk_bytes   = 640;    // WS packet size (bytes)
static volatile int      g_gain_shift    = 11;     // INMP441 32→16 shift (louder)
static volatile int32_t  g_hpf_alpha     = 31785;  // Q15 α=0.97
static volatile int32_t  g_clip_limit    = 30000;
static volatile float    g_volume        = 1.0f;
static volatile int      g_dma_bufs      = 8;

// ── PIPELINE SELECTION ────────────────────────────────────────────────────────
typedef enum { PIPE_LOCAL = 0, PIPE_SARVAM = 1, PIPE_GEMINI = 2 } pipeline_t;
static volatile pipeline_t g_pipeline = PIPE_LOCAL;
static const char* pipeline_name() {
    switch(g_pipeline) { case PIPE_SARVAM: return "sarvam"; case PIPE_GEMINI: return "gemini"; default: return "local"; }
}

// ── RING BUFFER ───────────────────────────────────────────────────────────────
// 30s at 16kHz stereo = 960 KB  — fits any TTS response
#define PLAY_RING_BYTES  (48000 * 2 * 30)   // supports up to 48kHz if needed

static uint8_t*          g_ring    = NULL;
static volatile uint32_t g_ring_wr = 0;
static volatile uint32_t g_ring_rd = 0;
static volatile bool     g_playing = false;

// ── RECORDING BUFFER (PSRAM) ──────────────────────────────────────────────────
#define RECORD_MAX_S   30
#define RECORD_BYTES   (48000 * 2 * RECORD_MAX_S)
static uint8_t*          g_rec      = NULL;
static volatile uint32_t g_rec_len  = 0;
static volatile uint32_t g_rec_tgt  = 0;
static volatile bool     g_rec_done = false;

// ── STACKS ────────────────────────────────────────────────────────────────────
#define STACK_CAP     8192
#define STACK_WS      12288
#define STACK_UPLOAD  20480
#define STACK_CONFIG  8192

// ── GLOBALS ───────────────────────────────────────────────────────────────────
static portMUX_TYPE      g_mux       = portMUX_INITIALIZER_UNLOCKED;
static volatile bool     g_ws_up     = false;
static volatile bool     g_wifi_up   = false;
static volatile bool     g_karaoke   = false;
static volatile bool     g_wsloop    = false;
static volatile bool     g_i2s_running = false;
static SemaphoreHandle_t g_ws_mtx    = NULL;
static SemaphoreHandle_t g_ring_mtx  = NULL;
static SemaphoreHandle_t g_cfg_mtx   = NULL;
static WebSocketsClient  g_ws;

// Server address (may be updated by /api/config)
static char g_ws_host[64]  = WS_HOST_DEFAULT;
static int  g_ws_port      = WS_PORT_DEFAULT;
static int  g_http_port    = HTTP_PORT_DEFAULT;

// Audio frame buffers — allocated from PSRAM at runtime
static int32_t* g_raw  = NULL;
static int16_t* g_pcm  = NULL;
static uint8_t* g_pkt  = NULL;   // WS accumulation buffer

// HPF state
static int32_t g_hpf_in = 0, g_hpf_out = 0;

// ── RING BUFFER HELPERS ───────────────────────────────────────────────────────
static uint32_t ring_used() {
    uint32_t w = g_ring_wr, r = g_ring_rd;
    return (w >= r) ? (w - r) : (PLAY_RING_BYTES - r + w);
}

static void ring_push(const uint8_t* d, uint32_t n) {
    if (!n) return;
    uint32_t fr = PLAY_RING_BYTES - ring_used() - 1;
    if (n > fr) {
        // overrun: advance read pointer to make room (oldest audio dropped)
        g_ring_rd = (g_ring_rd + (n - fr)) % PLAY_RING_BYTES;
    }
    uint32_t e = PLAY_RING_BYTES - g_ring_wr;
    if (n <= e) {
        memcpy(g_ring + g_ring_wr, d, n);
    } else {
        memcpy(g_ring + g_ring_wr, d, e);
        memcpy(g_ring, d + e, n - e);
    }
    g_ring_wr = (g_ring_wr + n) % PLAY_RING_BYTES;
}

static uint32_t ring_pop(uint8_t* dst, uint32_t max) {
    uint32_t av = ring_used();
    if (!av) return 0;
    uint32_t n = (av < max) ? av : max;
    uint32_t e = PLAY_RING_BYTES - g_ring_rd;
    if (n <= e) {
        memcpy(dst, g_ring + g_ring_rd, n);
    } else {
        memcpy(dst, g_ring + g_ring_rd, e);
        memcpy(dst + e, g_ring, n - e);
    }
    g_ring_rd = (g_ring_rd + n) % PLAY_RING_BYTES;
    return n;
}

static void ring_clear() {
    if (xSemaphoreTake(g_ring_mtx, pdMS_TO_TICKS(10)) == pdTRUE) {
        g_ring_wr = 0; g_ring_rd = 0;
        xSemaphoreGive(g_ring_mtx);
    }
}

// ── WS SEND HELPERS ───────────────────────────────────────────────────────────
static void ws_bin(const uint8_t* d, size_t n) {
    if (!g_ws_up || !n) return;
    if (xSemaphoreTake(g_ws_mtx, pdMS_TO_TICKS(5)) == pdTRUE) {
        g_ws.sendBIN(d, n);
        xSemaphoreGive(g_ws_mtx);
    }
}

static void ws_txt(const char* s) {
    if (!g_ws_up || !s) return;
    if (xSemaphoreTake(g_ws_mtx, pdMS_TO_TICKS(5)) == pdTRUE) {
        g_ws.sendTXT(s);
        xSemaphoreGive(g_ws_mtx);
    }
}

// ── AUDIO PROCESSING ─────────────────────────────────────────────────────────
static int16_t process_mic(int32_t raw) {
    int32_t v = raw >> g_gain_shift;
    int32_t cl = g_clip_limit;
    if (v >  cl) v =  cl;
    if (v < -cl) v = -cl;
    // DC-blocking HPF: y[n] = α*(y[n-1] + x[n] - x[n-1])
    int32_t s = (int16_t)v;
    int32_t d = s - g_hpf_in;
    int32_t ha = g_hpf_alpha;
    int32_t o = (g_hpf_out * ha + d * ha) >> 15;
    if (o >  32767) o =  32767;
    if (o < -32768) o = -32768;
    g_hpf_in = s; g_hpf_out = o;
    return (int16_t)o;
}

static void apply_volume(uint8_t* buf, uint32_t n) {
    float v = g_volume;
    if (v == 1.0f) return;
    int16_t* s16 = (int16_t*)buf;
    for (uint32_t i = 0; i < n / 2; i++) {
        int32_t s = (int32_t)(s16[i] * v);
        if (s >  32767) s =  32767;
        if (s < -32768) s = -32768;
        s16[i] = (int16_t)s;
    }
}

static void play_tone(float hz = 440.0f, float secs = 1.0f, float amp = 0.6f) {
    if (!g_i2s_running) return;
    int N = (int)(g_sample_rate * secs);
    int16_t* buf = (int16_t*)heap_caps_malloc(N * 2, MALLOC_CAP_SPIRAM);
    if (!buf) buf = (int16_t*)malloc(N * 2);
    if (!buf) return;
    int fade = g_sample_rate / 100;
    for (int i = 0; i < N; i++) {
        float a = amp;
        if (i < fade)     a *= (float)i / fade;
        if (i > N - fade) a *= (float)(N - i) / fade;
        buf[i] = (int16_t)(sinf(2.0f * 3.14159265f * hz * (float)i / g_sample_rate) * a * 32767.0f);
    }
    size_t w = 0;
    i2s_write(I2S_SPK, buf, N * 2, &w, pdMS_TO_TICKS(5000));
    heap_caps_free(buf);
}

// ── I2S INIT / DEINIT ─────────────────────────────────────────────────────────
static void deinit_i2s() {
    if (g_i2s_running) {
        i2s_driver_uninstall(I2S_MIC);
        i2s_driver_uninstall(I2S_SPK);
        g_i2s_running = false;
    }
}

static void init_mic() {
    uint32_t sr = g_sample_rate;
    uint32_t dl = g_dma_len;
    i2s_config_t c = {
        .mode               = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate        = sr,
        .bits_per_sample    = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format     = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags   = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count      = g_dma_bufs,
        .dma_buf_len        = (int)dl,
        .use_apll           = true,
        .tx_desc_auto_clear = false,
        .fixed_mclk         = 0
    };
    i2s_pin_config_t p = {
        .mck_io_num   = I2S_PIN_NO_CHANGE,
        .bck_io_num   = MIC_SCK,
        .ws_io_num    = MIC_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = MIC_SD
    };
    ESP_ERROR_CHECK(i2s_driver_install(I2S_MIC, &c, 0, NULL));
    ESP_ERROR_CHECK(i2s_set_pin(I2S_MIC, &p));
    ESP_ERROR_CHECK(i2s_zero_dma_buffer(I2S_MIC));
    Serial.printf("MIC OK  sr=%u  dma_len=%u\n", sr, dl);
}

static void init_spk() {
    uint32_t sr = g_sample_rate;
    uint32_t dl = g_dma_len;
    i2s_config_t c = {
        .mode               = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate        = sr,
        .bits_per_sample    = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format     = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags   = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count      = g_dma_bufs,
        .dma_buf_len        = (int)dl,
        .use_apll           = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk         = 0
    };
    i2s_pin_config_t p = {
        .mck_io_num   = I2S_PIN_NO_CHANGE,
        .bck_io_num   = SPK_BCK,
        .ws_io_num    = SPK_WS,
        .data_out_num = SPK_DOUT,
        .data_in_num  = I2S_PIN_NO_CHANGE
    };
    ESP_ERROR_CHECK(i2s_driver_install(I2S_SPK, &c, 0, NULL));
    ESP_ERROR_CHECK(i2s_set_pin(I2S_SPK, &p));
    ESP_ERROR_CHECK(i2s_zero_dma_buffer(I2S_SPK));
    Serial.printf("SPK OK  sr=%u  dma_len=%u\n", sr, dl);
}

static void reinit_i2s() {
    // Called after sample_rate / dma_len changes from config
    // Must NOT be called from capture task — call from ws/config task
    deinit_i2s();

    // Reallocate frame buffers for new DMA size
    if (g_raw) { heap_caps_free(g_raw); g_raw = NULL; }
    if (g_pcm) { heap_caps_free(g_pcm); g_pcm = NULL; }
    if (g_pkt) { heap_caps_free(g_pkt); g_pkt = NULL; }

    uint32_t dl = g_dma_len;
    g_raw = (int32_t*)heap_caps_malloc(dl * 4, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    g_pcm = (int16_t*)heap_caps_malloc(dl * 2, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    g_pkt = (uint8_t*)heap_caps_malloc(3200,   MALLOC_CAP_SPIRAM);
    if (!g_raw || !g_pcm || !g_pkt) {
        Serial.println("FATAL: frame buffer alloc");
        for (;;) delay(1000);
    }

    init_mic();
    init_spk();
    g_i2s_running = true;
}

// ── CONFIG FETCH ──────────────────────────────────────────────────────────────
// Server exposes GET /api/config → JSON like:
// {
//   "pipeline":   "local",
//   "chunk_size": 640,
//   "volume":     100,
//   "sample_rate":16000,
//   "dma_len":    256,
//   "dma_bufs":   8,
//   "gain_shift": 14,
//   "hpf_alpha":  31785,
//   "clip_limit": 30000,
//   "ws_host":    "10.133.85.73",
//   "ws_port":    8765,
//   "http_port":  8081
// }
static volatile bool g_need_reinit = false;

static void fetch_config() {
    if (!g_wifi_up) return;
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d/api/config", g_ws_host, g_http_port);
    HTTPClient http;
    http.begin(url);
    http.setTimeout(5000);
    int code = http.GET();
    if (code == 200) {
        String body = http.getString();
        StaticJsonDocument<512> doc;
        DeserializationError err = deserializeJson(doc, body);
        if (!err) {
            bool reinit = false;
            if (doc.containsKey("pipeline")) {
                const char* p = doc["pipeline"];
                pipeline_t np = PIPE_LOCAL;
                if (strcmp(p, "sarvam") == 0) np = PIPE_SARVAM;
                else if (strcmp(p, "gemini") == 0) np = PIPE_GEMINI;
                if (np != g_pipeline) { g_pipeline = np; Serial.printf("CFG pipeline: %s\n", p); }
            }
            if (doc.containsKey("chunk_size")) {
                uint32_t v = doc["chunk_size"];
                if (v >= 64 && v <= 3200 && (v % 2 == 0)) g_chunk_bytes = v;
            }
            if (doc.containsKey("volume")) {
                int v = doc["volume"]; if (v < 0) v = 0; if (v > 200) v = 200;
                g_volume = (float)v / 100.0f;
            }
            if (doc.containsKey("gain_shift")) {
                int v = doc["gain_shift"]; if (v >= 10 && v <= 18) g_gain_shift = v;
            }
            if (doc.containsKey("hpf_alpha")) {
                int32_t v = doc["hpf_alpha"]; if (v >= 0 && v <= 32767) g_hpf_alpha = v;
            }
            if (doc.containsKey("clip_limit")) {
                int32_t v = doc["clip_limit"]; if (v >= 1000 && v <= 32767) g_clip_limit = v;
            }
            if (doc.containsKey("ws_host")) {
                const char* h = doc["ws_host"];
                if (h && strcmp(h, g_ws_host) != 0) { strncpy(g_ws_host, h, 63); }
            }
            if (doc.containsKey("ws_port"))   g_ws_port   = doc["ws_port"];
            if (doc.containsKey("http_port"))  g_http_port = doc["http_port"];
            if (doc.containsKey("dma_bufs"))   g_dma_bufs  = doc["dma_bufs"];
            if (doc.containsKey("sample_rate")) {
                uint32_t v = doc["sample_rate"];
                if (v != g_sample_rate) { g_sample_rate = v; reinit = true; }
            }
            if (doc.containsKey("dma_len")) {
                uint32_t v = doc["dma_len"];
                if (v >= 64 && v <= 512 && v != g_dma_len) { g_dma_len = v; reinit = true; }
            }
            if (reinit) g_need_reinit = true;
            Serial.printf("CFG OK  pipeline=%s chunk=%u vol=%.0f%%\n",
                pipeline_name(), (uint32_t)g_chunk_bytes, g_volume * 100.0f);
        } else {
            Serial.printf("CFG JSON err: %s\n", err.c_str());
        }
    } else {
        Serial.printf("CFG HTTP %d\n", code);
    }
    http.end();
}

// ── WS EVENT HANDLER ─────────────────────────────────────────────────────────
static void ws_event(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
    case WStype_CONNECTED:
        g_ws_up = true;
        Serial.printf("WS connected → %s:%d  pipeline=%s\n", g_ws_host, g_ws_port, pipeline_name());
        // Announce ourselves to server
        {
            char hello[128];
            snprintf(hello, sizeof(hello),
                "HELLO:device=esp32s3-va;pipeline=%s;sr=%u;chunk=%u",
                pipeline_name(), (uint32_t)g_sample_rate, (uint32_t)g_chunk_bytes);
            ws_txt(hello);
        }
        break;

    case WStype_DISCONNECTED:
        g_ws_up = false;
        ring_clear();
        g_playing = false;
        Serial.println("WS disconnected");
        break;

    case WStype_BIN:
        if (length > 0 && payload) {
            if (g_wsloop) { ws_bin(payload, length); break; }
            g_playing = true;  // set BEFORE push so capture task sees it immediately
            if (xSemaphoreTake(g_ring_mtx, pdMS_TO_TICKS(5)) == pdTRUE) {
                ring_push(payload, (uint32_t)length);
                xSemaphoreGive(g_ring_mtx);
            }
        }
        break;

    case WStype_TEXT:
        if (!payload || !length) break;
        {
            const char* s = (const char*)payload;
            if (strcmp(s, "END") == 0) {
                // TTS stream finished — ring drains naturally, no action needed
            }
            else if (strncmp(s, "CMD:CHUNK_SIZE:", 15) == 0) {
                uint32_t n = (uint32_t)atoi(s + 15);
                if (n >= 64 && n <= 3200 && (n % 2 == 0)) {
                    g_chunk_bytes = n;
                    Serial.printf("CMD chunk=%u  (%.0fms @ %uHz)\n",
                        n, (float)n / (float)(g_sample_rate / 500), (uint32_t)g_sample_rate);
                }
            }
            else if (strncmp(s, "CMD:VOLUME:", 11) == 0) {
                int v = atoi(s + 11); if (v < 0) v = 0; if (v > 200) v = 200;
                g_volume = (float)v / 100.0f;
                Serial.printf("CMD volume=%d%%\n", v);
            }
            else if (strncmp(s, "CMD:PIPELINE:", 13) == 0) {
                const char* p = s + 13;
                if      (strcmp(p, "sarvam") == 0) g_pipeline = PIPE_SARVAM;
                else if (strcmp(p, "gemini") == 0) g_pipeline = PIPE_GEMINI;
                else                               g_pipeline = PIPE_LOCAL;
                Serial.printf("CMD pipeline=%s\n", pipeline_name());
            }
            else if (strncmp(s, "CMD:SAMPLE_RATE:", 16) == 0) {
                uint32_t v = (uint32_t)atoi(s + 16);
                if (v == 8000 || v == 16000 || v == 22050 || v == 44100) {
                    g_sample_rate = v; g_need_reinit = true;
                    Serial.printf("CMD sample_rate=%u (reinit pending)\n", v);
                }
            }
            else if (strncmp(s, "CMD:DMA_LEN:", 12) == 0) {
                uint32_t v = (uint32_t)atoi(s + 12);
                if (v >= 64 && v <= 512) {
                    g_dma_len = v; g_need_reinit = true;
                    Serial.printf("CMD dma_len=%u (reinit pending)\n", v);
                }
            }
            else if (strncmp(s, "CMD:GAIN_SHIFT:", 15) == 0) {
                int v = atoi(s + 15); if (v >= 10 && v <= 18) {
                    g_gain_shift = v; Serial.printf("CMD gain_shift=%d\n", v);
                }
            }
            else if (strncmp(s, "CMD:HPF_ALPHA:", 14) == 0) {
                int32_t v = atoi(s + 14); if (v >= 0 && v <= 32767) {
                    g_hpf_alpha = v; Serial.printf("CMD hpf_alpha=%d\n", v);
                }
            }
            else if (strncmp(s, "CMD:CLIP:", 9) == 0) {
                int32_t v = atoi(s + 9); if (v >= 1000 && v <= 32767) {
                    g_clip_limit = v; Serial.printf("CMD clip=%d\n", v);
                }
            }
            else if (strcmp(s, "CMD:KARAOKE")   == 0) { g_karaoke = true;  Serial.println("KARAOKE ON"); }
            else if (strcmp(s, "CMD:STOPK")     == 0) { g_karaoke = false; Serial.println("KARAOKE OFF"); }
            else if (strcmp(s, "CMD:TONE")      == 0) { play_tone(); }
            else if (strcmp(s, "CMD:WSLOOP_START") == 0) { g_wsloop = true; }
            else if (strcmp(s, "CMD:WSLOOP_STOP")  == 0) { g_wsloop = false; }
            else if (strcmp(s, "CMD:REBOOT")    == 0) { Serial.println("CMD REBOOT"); delay(500); ESP.restart(); }
            else if (strncmp(s, "CMD:OTA_URL:", 12) == 0) {
                // Trigger OTA from URL — runs in WS task context (non-blocking trigger)
                Serial.printf("OTA URL: %s\n", s + 12);
                // ArduinoOTA handles file-based OTA; for URL-based use Update.begin()
                // Simplified: just signal back — production code would spawn a task
                ws_txt("OTA:NOT_IMPL");
            }
            else { Serial.printf("WS: %s\n", s); }
        }
        break;
    default: break;
    }
}

// ── WAV HEADER ────────────────────────────────────────────────────────────────
static void wav_hdr(uint8_t* b, uint32_t dlen, uint32_t sr) {
    uint32_t fsz = dlen + 36;
    uint32_t br  = sr * 2;
    uint16_t blk = 2, bits = 16, ch = 1, fmt = 1, s1 = 16;
    memcpy(b,      "RIFF", 4); memcpy(b + 4,  &fsz,  4);
    memcpy(b + 8,  "WAVE", 4); memcpy(b + 12, "fmt ", 4);
    memcpy(b + 16, &s1,   4); memcpy(b + 20, &fmt,  2);
    memcpy(b + 22, &ch,   2); memcpy(b + 24, &sr,   4);
    memcpy(b + 28, &br,   4); memcpy(b + 30, &blk,  2);
    memcpy(b + 32, &bits, 2); memcpy(b + 34, "data", 4);
    memcpy(b + 38, &dlen, 4);
}

// ── UPLOAD TASK ───────────────────────────────────────────────────────────────
typedef struct { uint8_t* data; uint32_t len; uint32_t sr; } UpArg;

static void upload_task(void* arg) {
    UpArg* a = (UpArg*)arg;
    uint32_t wsz = 44 + a->len;
    uint8_t* wav = (uint8_t*)heap_caps_malloc(wsz, MALLOC_CAP_SPIRAM);
    if (!wav) wav = (uint8_t*)malloc(wsz);
    if (wav) {
        wav_hdr(wav, a->len, a->sr);
        memcpy(wav + 44, a->data, a->len);
        char url[128];
        snprintf(url, sizeof(url), "http://%s:%d/api/upload-recording", g_ws_host, g_http_port);
        HTTPClient http;
        http.begin(url);
        http.addHeader("Content-Type", "audio/wav");
        http.addHeader("X-Pipeline", pipeline_name());
        http.setTimeout(20000);
        int code = http.POST(wav, wsz);
        http.end();
        Serial.printf("UPLOAD: HTTP %d (%u bytes)\n", code, wsz);
        ws_txt(code == 200 ? "RECORD_DONE" : "RECORD_FAIL");
        heap_caps_free(wav);
    } else {
        ws_txt("RECORD_FAIL");
    }
    heap_caps_free(a->data);
    free(a);
    vTaskDelete(NULL);
}

// ── TASK: AUDIO CAPTURE + PLAYBACK (core 1) ──────────────────────────────────
static uint8_t play_buf[1024];  // 32ms @ 16kHz — smooth playback, no underrun
static uint32_t pkt_len = 0;

static void task_capture(void*) {
    while (true) {
        if (!g_i2s_running || g_need_reinit) {
            taskYIELD(); continue;  // wait for reinit to complete
        }

        // ── PLAYBACK ──────────────────────────────────────────────────────────
        // Use a drain counter: only stop after 8 consecutive empty reads (~40ms)
        // This prevents g_playing flapping false between 512-byte WS packets.
        static uint8_t s_drain_count = 0;
        if (g_playing) {
            uint32_t n = 0;
            if (xSemaphoreTake(g_ring_mtx, pdMS_TO_TICKS(1)) == pdTRUE) {
                n = ring_pop(play_buf, sizeof(play_buf));
                xSemaphoreGive(g_ring_mtx);
            }
            if (n > 0) {
                s_drain_count = 0;
                apply_volume(play_buf, n);
                size_t w = 0;
                i2s_write(I2S_SPK, play_buf, n, &w, pdMS_TO_TICKS(10));
            } else {
                s_drain_count++;
                if (s_drain_count >= 8) {   // ~40ms grace period
                    s_drain_count = 0;
                    g_playing = false;      // ring truly drained
                }
            }
        } else {
            s_drain_count = 0;
        }

        // ── MIC READ ──────────────────────────────────────────────────────────
        uint32_t dl = g_dma_len;
        size_t br = 0;
        if (i2s_read(I2S_MIC, g_raw, dl * 4, &br, pdMS_TO_TICKS(8)) != ESP_OK || !br) {
            taskYIELD(); continue;
        }
        uint32_t n = br / 4;
        for (uint32_t i = 0; i < n; i++) g_pcm[i] = process_mic(g_raw[i]);

        // ── KARAOKE ───────────────────────────────────────────────────────────
        if (g_karaoke) {
            size_t w = 0;
            i2s_write(I2S_SPK, g_pcm, n * 2, &w, pdMS_TO_TICKS(2));
            taskYIELD(); continue;
        }

        // ── STREAMING TO SERVER ───────────────────────────────────────────────
        if (g_ws_up) {
            uint32_t chunk = g_chunk_bytes;
            uint32_t bytes = n * 2;
            if (pkt_len + bytes > 3200) pkt_len = 0; // guard overflow
            memcpy(g_pkt + pkt_len, (uint8_t*)g_pcm, bytes);
            pkt_len += bytes;
            if (pkt_len >= chunk) {
                ws_bin(g_pkt, pkt_len);
                pkt_len = 0;
            }
        } else {
            pkt_len = 0;
        }

        // ── RECORDING ─────────────────────────────────────────────────────────
        if (g_rec_tgt > 0 && g_rec_len < g_rec_tgt && g_rec) {
            uint32_t rem = g_rec_tgt - g_rec_len;
            uint32_t cp  = (n * 2 < rem) ? n * 2 : rem;
            memcpy(g_rec + g_rec_len, g_pcm, cp);
            g_rec_len += cp;
            if (g_rec_len >= g_rec_tgt) { g_rec_tgt = 0; g_rec_done = true; }
        }

        taskYIELD();
    }
}

// ── TASK: CONFIG POLLER (core 0) ──────────────────────────────────────────────
static void task_config(void*) {
    static uint32_t last_cfg = 0;
    while (true) {
        uint32_t now = millis();
        if (now - last_cfg > CONFIG_POLL_MS || last_cfg == 0) {
            last_cfg = now;
            if (g_wifi_up) fetch_config();
        }
        if (g_need_reinit) {
            g_need_reinit = false;
            Serial.println("CFG reinit I2S...");
            reinit_i2s();
            Serial.println("CFG reinit done");
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

// ── TASK: WS + SERIAL + OTA (core 0) ─────────────────────────────────────────
static void task_ws(void*) {
    static String sbuf;
    static uint32_t wifi_ms = 0;

    while (true) {
        uint32_t now = millis();

        // WiFi watchdog
        if (now - wifi_ms > 3000) {
            wifi_ms = now;
            if (WiFi.status() != WL_CONNECTED) {
                WiFi.disconnect();
                WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
            }
            g_wifi_up = (WiFi.status() == WL_CONNECTED);
        }

        ArduinoOTA.handle();
        if (g_wifi_up) g_ws.loop();

        // Handle completed recording
        if (g_rec_done) {
            g_rec_done = false;
            UpArg* a = (UpArg*)malloc(sizeof(UpArg));
            uint8_t* copy = (uint8_t*)heap_caps_malloc(g_rec_len, MALLOC_CAP_SPIRAM);
            if (!copy) copy = (uint8_t*)malloc(g_rec_len);
            if (a && copy) {
                memcpy(copy, g_rec, g_rec_len);
                a->data = copy; a->len = g_rec_len; a->sr = g_sample_rate;
                xTaskCreatePinnedToCore(upload_task, "up", STACK_UPLOAD, a, 3, NULL, 0);
            } else {
                ws_txt("RECORD_FAIL");
                if (copy) heap_caps_free(copy);
                if (a) free(a);
            }
            g_rec_len = 0;
        }

        // Serial commands
        while (Serial.available()) {
            char c = (char)Serial.read();
            if (c == '\n' || c == '\r') {
                sbuf.trim();
                if (!sbuf.length()) { sbuf = ""; continue; }
                String u = sbuf; u.toUpperCase();
                if (u == "TONE") {
                    play_tone();
                } else if (u == "KARAOKE") {
                    g_karaoke = !g_karaoke;
                    Serial.printf("KARAOKE: %s\n", g_karaoke ? "ON" : "OFF");
                } else if (u == "STOPK") {
                    g_karaoke = false;
                } else if (u == "RECONFIG") {
                    fetch_config();
                } else if (u == "STATUS") {
                    Serial.printf("pipeline=%s  chunk=%u  vol=%.1f  playing=%d  ws=%s\n",
                        pipeline_name(), (uint32_t)g_chunk_bytes, (double)g_volume,
                        g_playing, g_ws_up ? "up" : "down");
                    Serial.printf("sr=%u  dma_len=%u  gain=%d  hpf=%d  clip=%d\n",
                        (uint32_t)g_sample_rate, (uint32_t)g_dma_len,
                        g_gain_shift, (int)g_hpf_alpha, (int)g_clip_limit);
                    Serial.printf("heap=%u  psram=%u  ring_used=%u\n",
                        ESP.getFreeHeap(), ESP.getFreePsram(), ring_used());
                } else if (g_ws_up) {
                    String m = "TEXT:" + sbuf;
                    ws_txt(m.c_str());
                } else {
                    Serial.println("WS not connected");
                }
                sbuf = "";
            } else if (sbuf.length() < 255) {
                sbuf += c;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

// ── SETUP ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200); delay(400);
    Serial.println("\n╔══════════════════════════════════╗");
    Serial.println("║  ESP32-S3 Voice Assistant  v18   ║");
    Serial.println("║  Multi-Pipeline, Full API Config ║");
    Serial.println("╚══════════════════════════════════╝");
    Serial.printf("Heap: %u  PSRAM: %u\n", ESP.getFreeHeap(), ESP.getFreePsram());

    // Allocate ring buffer from PSRAM
    g_ring = (uint8_t*)heap_caps_malloc(PLAY_RING_BYTES, MALLOC_CAP_SPIRAM);
    if (!g_ring) g_ring = (uint8_t*)malloc(PLAY_RING_BYTES);
    if (!g_ring) { Serial.println("FATAL: ring alloc"); for (;;) delay(1000); }
    memset(g_ring, 0, PLAY_RING_BYTES);

    // Allocate recording buffer from PSRAM
    g_rec = (uint8_t*)heap_caps_malloc(RECORD_BYTES, MALLOC_CAP_SPIRAM);
    if (!g_rec) g_rec = (uint8_t*)malloc(RECORD_BYTES);

    g_ws_mtx   = xSemaphoreCreateMutex();
    g_ring_mtx = xSemaphoreCreateMutex();
    g_cfg_mtx  = xSemaphoreCreateMutex();
    if (!g_ws_mtx || !g_ring_mtx || !g_cfg_mtx) {
        Serial.println("FATAL: mutex"); for (;;) delay(1000);
    }

    // Init I2S (uses default g_sample_rate / g_dma_len)
    reinit_i2s();

    // Boot tones
    play_tone(440.0f, 0.3f, 0.5f); delay(100);
    play_tone(880.0f, 0.2f, 0.4f);
    Serial.println("Boot beeps done");

    // WiFi
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("WiFi");
    for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; i++) {
        delay(500); Serial.print(".");
    }
    g_wifi_up = (WiFi.status() == WL_CONNECTED);
    Serial.printf("\nWiFi: %s\n", g_wifi_up ? WiFi.localIP().toString().c_str() : "failed");

    // Fetch config from server before connecting WS
    if (g_wifi_up) fetch_config();

    // OTA
    ArduinoOTA.setHostname("esp32s3-va-v16");
    ArduinoOTA.onStart([]()  { Serial.println("OTA start"); });
    ArduinoOTA.onEnd([]()    { Serial.println("\nOTA done"); });
    ArduinoOTA.onError([](ota_error_t e) { Serial.printf("OTA err[%u]\n", e); });
    ArduinoOTA.begin();

    // WebSocket
    g_ws.begin(g_ws_host, g_ws_port, WS_PATH);
    g_ws.onEvent(ws_event);
    g_ws.setReconnectInterval(3000);
    g_ws.enableHeartbeat(25000, 8000, 3);  // longer timeout during audio playback

    xTaskCreatePinnedToCore(task_capture, "cap",  STACK_CAP,    NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(task_ws,      "ws",   STACK_WS,     NULL, 4, NULL, 0);
    xTaskCreatePinnedToCore(task_config,  "cfg",  STACK_CONFIG, NULL, 2, NULL, 0);

    Serial.printf("Server:  ws://%s:%d\n", g_ws_host, g_ws_port);
    Serial.printf("Config:  http://%s:%d/api/config  (poll %lus)\n",
        g_ws_host, g_http_port, CONFIG_POLL_MS / 1000UL);
    Serial.printf("Pipeline: %s  chunk=%u  sr=%u\n",
        pipeline_name(), (uint32_t)g_chunk_bytes, (uint32_t)g_sample_rate);
    Serial.println("Serial: TONE  KARAOKE  STOPK  STATUS  RECONFIG  <text>");
    Serial.println("Mic streaming started — speak freely");
}

void loop() { vTaskDelay(pdMS_TO_TICKS(100)); }
