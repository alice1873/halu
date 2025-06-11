from fastapi import APIRouter
from pydantic import BaseModel
import yaml
from datetime import datetime

EVENT_YAML = "events.yaml"
router = APIRouter()

class EventIn(BaseModel):
    user: str
    event: str

@router.post("/log")
def log_event(payload: EventIn):
    event = {
        "user": payload.user,
        "event": payload.event,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(EVENT_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
    except FileNotFoundError:
