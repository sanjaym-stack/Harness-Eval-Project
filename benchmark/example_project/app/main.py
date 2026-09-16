from fastapi import FastAPI

from app.users import router as users_router

app = FastAPI(title="Benchmark Demo App")
app.include_router(users_router)
