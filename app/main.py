import os
import traceback
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.api import tenant, user, auth, product, payment, audit, dashboard
from app.services.discord import DiscordService

os.makedirs("uploads/products", exist_ok=True)

api_description = """
**NexCore SaaS API** is a high-performance Multi-Tenant Backend architecture designed for absolute data isolation and scalability. 🚀

### 🌟 Core Features
* **Physical Isolation (Dedicated Schemas):** Each tenant owns a secure, dedicated data dimension.
* **Stateless Security:** JWT authentication and Role-Based Access Control (RBAC).
* **High Performance:** Real-time database aggregations (BFF Dashboard).
* **Financial Integration:** Atomic and secure Stripe webhooks.

*Engineered with excellence for the Enterprise market.*
"""

tags_metadata = [
    {"name": "Authentication", "description": "JWT Token generation and validation."},
    {"name": "Tenants", "description": "Global tenant management and billing compliance."},
    {"name": "Users", "description": "Isolated user management within a specific tenant's ecosystem."},
    {"name": "Products", "description": "Catalog management with dimensional isolation (Schemas)."},
    {"name": "Dashboard", "description": "Heavy mathematical aggregations executed directly on the PostgreSQL engine."},
    {"name": "Payments & Webhooks", "description": "Secure Stripe integration for subscription management."},
    {"name": "Audit & Logs", "description": "Immutable traceability of all critical system actions."},
]

app = FastAPI(
    title="NexCore SaaS API",
    description=api_description,
    version="2.0.0-beta",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "Backend Engineering",
        "url": "https://github.com/ccerks/nexcore-saas-api",
    },
    license_info={
        "name": "Enterprise License",
    },
)

# Mount the static directory to serve product images publicly.
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Register SlowAPI rate-limit middleware.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches all unhandled exceptions and sanitises the public response.

    Security note: only the HTTP method, path, and exception *type* are forwarded
    to the Discord webhook. The full stack trace is intentionally withheld from
    external channels to prevent leaking SQL queries, internal state, or PII.
    The complete traceback is written to the application log instead.
    """
    # Safe summary: no stack frames, no variable values, no SQL.
    safe_summary = (
        f"Path: {request.method} {request.url.path}\n"
        f"Exception type: {type(exc).__name__}\n"
        f"Message: {str(exc)[:200]}"  # truncate to avoid accidental data leakage
    )
    DiscordService.send_alert(safe_summary)

    # Full traceback goes to the structured application log, not to external services.
    import logging
    logging.getLogger(__name__).error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Our engineering team has been notified."},
    )


# Router registration
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(tenant.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(product.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(payment.router, prefix="/api/v1/payments", tags=["Payments & Webhooks"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit & Logs"])


@app.get("/")
async def root() -> dict:
    return {"message": "NexCore API is online and operational."}


@app.get("/health")
async def health_check() -> dict:
    """Liveness probe endpoint consumed by Docker and load balancers."""
    return {"status": "healthy"}
