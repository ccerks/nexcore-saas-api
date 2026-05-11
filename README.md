# NexCore SaaS API 🚀

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-626CD9?logo=Stripe&logoColor=white)

NexCore is a robust, production-ready Multi-Tenant SaaS backend built with **FastAPI**, **PostgreSQL**, and **Redis**. It was designed with a focus on high scalability, data isolation, and modern security patterns.

## 🏗️ Architecture & Stack
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async, Type Safety, OpenAPI)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Cache & Rate Limiting:** [Redis](https://redis.io/)
- **Containerization:** [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **Validation:** [Pydantic V2](https://docs.pydantic.dev/)
- **Security:** JWT Authentication & PostgreSQL Row-Level Security (RLS) on a Shared Schema
- **Payments:** [Stripe Python SDK](https://stripe.com/docs/api)
  
### 🗄️ Database Entity-Relationship (Multi-Tenant Isolation)
```mermaid
erDiagram
    TENANTS ||--o{ USERS : "has"
    TENANTS ||--o{ PRODUCTS : "manages"
    PRODUCTS ||--o{ PRODUCTS : "parent/child (variations)"

    TENANTS {
        uuid id PK
        string name
        string slug
        boolean is_active
        string stripe_customer_id "Billing"
        string stripe_subscription_id "Billing"
    }

    USERS {
        uuid id PK
        uuid tenant_id FK "Data Isolation"
        string email
        string role
    }

    PRODUCTS {
        uuid id PK
        uuid tenant_id FK "Data Isolation"
        uuid parent_id FK "SKU Variations"
        string name
        string sku_pai
        json attributes
        float price
    }
````
## 🌟 Key Features
- **Multi-tenancy:** Efficient data isolation using tenant_id pattern and Row-Level Security (RLS).
- **Payment Gateway & Billing:** Stripe SDK integration for customer provisioning using Atomic Database Transactions (Flush/Rollback), paired with a secure Webhook listener for real-time churn control and automated tenant deactivation.
- **Advanced Catalog:** Complex product management supporting hierarchical SKU variations (parent/child relationships) and JSON-based dynamic attributes.
- **UUIDs:** All entities use UUID v4 for enhanced security and non-predictable IDs.
- **Automated Migrations:** Database versioning with Alembic.
- **Clean Architecture:** Organized structure for easy maintenance and scaling.
- **Interactive API Docs:** Auto-generated Swagger and ReDoc.
- **Performance & Observability:** Global rate limiting using the Sliding Window Counter algorithm via Redis Lua scripts (SlowAPI) to mitigate brute-force attacks, coupled with a centralized exception handler that sanitizes client responses and dispatches real-time stack traces to a Discord webhook.

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
3. Spin up the infrastructure::
   ```bash
   docker-compose up --build -d
   ```
4. Run migrations::
   ```bash
   docker-compose exec api alembic upgrade head
   ```
The API will be available at http://localhost:8000
Check the docs at http://localhost:8000/docs

## 🛠️ Project Structure
```text
  app/
  ├── api/        # Route handlers (Endpoints)
  ├── core/       # Global configs (Security, JWT, Env)
  ├── db/         # Session management & engine
  ├── models/     # SQLAlchemy database models
  ├── schemas/    # Pydantic data contracts
  ├── services/   # Business logic (Service layer)
scripts/
  └── create_admin.py # Utility for initial system setup
```
## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation**
  - [x] Clean Architecture setup
  - [x] Docker & Docker Compose orchestration
  - [x] PostgreSQL & Redis integration
  - [x] Alembic migrations setup
        
- [x] **Phase 2: Identity & Multi-Tenancy**
  - [x] Tenant model and isolation logic
  - [x] User model and relational mapping
  - [x] JWT Authentication (Access & Refresh tokens)
  - [x] Role-Based Access Control (RBAC)
        
- [X] **Phase 3: E-commerce & Payments Core**
  - [x] Product and Inventory models per Tenant
  - [x] Stripe API integration for subscription billing
  - [x] Webhook listener for async payment events
        
- [X] **Phase 4: Performance & Observability**
  - [X] Advanced Rate Limiting with Redis
  - [X] Global exception handling and Discord alerts
  - [X] CI/CD Pipeline (GitHub Actions)

-  [ ] **Phase 5: Enterprise & Advanced Integrations**
  - [ ] Asynchronous messaging and notifications via RabbitMQ
  - [ ] Tenant-level audit logging
  - [ ] Usage dashboards and telemetry
  - [ ] Physical database isolation strategies (Dedicated Schemas)

**Developed by** [Caio Cerqueira](https://github.com/ccerks) 🚀
