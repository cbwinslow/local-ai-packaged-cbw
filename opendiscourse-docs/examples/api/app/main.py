from fastapi import FastAPI

app = FastAPI(title="OpenDiscourse API")

@app.get("/health")
def health():
    return {"ok": True}
