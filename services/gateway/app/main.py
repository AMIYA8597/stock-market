from fastapi import FastAPI, APIRouter

app = FastAPI(title="NeuroQuant Gateway")

@app.get("/health")
async def health():
    return {"status": "ok"}

api_v1 = APIRouter(prefix="/api/v1")


@api_v1.get("/health")
async def api_health():
    return {"status": "ok", "component": "gateway"}


@api_v1.get("/ping")
async def ping():
    return {"message": "pong from gateway"}


app.include_router(api_v1)
