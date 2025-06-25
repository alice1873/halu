# GPT_RP.py
import os
from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

import yaml

# 指定角色卡資料夾
CHAR_DIR = "characters"

# --------- 資料結構定義 ---------
class MessageIn(BaseModel):
    character: str   # 角色英文名稱（檔名去掉 .yaml）
    message: str

class ReplyOut(BaseModel):
    reply: str
    mood: str
    timestamp: str

class MessageIn(BaseModel):
    message: str
    character: Optional[str] = "default"

# --------- 角色卡載入 ---------
def load_character_yaml(char_name):
    """
    依據角色名讀取 characters/char_name.yaml
    """
    path = os.path.join(CHAR_DIR, f"{char_name}.yaml")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"角色卡 {char_name} 不存在！")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # 基本檢查
    for key in ("basic_info", "speech_patterns"):
        if key not in data:
            raise HTTPException(status_code=500, detail=f"{char_name}.yaml 格式錯誤，缺少 {key}")
    return data

def detect_mood(msg):
    low = msg.lower()
    if any(x in low for x in ("angry", "mad", "怒", "生氣")):
        return "angry"
    if any(x in low for x in ("happy", "love", "開心", "喜")):
        return "happy"
    return "neutral"

# --------- FastAPI 與路由 ---------
router = APIRouter()

@router.post("/respond", response_model=ReplyOut)
def respond(payload: MessageIn):
    char_data = load_character_yaml(payload.character)
    name = char_data["basic_info"]["name"]
    templates = char_data["speech_patterns"]
    mood = detect_mood(payload.message)
    template = templates.get(mood) or templates.get("neutral", "{msg}")
    reply_text = template.format(name=name, msg=payload.message)
    return {
        "reply": reply_text,
        "mood": mood,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/list_roles")
def list_roles():
    """
    回傳目前 /characters/ 資料夾下所有角色（去掉 .yaml 副檔名）
    """
    files = [f[:-5] for f in os.listdir(CHAR_DIR) if f.endswith(".yaml")]
    return {"roles": files}

# --------- FastAPI 主體 ---------
app = FastAPI(title="Multi-Character RP", version="1.0.0")
app.include_router(router)

# --------- 本機測試專用 ---------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("GPT_RP:app", host="0.0.0.0", port=8000)
