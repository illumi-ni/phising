from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import dashboard, emails, scenarios

app = FastAPI(title="Phishing Simulation & Benchmarking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios.router)
app.include_router(emails.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
