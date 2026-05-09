# NexCore SaaS API 🚀

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

NexCore is a robust, production-ready Multi-Tenant SaaS backend built with **FastAPI**, **PostgreSQL**, and **Redis**. It was designed with a focus on high scalability, data isolation, and modern security patterns.

## 🏗️ Architecture & Stack
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async, Type Safety, OpenAPI)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Cache & Rate Limiting:** [Redis](https://redis.io/)
- **Containerization:** [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **Validation:** [Pydantic V2](https://docs.pydantic.dev/)
- **Security:** JWT Authentication & Row-Level Isolation (Shared Schema)
  
### 🗄️ Database Entity-Relationship (Multi-Tenant Isolation)
```mermaid
erDiagram
    TENANTS ||--o{ USERS : "has"
    TENANTS ||--o{ PRODUCTS : "manages"
    USERS ||--o{ PRODUCTS : "creates"

    TENANTS {
        uuid id PK
        string name
        string slug
        boolean is_active
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
        string name
        float price
    }
````
## 🌟 Key Features
- **Multi-tenancy:** Efficient data isolation using `tenant_id` pattern.
- **UUIDs:** All entities use UUID v4 for enhanced security and non-predictable IDs.
- **Automated Migrations:** Database versioning with Alembic.
- **Clean Architecture:** Organized structure for easy maintenance and scaling.
- **Interactive API Docs:** Auto-generated Swagger and ReDoc.

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose installed.

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/ccerks/nexcore-saas-api.git](https://github.com/ccerks/nexcore-saas-api.git)
   cd nexcore-saas-api
   ```
2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your local credentials if needed
   ```
3. Spin up the infrastructure::
   ```bash
   docker-compose up --build -d
   ```
4. Run migrations::
   ```bash
   docker-compose exec api alembic upgrade head
   ```
The API will be available at http://localhost:8000.
Check the docs at http://localhost:8000/docs.

## 🛠️ Project Structure
```plaintext
  app/
  ├── api/        # Route handlers (Endpoints)
  ├── core/       # Global configs (Security, JWT, Env)
  ├── db/         # Session management & engine
  ├── models/     # SQLAlchemy database models
  ├── schemas/    # Pydantic data contracts
  └── services/   # Business logic (Service layer)
```
## 🗺️ Development Roadmap

- [x] **Phase 1: Foundation**
  - [x] Clean Architecture setup
  - [x] Docker & Docker Compose orchestration
  - [x] PostgreSQL & Redis integration
  - [x] Alembic migrations setup

- [ ] **Phase 2: Identity & Multi-Tenancy**
  - [ ] Tenant model and isolation logic
  - [ ] User model and relational mapping
  - [ ] JWT Authentication (Access & Refresh tokens)
  - [ ] Role-Based Access Control (RBAC)

- [ ] **Phase 3: E-commerce & Payments Core**
  - [ ] Product and Inventory models per Tenant
  - [ ] Stripe API integration for subscription billing
  - [ ] Webhook listener for async payment events

- [ ] **Phase 4: Performance & Observability**
  - [ ] Advanced Rate Limiting with Redis
  - [ ] Global exception handling and Discord alerts
  - [ ] CI/CD Pipeline (GitHub Actions)

**Developed by** [Caio Cerqueira](https://github.com/ccerks) 🚀
   
   
