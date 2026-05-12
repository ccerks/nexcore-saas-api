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
We utilize a **Shared Schema** approach where all Tenants reside in the same database but are logically isolated.

- **Data Isolation:** Every critical table (Users, Products, etc.) contains a `tenant_id` foreign key.
- **Query Filtering:** All database queries are automatically filtered by the `tenant_id` extracted from the JWT, ensuring a Merchant can never access another Merchant's data.

```mermaid
erDiagram
    TENANTS ||--o{ USERS : "has"
    TENANTS ||--o{ PRODUCTS : "manages"
    TENANTS ||--o{ AUDIT_LOGS : "has records"
    USERS ||--o{ AUDIT_LOGS : "performs"
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
        string image_url "Storage Path"
        json attributes
        float price
    }

    AUDIT_LOGS {
        uuid id PK
        uuid tenant_id FK "Data Isolation"
        uuid user_id FK "Actor"
        string action "CREATE/UPDATE/DELETE"
        string entity_name
        string entity_id
        json changes "Snapshot"
        datetime created_at
    }
```

## 🌟 Key Features
- **Multi-tenancy:** Efficient data isolation using tenant_id pattern and Row-Level Security (RLS).
- **Payment Gateway & Billing:** Stripe SDK integration for customer provisioning using Atomic Database Transactions (Flush/Rollback), paired with a secure Webhook listener for real-time churn control and automated tenant deactivation.
- **Advanced Catalog:** Complex product management supporting hierarchical SKU variations (parent/child relationships) and JSON-based dynamic attributes.
- **Secure Storage:** Managed multipart file uploads for product images, with UUID-based renaming and protected static serving.
- **Audit & Traceability:** Immutable audit logging for critical entity actions, safely stored via atomic transactions.
- **UUIDs:** All entities use UUID v4 for enhanced security and non-predictable IDs.
- **Automated Migrations:** Database versioning with Alembic.
- **Clean Architecture:** Organized structure for easy maintenance and scaling.
- **Interactive API Docs:** Auto-generated Swagger and ReDoc.
- **Performance & Observability:** Global rate limiting using the Sliding Window Counter algorithm via Redis Lua scripts (SlowAPI) to mitigate brute-force attacks. Paginated endpoints for large catalogs. Centralized exception handler that sanitizes client responses and dispatches real-time stack traces to a Discord webhook.

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
4. Run migrations:
   ```bash
   docker-compose exec api alembic upgrade head
   ```
The API will be available at http://localhost:8000
Check the docs at http://localhost:8000/docs

## 💳 Stripe Setup & Local Testing
To handle real-time billing events (Webhooks) during development, follow these steps:

1. **Configure API Keys:** Ensure your `.env` contains:
   - `STRIPE_SECRET_KEY`: Your Stripe Secret Key (sk_test_...).
   - `STRIPE_WEBHOOK_SECRET`: The secret generated by the Stripe CLI (whsec_...).

2. **Install Stripe CLI:** Download the official [Stripe CLI](https://github.com/stripe/stripe-cli/releases) and place the executable in the project root.

3. **Start the Webhook Tunnel:**
   Open a terminal and run the "PSS Radar":
   ```bash
   ./stripe listen --forward-to localhost:8000/api/v1/payments/webhook
   ```

4. **Trigger Test Events:**
   ```bash
   ./stripe trigger customer.subscription.deleted
   ```

## 📡 Observability & Monitoring
The system features a Global Exception Handler that monitors the health of the API in real-time.

- **Discord Integration:** Any `500 Internal Server Error` triggers an automated alert via Webhook.
- **Payload Sanitization:** While the engineering team receives the full stack trace on Discord, the end-user only sees a sanitized, secure error message to prevent information leakage.

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
        
- [x] **Phase 3: E-commerce & Payments Core**
  - [x] Product and Inventory models per Tenant
  - [x] Stripe API integration for subscription billing
  - [x] Webhook listener for async payment events
  - [x] Secure File/Image Storage handling
        
- [x] **Phase 4: Performance & Observability**
  - [x] Advanced Rate Limiting with Redis
  - [x] Paginated endpoints for resource lists
  - [x] Global exception handling and Discord alerts
  - [x] CI/CD Pipeline (GitHub Actions)

- [x] **Phase 5: Enterprise & Advanced Integrations**
  - [x] Tenant-level audit logging
  - [ ] Usage dashboards and telemetry
  - [ ] Asynchronous messaging and notifications via RabbitMQ
  - [ ] Physical database isolation strategies (Dedicated Schemas)

**Developed by** [Caio Cerqueira](https://github.com/ccerks) 🚀