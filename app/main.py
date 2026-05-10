from fastapi import FastAPI
from app.api import tenant, user  # ⚠️ O SEGREDO ESTÁ AQUI: adicionar o ', user'
from app.models import Tenant, User 

app = FastAPI(title="NexCore SaaS API")

# Mapeando os Endpoints no Swagger
app.include_router(tenant.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/")
async def root():
    return {"message": "NexCore API is online and operational."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}