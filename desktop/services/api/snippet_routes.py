"""
Snippet API Routes — Code snippet library access.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/snippets")
async def list_snippets(category: str = "", tag: str = "", board: str = ""):
    """List code snippets with optional filters."""
    from services.code_snippets import get_snippets
    return {"snippets": get_snippets(category, tag, board)}


@router.get("/snippets/categories")
async def snippet_categories():
    from services.code_snippets import get_snippet_categories
    return {"categories": get_snippet_categories()}


@router.get("/snippets/search")
async def search_snippets(q: str = ""):
    from services.code_snippets import search_snippets
    return {"snippets": search_snippets(q)}
