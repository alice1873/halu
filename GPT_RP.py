# GPT_RP.py — Minimal single‑character role‑play engine wrapped with FastAPI
# ----------------------------------------------------------------------
# 部署步驟（Render / Railway）
#   1. 將本檔與 character.yaml 放在同一 repo
#   2. 環境變數 CHAR_YAML_PATH 指向角色檔（預設 character.yaml）
#   3. Start command:  python -m uvicorn GPT_RP:app --host 0.0.0.0 --port $PORT
# ----------------------------------------------------------------------
"""
提供：
  • POST  /respond   → 角色依訊息即時回覆
  • POST  /reset     → 清空暫存狀態（佔位用）
  • GET   /health    → 健康檢查

不含長期記憶；若需串接「記憶外掛」，在 respond() 裡呼叫對方 /save API 即可。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Any

import yaml
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

# ----------------------------------------------------------------------
#                         ──  Core Engine  ──
# ----------------------------------------------------------------------

class SoloEngine:
    """最精簡的單一角色回覆引擎。"""

    def __init__(self, char_data: Dict[str, Any]):
        self.char = char_data
        self.name: str = char_data["basic_info"]["name"]
        # speech_patterns: {mood: template}
        self.templates: Dict[str, str] = char_data["speech_patterns"]

    # --- construction helpers -------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str) -> "SoloEngine":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # 極簡驗證
        for key in ("basic_info", "speech_patterns"):
            if key not in data:
                raise ValueError(f"YAML missing required top‑level key: {key}")
        return cls(data)

    # --- internal helpers -----------------------------------------------------
    @staticmethod
    def _detect_mood(msg: str) -> str:
        low = msg.lower()
        if any(x in low for x in ("angry", "mad", "怒", "生氣")):
            return "angry"
        if any(x in low for x in ("happy", "love", "開心", "喜")):
            return "happy"
        return "neutral"

    # --- public API -----------------------------------------------------------
    def respond(self, user_msg: str) -> Dict[str, str]:
        """產生角色回覆字串與 metadata。"""
        mood = self._detect_mood(user_msg)
        template = self.templates.get(mood) or self.templates.get("neutral", "{msg}")
        reply_text = template.format(name=self.name, msg=user_msg)
        return {
            "reply": reply_text,
            "mood": mood,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def reset(self):
        """佔位函式：日後可清空暫存、重設好感度等。"""
        return

# ----------------------------------------------------------------------
#                         ──  FastAPI Layer  ──
# ----------------------------------------------------------------------

router = APIRouter()
CHAR_YAML_PATH = os.getenv("CHAR_YAML_PATH", "character.yaml")
_engine: SoloEngine | None = None

def _load_engine() -> SoloEngine:
    global _engine
    if _engine is None:
        _engine = SoloEngine.from_yaml(CHAR_YAML_PATH)
    return _engine

# ----- Pydantic Schemas -------------------------------------------------------
class MessageIn(BaseModel):
    user_id: str | None = None  # optional,保留給日後串記憶
    message: str

class ReplyOut(BaseModel):
    reply: str
    mood: str
    timestamp: str

# ----- Routes ----------------------------------------------------------------
@router.post("/respond", response_model=ReplyOut)
def respond(payload: MessageIn):
    eng = _load_engine()
    return eng.respond(payload.message)

@router.post("/reset", status_code=204)
def reset():
    eng = _load_engine()
    eng.reset()
    return

@router.get("/health")
def health():
    return {"status": "ok"}

# ----- FastAPI App -----------------------------------------------------------
app = FastAPI(title="Solo Character RP", version="0.1.0")
app.include_router(router)

# ----- Entry point for local dev --------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("GPT_RP:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
