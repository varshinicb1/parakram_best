"""
Parakram AI — FastAPI Backend
AI-assisted embedded systems development platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.project_routes import router as project_router
from api.canvas_routes import router as canvas_router
from api.build_routes import router as build_router
from api.flash_routes import router as flash_router
from api.pipeline_routes import router as pipeline_router
from api.suggestion_routes import router as suggestion_router
from api.template_routes import router as template_router
from api.simulation_routes import router as simulation_router
from api.serial_monitor import router as serial_router
from api.wokwi_routes import router as wokwi_router
from api.agent_routes import router as agent_router
from api.llm_routes import router as llm_router
from api.voice_routes import router as voice_router
from api.auth_routes import router as auth_router
from api.admin_routes import router as admin_router
from api.git_routes import router as git_router
from api.installer_routes import router as installer_router
from api.extension_routes import router as extension_router
from api.agent_v2_routes import router as agent_v2_router
from api.analysis_routes import router as analysis_router
from api.workspace_routes import router as workspace_router
from api.ota_power_routes import router as ota_power_router
from api.subscription_routes import router as subscription_router
from api.gallery_routes import router as gallery_router
from api.board_export_routes import router as board_export_router
from api.realtime_routes import router as realtime_router
from api.marketplace_routes import router as marketplace_router
from api.snippet_routes import router as snippet_router
from api.signup_routes import router as signup_router
from api.docs_routes import router as docs_router

load_dotenv()

app = FastAPI(
    title="Parakram AI",
    description="AI-assisted embedded systems development platform",
    version="2.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:1420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(project_router, prefix="/api/projects", tags=["Projects"])
app.include_router(canvas_router, prefix="/api/canvas", tags=["Canvas"])
app.include_router(build_router, prefix="/api/build", tags=["Build"])
app.include_router(flash_router, prefix="/api/flash", tags=["Flash"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(suggestion_router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(template_router, prefix="/api/templates", tags=["Templates"])
app.include_router(simulation_router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(serial_router, prefix="/api/serial", tags=["Serial Monitor"])
app.include_router(wokwi_router, prefix="/api/wokwi", tags=["Wokwi Simulator"])
app.include_router(agent_router, prefix="/api/agent", tags=["Agent Intelligence"])
app.include_router(llm_router, prefix="/api/llm", tags=["LLM Providers"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice Input"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin Console"])
app.include_router(git_router, prefix="/api/git", tags=["Git Version Control"])
app.include_router(installer_router, prefix="/api/installer", tags=["Installer"])
app.include_router(extension_router, prefix="/api/extensions", tags=["Extensions"])
app.include_router(agent_v2_router, prefix="/api/agent/v2", tags=["Autonomous Agent"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["Analysis Tools"])
app.include_router(workspace_router, prefix="/api/workspace", tags=["Workspace"])
app.include_router(ota_power_router, prefix="/api/tools", tags=["OTA & Power"])
app.include_router(subscription_router, prefix="/api/billing", tags=["Billing & Plans"])
app.include_router(gallery_router, prefix="/api/gallery", tags=["Gallery & Crash"])
app.include_router(board_export_router, prefix="/api/hardware", tags=["Board DB & Export"])
app.include_router(realtime_router, prefix="/api/rt", tags=["Realtime & Memory"])
app.include_router(marketplace_router, prefix="/api/store", tags=["Marketplace & Wiring"])
app.include_router(snippet_router, prefix="/api/code", tags=["Code Snippets"])
app.include_router(signup_router, prefix="/api/users", tags=["Signup & Downloads"])
app.include_router(docs_router, prefix="", tags=["Documentation"])


@app.get("/")
async def root():
    return {
        "name": "Parakram AI",
        "version": "2.0.0",
        "status": "running",
        "engines": [
            "Multi-Provider LLM (OpenRouter Free / Ollama / Custom)",
            "RAG (nomic-embed-text)",
            "Self-Healing Compiler",
            "Code Review Agent",
            "Serial Debugger",
            "Schematic Parser",
            "Voice Input (Sarvam AI)",
            "Web Browser Tool",
        ],
        "boards": ["esp32dev", "esp32-s3", "esp32-c3", "stm32f4", "rp2040", "mega2560"],
        "v2_features": [
            "Multi-provider LLM routing (9 free models)",
            "User-managed API keys & custom providers",
            "Voice input via Sarvam AI",
            "Hardware simulator (Wokwi)",
            "Feature verification lab",
            "Git version control & auto-releases",
            "JWT Authentication & Admin console",
            "Toolchain & library auto-installer",
            "3D WebGL UI (Three.js)",
        ],
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
