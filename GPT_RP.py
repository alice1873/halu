from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
import yaml

# --------------------
# 常數設定
# --------------------
CHAR_DIR = "characters"  # 存放角色卡的資料夾
DEFAULT_CHAR = "lazul"  # 沒帶 character 時的預設角色

# --------------------
# 資料結構
# --------------------
class MessageIn(BaseModel):
    """使用者輸入結構

    - message: 必填，對角色說的話
    - character: 選填，不給就用 DEFAULT_CHAR
    """
    message: str
    character: Optional[str] = DEFAULT_CHAR

class ReplyOut(BaseModel):
    """API 回傳結構——只回覆角色台詞，保持簡潔給 GPT 朗讀"""
    reply: str

# --------------------
# 工具函式
# --------------------

def load_character_yaml(char_name: str):
    """讀取對應角色卡 YAML；若不存在則拋 404"""
    path = os.path.join(CHAR_DIR, f"{char_name}.yaml")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"角色卡 {char_name}.yaml 不存在！")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 基本欄位檢查
    for key in ("basic_info", "speech_patterns"):
        if key not in data:
            raise HTTPException(status_code=500, detail=f"{char_name}.yaml 缺少 {key} 區塊")
    return data


def pick_reply(char_data: dict, user_msg: str) -> str:
    """根據使用者訊息與角色口吻回傳一句話（簡易範例）"""
    # 先做非常簡單的情緒偵測
    low = user_msg.lower()
    if any(x in low for x in ("angry", "mad", "怒", "生氣")):
        mood = "angry"
    elif any(x in low for x in ("happy", "love", "開心", "喜")):
        mood = "happy"
    else:
        mood = "neutral"

    tpl = char_data["speech_patterns"].get(mood) or char_data["speech_patterns"].get("neutral", "{msg}")
    name = char_data["basic_info"].get("name", char_data["basic_info"].get("role", "角色"))
    return tpl.format(name=name, msg=user_msg)

# --------------------
# FastAPI + Router
# --------------------
router = APIRouter()

@router.post(
    "/respond",
    operation_id="respond_character",  # 🔑 必須與 OpenAPI/Actions 同名
    response_model=ReplyOut,
)
async def respond(payload: MessageIn):
    """主要對話入口——GPT 工具會呼叫這裡"""
    char_name = payload.character or DEFAULT_CHAR
    char_data = load_character_yaml(char_name)
    reply_text = pick_reply(char_data, payload.message)
    return {"reply": reply_text}

# health 與 list_roles 方便監控 / 除錯
@router.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@router.get("/list_roles")
async def list_roles():
    roles = [f[:-5] for f in os.listdir(CHAR_DIR) if f.endswith(".yaml")]
    return {"roles": roles}

# --------------------
# FastAPI 應用實例
# --------------------
app = FastAPI(title="Simple Multi-Character RP", version="1.0.0")
app.include_router(router)

# --------------------
# 直接執行時（本地測試）
# --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("GPT_RP:app", host="0.0.0.0", port=8000, reload=True)
