# Aurelia Backend

FastAPI backend cho nền tảng phỏng vấn AI. Hiện tại đã có **authentication & authorization** (JWT).

## Auth API

| Method | Path | Mô tả |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Đăng ký HR (`username`, `email`, `password`) |
| `POST` | `/api/v1/auth/login` | Đăng nhập (`email`, `password`) |
| `GET` | `/api/v1/auth/me` | Lấy user hiện tại (Bearer token) |
| `GET` | `/api/v1/auth/me/hr` | Route mẫu yêu cầu role HR |

Response token:

```json
{ "access_token": "...", "token_type": "bearer" }
```

User (`/me`):

```json
{ "id": 1, "username": "hr_user", "email": "hr@demo.com", "role": "hr" }
```

## Chạy bằng Docker Compose (khuyến nghị)

Từ **repo root**:

```bash
cp .env.example .env   # chỉnh JWT_SECRET / POSTGRES_PASSWORD nếu cần
docker compose up -d --build
```

- PostgreSQL: `localhost:5432` (user/db: `aurelia`)
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- User data lưu trong volume `postgres_data`

Dừng stack:

```bash
docker compose down        # giữ data
docker compose down -v     # xóa volume PostgreSQL
```

## Chạy local + uvicorn (tùy chọn, khi debug code)

```bash
docker compose up -d postgres   # chỉ DB
cd backend
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Chạy local + SQLite (không Docker)

Trong `backend/.env` đặt `DATABASE_URL=sqlite:///./data/aurelia.db`, rồi chạy uvicorn như trên.

Dừng stack:

```bash
docker compose down        # giữ data
docker compose down -v     # xóa volume PostgreSQL
```

Frontend dev proxy `/api` → `http://localhost:8000` (xem `configs/frontend-services.yml`).

## Test

```bash
.venv/bin/python -m pytest tests/ -q
```

## Authorization

- JWT payload chứa `sub` (user id) và `role` (`hr` | `admin`).
- Dùng dependency `require_hr_user` cho các endpoint HR-only (interviews, reports, …).
- Candidate endpoints (phòng phỏng vấn) sẽ public hoặc dùng meeting token — làm ở bước sau.