# NexCore SaaS API 🚀

![Version](https://img.shields.io/badge/version-2.0.0--beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?logo=rabbitmq&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-626CD9?logo=Stripe&logoColor=white)

NexCore is a robust, production-ready Multi-Tenant SaaS backend. In version 2.0.0, the architecture was upgraded to an **Enterprise Dedicated Schema** model, ensuring absolute physical data isolation, asynchronous performance tuning, and event-driven background processing.

## 🏗️ Architecture & Stack
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async, Type Safety, OpenAPI)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Multi-Tenancy:** Dedicated PostgreSQL Schemas (Physical Isolation)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/) (Dynamic Schema Routing)
- **Cache & Rate Limiting:** [Redis](https://redis.io/)
- **Message Broker:** [RabbitMQ](https://www.rabbitmq.com/) (Event-Driven Background Tasks)
- **Async I/O Storage:** `aiofiles` for non-blocking media handling
- **Containerization:** [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **Validation:** [Pydantic V2](https://docs.pydantic.dev/)
- **Security:** JWT Authentication & Cross-Schema SQL Sniper Queries
- **Payments:** [Stripe Python SDK](https://stripe.com/docs/api)

### 🗄️ Database Entity-Relationship (Physical Schema Isolation)
NexCore utilizes a strict multi-dimensional database topology. Global entities reside in the `public` schema, while each tenant gets a dynamically provisioned isolated schema (`tenant_<slug>`). Foreign keys securely cross these boundaries.

```mermaid
erDiagram
    %% GLOBAL MAP (public schema)
    public_TENANTS ||--o{ public_USERS : "has"
    
    %% ISOLATED ZONES (tenant_* schemas)
    public_TENANTS ||--o{ tenant_PRODUCTS : "manages"
    public_TENANTS ||--o{ tenant_AUDIT_LOGS : "has records"
    public_USERS ||--o{ tenant_AUDIT_LOGS : "performs"
    tenant_PRODUCTS ||--o{ tenant_PRODUCTS : "parent/child (variations)"

    public_TENANTS {
        uuid id PK
        string name
        string slug
        boolean is_active
        string stripe_customer_id "Billing"
        string stripe_subscription_id "Billing"
    }

    public_USERS {
        uuid id PK
        uuid tenant_id FK "Global Identity Anchor"
        string email
        string role
    }

    tenant_PRODUCTS {
        uuid id PK
        uuid tenant_id FK "Cross-Schema Ref"
        uuid parent_id FK "SKU Variations"
        string name
        string sku_pai
        string image_url "Storage Path"
        json attributes
        float price
        datetime deleted_at "Soft Delete"
    }

    tenant_AUDIT_LOGS {
        uuid id PK
        uuid tenant_id FK "Cross-Schema Ref"
        uuid user_id FK "Actor Ref"
        string action "CREATE/UPDATE/DELETE"
        string entity_name
        json changes "Snapshot"
    }
```

## 🌟 Key Features
- **Enterprise Multi-tenancy:** Physical data isolation via dynamically generated PostgreSQL schemas per tenant. Prevents data leakage at the database engine level.
- **Cross-Schema Validation:** Employs raw SQL "Sniper Queries" to validate global states (e.g., Free Tier limits) directly from the `public` schema without losing the tenant's transaction context.
- **Event-Driven Architecture:** Asynchronous background task processing using RabbitMQ (e.g., orphaned image cleanup and Discord Webhooks) to guarantee non-blocking HTTP responses.
- **Asynchronous Storage I/O:** Utilizes `aiofiles` for true async multipart file uploads, protecting the FastAPI event loop during heavy disk writes.
- **Payment Gateway & Billing:** Stripe SDK integration using Atomic Database Transactions, paired with a secure Webhook listener.
- **High-Performance Ingestion (Bulk Insert):** Atomic batch processing for catalogs.
- **Audit & Traceability:** Immutable audit logging stored safely within the tenant's isolated dimension.
- **Performance & Observability:** Global rate limiting using the Sliding Window Counter algorithm via Redis. Centralized exception handler that sanitizes responses and dispatches real-time stack traces to Discord.

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose installed.
- Stripe account (Test Mode Keys).

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/ccerks/nexcore-saas-api.git](https://github.com/ccerks/nexcore-saas-api.git)
   cd nexcore-saas-api
   ```
2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
3. Spin up the infrastructure:
   ```bash
   docker-compose up --build -d
   ```
4. Run migrations (This creates the global schema architecture):
   ```bash
   docker-compose exec api alembic upgrade head
   ```
5. Provision the initial Administrator:
   ```bash
   docker-compose exec api python scripts/create_admin.py
   ```

The API will be available at `http://localhost:8000`
Check the interactive docs at `http://localhost:8000/docs`

## 💳 Stripe Setup & Local Testing
To handle real-time billing events (Webhooks) during development:

1. **Configure API Keys:** Add your `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to `.env`.
2. **Start the Webhook Tunnel:** Use the Stripe CLI to forward events:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/webhook
   ```

## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation**
  - [x] Clean Architecture setup
  - [x] Docker & Docker Compose orchestration
  - [x] PostgreSQL & Redis integration
  - [x] Alembic migrations setup
        
- [x] **Phase 2: Identity & Base Multi-Tenancy**
  - [x] Tenant and User models
  - [x] JWT Authentication & RBAC
        
- [x] **Phase 3: E-commerce & Payments Core**
  - [x] Product and Inventory models
  - [x] Bulk Insert functionality (Horde Encounters)
  - [x] Stripe API integration & Webhook listener
  - [x] Secure File/Image Storage handling
        
- [x] **Phase 4: Performance & Observability**
  - [x] Advanced Rate Limiting with Redis
  - [x] Global exception handling and Discord alerts
  - [x] Automated Testing Suite (Pytest + Faker)

- [x] **Phase 5: Enterprise Architecture (v2.0.0)**
  - [x] Physical database isolation strategies (Dedicated Schemas)
  - [x] Alembic dynamic routing logic (`include_object`)
  - [x] Asynchronous Storage I/O (`aiofiles`)
  - [x] Asynchronous messaging via RabbitMQ
  - [x] Tenant-level isolated audit logging

**Developed by** [Caio Cerqueira](https://github.com/ccerks) 🚀