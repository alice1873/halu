import os
import asyncio
import yaml
import random
import hmac
import hashlib
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

from fastapi import FastAPI, APIRouter, HTTPException, Request
from pydantic import BaseModel
from watchfiles import awatch

# -------------------------------------------------
# FastAPI 初始化
# -------------------------------------------------
app = FastAPI(title="GPT_RP")
router = APIRouter(prefix="/api")

# -------------------------------------------------
# 路徑與全域常數
# -------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
CHAR_DIR: Path = BASE_DIR / "characters"
SNIPPET_PATH: Path = BASE_DIR / "snippets.yaml"
DEFAULT_CHAR: str = "lazul"          # 沒帶 characters 時用這隻

# -------------------------------------------------
# 共用小工具
# -------------------------------------------------

def _load_yaml(path: Path):
    """讀任何 YAML，若不存在回空 dict/list."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_character_yaml(char_name: str) -> Dict:
    """讀取單一角色卡並做安全檢查"""
    lc_name = char_name.lower()
    if not lc_name.isidentifier():
        raise HTTPException(status_code=400, detail="非法角色 ID")
    path = CHAR_DIR / f"{lc_name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"角色 {char_name} 不存在")
    return _load_yaml(path)


def pick_reply(char_data: dict, user_msg: str) -> str:
    """從 speech_patterns 隨機挑一句，支援 {{name}} 與 {{user_msg}} 佔位符"""
    patterns = char_data.get("speech_patterns") or []
    if not patterns:
        return "..."
    tpl = random.choice(patterns)
    name = char_data.get("name", "")
    return tpl.format(name=name, user_msg=user_msg)

# -------------------------------------------------
# Snippets 熱重載 (watchfiles)
# -------------------------------------------------

snippets_cache: Dict[str, str] = {}


def _load_snippets() -> Dict[str, str]:
    data = _load_yaml(SNIPPET_PATH)
    if not isinstance(data, list):
        raise RuntimeError("snippets.yaml 必須是 list")
    return {d["id"]: d["text"] for d in data if "id" in d and "text" in d}


@app.on_event("startup")
async def startup():
    """啟動時先讀 snippets，再開 watchdog 監聽"""
    global snippets_cache
    snippets_cache = _load_snippets()

    async def _watch():
        async for _ in awatch(SNIPPET_PATH):
            try:
                snippets_cache.update(_load_snippets())
                print("[snippets] hot‑reloaded ✅")
            except Exception as e:
                print("[snippets] reload failed:", e)

    asyncio.create_task(_watch())

# -------------------------------------------------
# Pydantic Models
# -------------------------------------------------

class ReplyAtom(BaseModel):
    name: str
    reply: str


class RespondIn(BaseModel):
    user_msg: str
    char_name: Optional[str] = None


class SnippetCallIn(BaseModel):
    snippet_id: str


class SnippetOut(BaseModel):
    snippet_id: str
    text: str

# -------------------------------------------------
# API Routes
# -------------------------------------------------

@router.post("/respond", response_model=ReplyAtom)
async def respond(payload: RespondIn):
    """一般 1 對 1 對話：前端沒指定角色就用 DEFAULT_CHAR"""
    char_name = payload.char_name or DEFAULT_CHAR  # ★★ fallback
    char_data = load_character_yaml(char_name)
    reply_text = pick_reply(char_data, payload.user_msg)
    return ReplyAtom(name=char_name, reply=reply_text)


@router.post("/snippet/call", response_model=SnippetOut)
async def call_snippet(payload: SnippetCallIn):
    """前端強制插入一段 snippet 劇情"""
    snippet_text = snippets_cache.get(payload.snippet_id)
    if snippet_text is None:
        raise HTTPException(status_code=404, detail="Snippet 不存在")
    return SnippetOut(snippet_id=payload.snippet_id, text=snippet_text)

# -- 如需 GitHub Webhook 自動 git pull，可在此另外補一條路由 --

# -------------------------------------------------
# 最後把 router 掛進 app
# -------------------------------------------------
app.include_router(router)
