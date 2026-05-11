from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.api import tenant, user, auth, product, payment
from app.services.discord import DiscordService

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json"
)

# Register SlowAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register Global Exception Handler for 500 Errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions, sanitizes the user response,
    and dispatches the stack trace to the engineering team via Discord.
    """
    # Formats the error context
    error_context = f"Path: {request.method} {request.url.path}\nError: {str(exc)}\n"
    
    # Transmits to Discord
    DiscordService.send_alert(error_context)
    
    # Returns a sanitized generic message to the client (Security standard)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Our engineering team has been notified."},
    )

# Router Registration
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(tenant.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(product.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(payment.router, prefix="/api/v1/payments", tags=["Payments & Webhooks"])

@app.get("/")
async def root():
    return {"message": "NexCore API is online and operational."}

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    mod to trigger a simulated critical failure.
    """
    # Simulated critical failure to test Discord alerting
    #raise Exception("Simulated Core System Failure - Testing Discord Integration")
    
    return {"status": "healthy"}