from fastapi import FastAPI

app = FastAPI(title="NexCore SaaS API")

@app.get("/")
async def root():
    return {"message": "NexCore API is online and operational."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}