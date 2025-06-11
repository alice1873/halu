from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from GPT_RP import router as rp_router      # 角色回應 API
from event_log import router as event_router  # 事件追蹤 API

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rp_router, prefix="/rp")       # 角色回覆（/rp/respond, /rp/reset, /rp/health）
app.include_router(event_router, prefix="/event") # 事件追蹤（/event/log, /event/list）
