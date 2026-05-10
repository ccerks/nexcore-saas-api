from fastapi import FastAPI
from app.api import tenant

# Import models to initialize the SQLAlchemy registry and avoid MissingName errors
from app.models import Tenant, User 

app = FastAPI(title="NexCore SaaS API")

app.include_router(tenant.router, prefix="/api/v1/tenants", tags=["Tenants"])

@app.get("/")
async def root():
    return {"message": "NexCore API is online and operational."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}