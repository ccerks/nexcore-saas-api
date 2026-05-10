from fastapi import FastAPI
from app.api import tenant, user, auth, product
from app.models import Tenant, User, Product

app = FastAPI(title="NexCore SaaS API")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(tenant.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(product.router, prefix="/api/v1/products", tags=["Products"])

@app.get("/")
async def root():
    return {"message": "NexCore API is online and operational."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}