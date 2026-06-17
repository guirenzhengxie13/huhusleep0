from fastapi import FastAPI

from app.api.import_api import router as import_router


app = FastAPI(title="HuhuSleep Import Debug API")
app.include_router(import_router)


@app.get("/")
def root():
    return {"ok": True, "service": "huhusleep-import-debug"}

