from fastapi import FastAPI

from zero_semester.admin.routes import auth, dashboard, public

app = FastAPI(title="Нулевой семестр — админка", version="0.1.0")
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(dashboard.router)


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
