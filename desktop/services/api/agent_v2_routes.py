"""
Autonomous Agent API Routes — Execute the full firmware pipeline.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from agents.autonomous_agent import AutonomousAgent, parse_intent
from agents.chip_knowledge_base import get_all_supported_chips

router = APIRouter()
agent = AutonomousAgent()


class GenerateRequest(BaseModel):
    prompt: str
    board: Optional[str] = None
    session_id: Optional[str] = None


class IntentRequest(BaseModel):
    prompt: str


@router.post("/generate")
async def generate_firmware(req: GenerateRequest):
    """Execute the full autonomous pipeline: prompt → compilable firmware."""
    session = await agent.execute(
        prompt=req.prompt,
        session_id=req.session_id,
    )
    return {
        "session_id": session.session_id,
        "status": session.status,
        "board": session.board,
        "files": session.files,
        "compile_success": session.compile_success,
        "compile_output": session.compile_output[-2000:] if session.compile_output else "",
        "attempts": session.attempt,
        "steps": [s.__dict__ for s in session.steps],
        "errors": session.errors,
    }


@router.post("/parse-intent")
async def parse_user_intent(req: IntentRequest):
    """Parse a prompt without generating code — preview what the agent detects."""
    return parse_intent(req.prompt)


@router.get("/supported-chips")
async def supported_chips():
    """List all supported MCU families."""
    return {"chips": get_all_supported_chips()}
