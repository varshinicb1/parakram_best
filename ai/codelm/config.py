"""Single source of truth for all CodeLM constants."""

from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent
CORPUS_DIR = ROOT_DIR / "corpus"
RAW_DIR = CORPUS_DIR / "raw"
DB_PATH = CORPUS_DIR / "codelm_corpus.db"
INDEX_DIR = ROOT_DIR / "embedding" / "indices"
MODEL_DIR = ROOT_DIR / "model" / "checkpoints"

# Corpus
MIN_BLOCK_LINES = 4
MAX_BLOCK_LINES = 500
SUPPORTED_EXTENSIONS = {".c", ".h"}
COMPILATION_TIMEOUT_SECONDS = 30

# Embedding
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
TRIPLET_MARGIN = 0.3
BATCH_SIZE = 64

# Model architecture
VOCAB_SIZE = 16384
BLOCK_DIM = 512
N_HEADS = 8
N_LAYERS = 6
MAX_SEQ_LEN = 256
DROPOUT = 0.1

# Training
LEARNING_RATE = 2e-4
WEIGHT_DECAY = 0.01
WARMUP_STEPS = 500
MAX_EPOCHS = 20
LORA_RANK = 16
LORA_ALPHA = 32
GRADIENT_ACCUMULATION_STEPS = 4

# Inference
TOP_K = 50
TOP_P = 0.9
TEMPERATURE = 0.7
MAX_GENERATE_LEN = 128

# Target MCUs
TARGET_MCUS = {
    "esp32s3": {
        "arch": "xtensa",
        "flash_kb": 16384,
        "sram_kb": 512,
        "psram_kb": 8192,
        "compiler": "xtensa-esp32s3-elf-gcc",
    },
    "rp2040": {
        "arch": "arm-cortex-m0+",
        "flash_kb": 2048,
        "sram_kb": 264,
        "psram_kb": 0,
        "compiler": "arm-none-eabi-gcc",
    },
    "stm32f4": {
        "arch": "arm-cortex-m4f",
        "flash_kb": 1024,
        "sram_kb": 192,
        "psram_kb": 0,
        "compiler": "arm-none-eabi-gcc",
    },
}
