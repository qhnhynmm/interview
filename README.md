# InterviewAI Aurelia

**Nền tảng phỏng vấn tuyển dụng AI end-to-end** — từ tạo link phỏng vấn, phỏng vấn voice realtime, bài tập coding/cognitive, proctoring trong trình duyệt, đến chấm điểm và báo cáo PDF cho HR.

Aurelia phục vụ hai nhóm người dùng trên cùng một hệ thống:

| Vai trò | Làm gì |
| --- | --- |
| **HR** | Đăng ký, upload CV + JD, tạo buổi phỏng vấn, theo dõi trạng thái, xem report & hồ sơ ứng viên |
| **Ứng viên** | Mở meeting link, đọc quy định, bật camera/mic, phỏng vấn voice với AI, làm bài tập, nộp bài |

---

## Mục lục

- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc](#kiến-trúc)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Cấu trúc repo](#cấu-trúc-repo)
- [Cấu hình](#cấu-hình)
- [Luồng nghiệp vụ](#luồng-nghiệp-vụ)
- [API & tài liệu agent](#api--tài-liệu-agent)
- [Phát triển local](#phát-triển-local)
- [Test](#test)
- [Deploy production](#deploy-production)
- [Troubleshooting](#troubleshooting)

---

## Tính năng chính

### HR Workspace
- Đăng ký / đăng nhập JWT
- Form tạo interview: CV (PDF/DOCX/TXT), JD, vị trí, seniority, ngôn ngữ, giọng AI, slot hẹn
- SSE progress khi Planning + Assignment agent chạy
- Bảng kết quả realtime (poll + SSE `report_ready`)
- Hồ sơ ứng viên: CV đã extract, transcript, recording, report JSON, tải PDF

### Phòng phỏng vấn (Candidate)
- LiveKit voice room — AI interviewer nói chuyện qua Gemini Live
- Chuyển UI giữa **interview mode** và **code mode** (data message từ agent)
- Bài tập:
  - **DSA** — Monaco Editor + Python test runner
  - **Project** — Sandpack React sandbox
  - **Cognitive** — 10 câu MCQ
- AI coding assistant (bật/tắt theo loại bài)
- Proctoring trong browser: tab switch, multi-face, gaze-away, phone, external monitor (MediaPipe)
- Ghi hình camera + audio, upload chunk/final lên MinIO
- Proctoring events fire-and-forget → backend → LiveKit agent

### AI Agents (4-agent panel)
| Agent | Thời điểm chạy | Output |
| --- | --- | --- |
| **Planning** | Tạo link | 3 markdown briefs + competencies + directive |
| **Assignment** | Sau Planning | JSON bài tập (coding / cognitive) |
| **Interview** | Candidate join room | Voice Q&A, switch mode, transcript |
| **Inspector** | Kết thúc phỏng vấn | Scorecard + report PDF |

Mỗi agent có **fallback deterministic** khi LLM hoặc service không khả dụng — hệ thống vẫn trả HTTP 200.

---

## Kiến trúc

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15)          http://localhost:8080                   │
│  /  /interview/:id  /candidate/:id                                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ /api/v1/*
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)              http://localhost:8000                 │
│  Auth · Interviews · LiveKit tokens · Report worker · Object storage    │
└───────┬─────────────────────────────┬───────────────────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────┐            ┌────────────────────────────────────────┐
│  PostgreSQL   │            │  AI Services (FastAPI)  :8001            │
│  source of    │◄── MCP ────│  Planning · Assignment · Inspector       │
│  truth        │   httpx    │  Coding Assistant · MCP toolbox          │
└───────────────┘            └───────────────┬────────────────────────────┘
        │                                    │
        ▼                                    ▼
┌───────────────┐            ┌────────────────────────────────────────┐
│  MinIO        │            │  Interview Worker (LiveKit agent)        │
│  cvs ·        │            │  Gemini Live voice · MCP tools           │
│  recordings · │            └───────────────┬────────────────────────────┘
│  reports      │                            │
└───────────────┘                            ▼
                               ┌────────────────────────────────────────┐
                               │  LiveKit Server         ws://:7880      │
                               └────────────────────────────────────────┘
```

**Nguyên tắc thiết kế**
- Postgres là **single source of truth** cho interview state
- AI Services **không** ghi DB trực tiếp — gọi Backend qua MCP HTTP + `X-Service-Key`
- Frontend gọi Backend qua `/api` (Next.js proxy trong Docker, Vite/Next dev proxy khi local)
- CV, recording, report PDF lưu MinIO (S3-compatible); path trong DB dạng `s3://bucket/key`

---

## Tech stack

| Layer | Công nghệ |
| --- | --- |
| Frontend | Next.js 15, React 19, LiveKit Client, Monaco, Sandpack, MediaPipe |
| Backend | FastAPI, SQLAlchemy, PostgreSQL, JWT, boto3/MinIO |
| AI Services | FastAPI, Agent Framework (MAF), Gemini, MCP (FastMCP) |
| Voice | LiveKit Server + `livekit-agents` + Gemini Live plugin |
| Storage | PostgreSQL, MinIO |
| Observability | OpenTelemetry → Arize Phoenix (profile `observability`) |
| Infra | Docker Compose, Nginx, AWS EC2 scripts |

---

## Quick start

### Yêu cầu
- Docker & Docker Compose
- `GEMINI_API_KEY` (bắt buộc để parse CV PDF/DOCX và chạy agents đầy đủ)

### Chạy toàn bộ stack (khuyến nghị)

```bash
git clone <repo-url> interview
cd interview

cp .env.example .env
# Chỉnh GEMINI_API_KEY, JWT_SECRET trong .env

docker compose up -d --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:8080 |
| Backend API + Swagger | http://localhost:8000/docs |
| AI Services health | http://localhost:8001/health |
| MinIO Console | http://localhost:9001 |
| Phoenix tracing (tùy chọn) | http://localhost:6006 |

Verify LiveKit:

```bash
./scripts/verify-livekit.sh
```

### Dừng stack

```bash
docker compose down        # giữ data
docker compose down -v     # xóa volume PostgreSQL + MinIO
```

### Dev frontend hot-reload (tùy chọn)

```bash
cd frontend && npm install && npm run dev
# Mở http://localhost:3000
# Đặt FRONTEND_URL=http://localhost:3000 trong .env
```

---

## Cấu trúc repo

```text
interview/
├── frontend/                 # Next.js — HR dashboard + interview room + candidate profile
│   ├── app/                  # App Router (/, /interview/[id], /candidate/[id])
│   └── src/
│       ├── legacy-pages/     # InterviewRoom, Result, CandidateProfile, ...
│       ├── components/       # CodePanel, SandpackPanel, CognitivePanel, ...
│       ├── hooks/            # useLiveKit, useProctoring, useCameraRecorder
│       └── utils/            # auth.js, interviews.js
│
├── backend/                  # FastAPI — auth, interviews, LiveKit, report worker
│   └── app/
│       ├── api/v1/           # REST routers
│       ├── models/           # SQLAlchemy models
│       └── services/         # planning, assignment, inspector, code_runner, recording, ...
│
├── ai-services/              # AI agents + MCP toolbox
│   └── app/
│       ├── agents/           # planning, assignment, interview, inspector, coding_assistant
│       ├── mcp/              # interview_tools, assignment_tools
│       └── docs/             # Agent design docs
│
├── configs/                  # YAML defaults (ports, buckets, agent endpoints)
│   ├── backend-services.yml
│   ├── frontend-services.yml
│   ├── ai-services.yml
│   ├── livekit.yaml
│   └── nginx/                # aurelia.io.vn reverse proxy
│
├── scripts/
│   ├── verify-livekit.sh
│   └── aws/                  # setup-ec2, deploy, setup-domain
│
├── docker-compose.yml
├── docker-compose.aws.yml
└── .env.example
```

---

## Cấu hình

File cấu hình chính: **`.env`** ở repo root (copy từ `.env.example`).

| Biến | Mô tả |
| --- | --- |
| `GEMINI_API_KEY` | Google AI — CV extraction + tất cả LLM agents |
| `JWT_SECRET` | Ký JWT cho HR auth |
| `FRONTEND_URL` | URL công khai cho meeting link (`http://localhost:8080` hoặc `https://aurelia.io.vn`) |
| `LIVEKIT_*` | WebSocket URL, API key/secret cho voice rooms |
| `INTERNAL_SERVICE_KEY` | MCP → backend service auth; để trống = dev mode |
| `MINIO_*` | Object storage cho CV, recording, report PDF |

Defaults không secret nằm trong `configs/*.yml` — được `backend/app/config.py` và `ai-services/app/config.py` load, override bởi env.

**Production checklist**
- [ ] `JWT_SECRET` — chuỗi random dài
- [ ] `INTERNAL_SERVICE_KEY` — bật service auth
- [ ] `FRONTEND_URL` + `LIVEKIT_PUBLIC_URL` — domain HTTPS/WSS
- [ ] `GEMINI_API_KEY` — quota đủ cho production
- [ ] Nginx + Certbot (`configs/nginx/aurelia.io.vn.conf`)
- [ ] Không commit `.env`, `*.pem`, credentials

---

## Luồng nghiệp vụ

### 1. HR tạo interview

```text
HR upload CV + JD
    → Backend extract CV (Gemini)
    → Planning Agent  → interview_brief, evaluation_brief, assignment_brief
    → Assignment Agent → Assignment JSON (DSA / project / cognitive)
    → Lưu Postgres + CV lên MinIO
    → Trả meeting link: {FRONTEND_URL}/interview/{id}
```

### 2. Candidate phỏng vấn

```text
Mở link → đọc quy định → bật camera/mic
    → GET /join-token → LiveKit room
    → Interview Worker (Gemini Live) join room
    → Voice Q&A + proctoring events
    → Agent switch_mode('code') → Monaco / Sandpack / MCQ
    → sync-code · run-code · submit-assignment
    → Kết thúc → upload recording → POST /end
```

### 3. Chấm điểm & report

```text
POST /end → status = evaluating
    → Report worker (background thread)
    → Inspector Agent → scorecard + PDF
    → Lưu report JSON + PDF path vào Postgres/MinIO
    → status = completed
    → HR nhận SSE report_ready · xem /candidate/{id}
```

---

## API & tài liệu agent

### Backend (`/api/v1`)

| Nhóm | Endpoint chính |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `GET /auth/me` |
| HR | `GET /interviews`, `POST /interviews/generate-link`, `GET /interviews/slots` |
| Candidate (public) | `GET /interviews/{id}`, `GET /join-token`, `POST /proctor-event`, `POST /end` |
| Assignment | `POST /sync-code`, `/run-code`, `/submit-assignment`, `/code-assist` |
| Recording | `POST /recording/chunk`, `POST /recording`, `GET /recording` (HR auth) |
| Report | `GET /dossier`, `GET /report`, `GET /report.pdf`, `GET /events` (SSE) |

Swagger đầy đủ: http://localhost:8000/docs

### AI Services (`/api/v1`)

| Agent | Endpoint |
| --- | --- |
| Planning | `POST /planning/plan` (+ SSE stream) |
| Assignment | `POST /assignment/generate` (+ SSE stream) |
| Inspector | `POST /inspector/evaluate` |
| Coding Assistant | `POST /coding-assistant/chat` |

### Tài liệu chi tiết agent

| Tài liệu | Nội dung |
| --- | --- |
| [Planning Agent](ai-services/docs/PLANNING_AGENT.md) | Pipeline CV+JD → 3 briefs |
| [Assignment Agent](ai-services/docs/ASSIGNMENT_AGENT.md) | DSA / project / cognitive |
| [MCP Toolbox](ai-services/docs/MCP_TOOLBOX.md) | 14 interview tools + 3 assignment tools |
| [Frontend README](frontend/README.md) | Routes, hooks, proctoring |
| [Backend README](backend/README.md) | Auth, Docker, SQLite dev |
| [Interview Tab](frontend/INTERVIEW_TAB.md) | Luồng form tạo interview |

---

## Phát triển local

### Backend only (SQLite, không Docker)

```bash
cd backend
cp .env.example .env
# DATABASE_URL=sqlite:///./data/aurelia.db

python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### AI Services

```bash
cd ai-services
python -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8001
```

### Interview Worker (voice agent)

```bash
# Cần LiveKit + Backend + AI Services đang chạy
docker compose up -d interview-worker

# Hoặc local:
cd ai-services && PYTHONPATH=. python -m app.worker dev
```

### Observability (Phoenix)

```bash
docker compose --profile observability up -d phoenix
# UI: http://localhost:6006
```

---

## Test

```bash
# Backend (25 tests)
cd backend && .venv/bin/python -m pytest tests/ -q

# AI Services (trong Docker container)
docker exec aurelia-ai-services python -m pytest tests/ -q
```

---

## Deploy production

### AWS EC2

```bash
cp .env.aws.example .env
# Chỉnh secret, GEMINI_API_KEY, domain

./scripts/aws/setup-ec2.sh    # lần đầu
./scripts/aws/deploy.sh       # build + up
./scripts/aws/setup-domain.sh # DNS + nginx + certbot (aurelia.io.vn)
```

Compose production: `docker-compose.yml` + `docker-compose.aws.yml`

### Nginx reverse proxy

Cấu hình mẫu: `configs/nginx/aurelia.io.vn.conf`

```text
aurelia.io.vn        → frontend :8080
livekit.aurelia.io.vn → LiveKit :7880 (WSS)
```

---

## Troubleshooting

| Triệu chứng | Gợi ý |
| --- | --- |
| Swagger / API `NetworkError` trên Linux Docker | Stack dùng `network_mode: host` — kiểm tra port 8000/8080 không bị chiếm |
| Planning trả mock plan | AI Services chưa chạy hoặc `GEMINI_API_KEY` trống |
| Candidate không nghe được AI | Kiểm tra LiveKit: `./scripts/verify-livekit.sh`, `LIVEKIT_PUBLIC_URL` đúng WSS |
| CV PDF không extract | Cần `GEMINI_API_KEY`; không có key → placeholder text |
| Recording không hiện trên profile | Cần upload thành công + HR đăng nhập (video dùng `?token=` JWT) |
| Report stuck ở `evaluating` | Xem log `aurelia-backend`, Inspector agent :8001, `GEMINI_API_KEY` |
| `docker compose` chậm pull Phoenix | Dùng profile: `docker compose up -d` (không bật observability) |

Logs:

```bash
docker logs -f aurelia-backend
docker logs -f aurelia-ai-services
docker logs -f aurelia-interview-worker
docker logs -f aurelia-frontend
```

---

## License

Internal HR tool — © 2026 InterviewAI Aurelia.