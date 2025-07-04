# 🐾 VetAnalytics – FastAPI Backend

An **object-oriented, production-ready** FastAPI backend for analysing veterinary blood test PDFs with **GPT-4o Vision**. The service exposes RESTful APIs that cover patient management, AI-powered diagnostics, and full JWT-based authentication with human-readable IDs (e.g. `PAT-001`, `VET-001`, `ADM-001`).

---

## 🚀 Quick Start

```bash
# 1. Clone repository
$ git clone <repo-url>
$ cd bloodwork-backend

# 2. Create and activate virtual environment
$ python -m venv venv
$ source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
$ pip install -r requirements.txt

# 4. Create .env file (see Configuration)

# 5. Run dev server
$ uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs to explore the interactive API.

---

## 🏗️ High-Level Architecture

```
app/
├── main.py                     # FastAPI instance & wiring
├── auth/                       # JWT auth, hashing, token logic
│   ├── auth_service.py         # Core authentication workflow
│   ├── token_service.py        # JWT encode / decode helpers
│   └── password_service.py     # BCrypt hashing & validation
├── routers/                    # API layer (one router per domain)
│   ├── auth_router.py          # /auth/* endpoints
│   ├── patient_router.py       # /patients/* endpoints
│   ├── analysis_router.py      # /analysis/* PDF upload & processing
│   └── diagnostic_router.py    # /diagnostics/* AI results
├── models/                     # Pydantic DB models with readable IDs
│   └── database_models.py      # Patient, User, Admin, Diagnostic, ...
├── repositories/               # Data access layer (MongoDB async)
│   ├── patient_repository.py   # CRUD + soft-delete
│   ├── user_repository.py      # Vet / Technician accounts
│   ├── admin_repository.py     # Admin accounts
│   ├── ai_diagnostic_repo.py   # Diagnostic persistence
│   └── refresh_token_repo.py   # Refresh token storage
├── services/                   # Business logic / external integrations
│   ├── pdf_analysis_service.py # End-to-end PDF → AI report pipeline
│   ├── openai_service.py       # GPT-4o Vision interface
│   └── database_service.py     # Async MongoDB / GridFS wrapper
├── dependencies/               # FastAPI DI helpers
│   └── auth_dependencies.py    # `Depends(...)` for auth / roles
├── prompts/                    # System & extraction prompts
└── utils/                      # Logging, file helpers, etc.
```

The code follows **Clean Architecture** and **SOLID** principles:

- **Domain-driven models** (Pydantic)
- **Repository pattern** for data persistence
- **Service layer** for business rules & external APIs
- **Router layer** (presentation)
- Dependency Injection between layers

---

## 🔑 Key Features

1. **Human-Readable Sequential IDs**  
   `PAT-001`, `VET-042`, `DGN-155` generated atomically in MongoDB – no ObjectIds exposed to the client.
2. **JWT Authentication**  
   Access & Refresh tokens (`HS256`), role embedded, full revoke / logout-all.
3. **Role-Based Access Control**  
   Admin, Veterinarian, Technician guards via FastAPI dependencies.
4. **AI-Powered Bloodwork Analysis**  
   GPT-4o Vision processes 300 DPI images extracted from uploaded PDFs. Results returned as structured JSON in Italian.
5. **Asynchronous Processing**  
   Heavy analysis runs in the background; endpoints return polling IDs.
6. **GridFS File Storage**  
   Original PDFs stored in MongoDB GridFS with metadata.
7. **Centralised Logging**  
   Singleton logger with module-level children and formatted output.
8. **Clean Error Handling**  
   3-tiered (service → router → global) with meaningful HTTP codes.
9. **Docker-Ready**  
   No Dockerfile included by default, but codebase is 12-factor compliant.

---

## 🛣️ API Overview (v1)

### Authentication – `/auth`

| Method | Path          | Description                                       |
| ------ | ------------- | ------------------------------------------------- |
| POST   | `/register`   | Register Vet / Technician (pending approval)      |
| POST   | `/login`      | Obtain **access** + **refresh** tokens            |
| POST   | `/refresh`    | Swap a valid refresh token for a new access token |
| POST   | `/logout`     | Invalidate a single refresh token                 |
| POST   | `/logout/all` | Invalidate **all** devices for current user       |
| GET    | `/profile`    | Get own profile                                   |
| PUT    | `/profile`    | Update own profile / email                        |
| PUT    | `/password`   | Change password                                   |

Admin-only endpoints for user approval / management are exposed under `/auth/admin/*` (see Swagger).

### Patients – `/patients`

| Method | Path             | Description                    |
| ------ | ---------------- | ------------------------------ |
| POST   | `/`              | Create patient (Vet / Admin)   |
| GET    | `/`              | Paginated list (auth required) |
| GET    | `/{patient_id}`  | Get single record              |
| PUT    | `/{patient_id}`  | Update                         |
| DELETE | `/{patient_id}`  | Soft delete                    |
| GET    | `/search/{name}` | Full-text search               |

### Analysis & Diagnostics – `/analysis`, `/diagnostics`

1. **Upload PDF** – `POST /analysis/pdf_analysis`  
   Receives multipart PDF, returns `{ diagnostic_id }` immediately.
2. **Check Result** – `GET /analysis/pdf_analysis_result/{id}`
3. **Patient Diagnostics** – `/diagnostics/patient/{patient_id}` (list, latest, tests-count, pending-status).

All diagnostic JSON conforms to the schemas in `app/schemas/diagnostic_schemas.py`.

---

## ⚙️ Configuration

Create `.env` in `bloodwork-backend/`:

```env
# ===== General =====
OPENAI_API_KEY=<your-key>

# ===== MongoDB =====
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=veterinary_bloodwork

# ===== JWT =====
JWT_SECRET_KEY=change-me-in-prod
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

Optional AWS keys are only required if you enable EC2 auto-scaling in `utils/ec2_instance_controller.py` (currently disabled).

---

## 📦 Python Dependencies (excerpt)

Dependency versions are pinned in `requirements.txt`. Key libraries:

- `fastapi` – Web framework
- `uvicorn` – ASGI server
- `motor` – Async MongoDB driver
- `python-multipart` – File uploads
- `PyMuPDF` – PDF → image conversion (300 DPI)
- `openai` – GPT-4o Vision
- `passlib[bcrypt]` – Secure password hashing
- `python-dotenv` – `.env` loader
- `pydantic` – Data validation

---

## 🧪 Testing & Health

- **Health Check:** `GET /api/health` returns `{ "status": "healthy" }`.
- **Protected Test:** `GET /api/protected` requires Bearer token.
- **Manual Endpoint Testing** – see examples below.

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"demo","password":"secret"}'

# Upload PDF for analysis
curl -X POST http://localhost:8000/analysis/pdf_analysis \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     -F "file=@bloodwork.pdf" \
     -F "patient_id=PAT-001"
```

---

## 🛠️ Development Notes

- **ID Generation** – implemented via `DatabaseService.get_next_sequential_id()` using an atomic `$inc` on a `counters` collection.
- **Refresh Token Storage** – SHA-256 hashed token, expiry indexed, invalidated on logout.
- **BackgroundTasks** – built-in FastAPI background runner; swap with Celery if throughput grows.

---

## 🤝 Contributing

1. Fork & create a feature branch.
2. Follow **PEP-8** and include type hints.
3. Write docstrings and add logging.
4. Submit a PR with a clear description.

---

## 📄 License

Proprietary software. All rights reserved.
