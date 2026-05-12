# NexCore SaaS API 🚀

NexCore is a high-performance, multi-tenant e-commerce backend built with **FastAPI**. Designed with scalability and clean architecture in mind, it provides a robust foundation for managing complex product catalogs with strict data isolation.

## 🛠️ Tech Stack

* **Framework:** FastAPI
* **Database:** PostgreSQL + SQLAlchemy 2.0 (ORM)
* **Migrations:** Alembic
* **Security:** JWT Authentication + Password Hashing (Passlib)
* **Validation:** Pydantic V2
* **Infrastructure:** Docker & Docker Compose
* **Monitoring:** Discord Integration (Real-time Error Alerts)

## 🌟 Advanced Features

### 🏢 Multi-tenant Architecture
* **Strict Isolation:** Data is segmented by `tenant_id` at the database level.
* **Security Injection:** The `tenant_id` is automatically extracted from the JWT token, preventing any cross-tenant data leaks.

### 📦 Product Management (Enterprise Ready)
* **Generic Pagination:** Implements a reusable pagination schema (`PaginatedResponse[T]`) for all list endpoints, ensuring high performance even with millions of records.
* **Smart Search:** Case-insensitive filtering by product name using `ILIKE` operations.
* **Image Handling:** Secure multipart file uploads. Images are renamed with UUIDs and served via a protected static route.

### 🕵️ Audit & Traceability (The "Black Box")
* **Atomic Transactions:** Audit logs are saved within the same transaction as the main action. If a product fails to save, the log isn't recorded, and vice-versa.
* **Change Tracking:** Stores full JSON snapshots of created/modified entities to track historical changes.
* **Role-based Visibility:** Tenants can access their own audit logs to monitor user activity within their store.

### 🛡️ Resilience & Security
* **Rate Limiting:** Protection against brute-force attacks using SlowAPI.
* **Global Exception Handler:** All 500 errors are sanitized for the user and dispatched with full stack traces to an engineering Discord channel.
* **Relational Integrity:** Complex self-referential relationships for parent/child product variations (SKU hierarchy).

## 🚀 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/nexcore-saas-api.git](https://github.com/your-username/nexcore-saas-api.git)
    ```
2.  **Set up environment variables:**
    Copy `.env.example` to `.env` and fill in your database and Discord credentials.
3.  **Spin up the environment:**
    ```bash
    docker-compose up --build
    ```
4.  **Run Migrations:**
    ```bash
    docker-compose exec api alembic upgrade head
    ```
5.  **Access Documentation:**
    Navigate to `http://localhost:8000/docs` to explore the Interactive Swagger UI.

## 🏛️ Architecture Principles

* **SOLID & DRY:** Code organized into Services, Models, and Schemas to ensure single responsibility and reusability.
* **KISS:** Prioritizing simple, maintainable solutions over unnecessary complexity.
* **Clean Code:** Focused on readability, type safety, and standardized RESTful patterns.

---
Developed with focus on high-scale performance and reliability.