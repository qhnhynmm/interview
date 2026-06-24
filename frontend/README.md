# Aurelia Frontend

`frontend/` là giao diện web cho nền tảng Aurelia. Cùng một app phục vụ hai nhóm màn hình: workspace của HR để tạo và theo dõi phỏng vấn, và phòng phỏng vấn trực tiếp cho ứng viên khi mở meeting link.

Frontend được viết bằng React + Vite, gọi backend qua `/api`, kết nối LiveKit cho audio/video realtime, ghi hình phiên phỏng vấn, chạy proctoring trong trình duyệt và hiển thị bài coding/cognitive assignment.

## Use Case

- HR đăng ký, đăng nhập, tạo interview từ CV, JD, vị trí, ngôn ngữ và slot hẹn.
- HR xem danh sách buổi phỏng vấn, trạng thái, điểm số, report và hồ sơ ứng viên.
- Candidate mở `/interview/:id`, đọc quy định, bật camera/mic và vào LiveKit room.
- Interview Agent gửi data message để chuyển UI giữa chế độ phỏng vấn và chế độ bài tập.
- Candidate làm bài DSA bằng Monaco, project task bằng Sandpack hoặc cognitive test dạng lựa chọn.
- Candidate có thể dùng AI coding assistant nếu agent/backend bật quyền.
- Browser báo proctoring events như tab switch, màn hình phụ, gaze-away, nhiều khuôn mặt hoặc điện thoại.
- Khi kết thúc, frontend upload recording và nghe SSE để cập nhật khi report sẵn sàng.

## Tech Stack

| Nhóm | Công nghệ |
| --- | --- |
| UI | React 19, React DOM, CSS thuần trong `index.css` và `App.css` |
| Build/dev | Vite 8, `@vitejs/plugin-react`, ESLint |
| Realtime | `livekit-client` |
| Coding UI | Monaco Editor, CodeSandbox Sandpack |
| Markdown | `react-markdown`, `remark-gfm` |
| Proctoring | MediaPipe Tasks Vision, FaceLandmarker, ObjectDetector |
| Auth client | JWT Bearer token lưu trong `localStorage` |

## Kiến Trúc Frontend

```text
src/main.jsx
  |
  +-- /interview/:id  -> pages/InterviewRoom.jsx
  +-- /candidate/:id  -> pages/CandidateProfile.jsx
  +-- route khác      -> App.jsx

App.jsx
  |
  +-- Home.jsx        -> giới thiệu platform
  +-- Interview.jsx   -> form tạo interview
  +-- Result.jsx      -> bảng kết quả/report
  +-- Login/Register  -> auth flow HR

InterviewRoom.jsx
  |
  +-- useLiveKit           -> join room, nhận data message
  +-- useCameraRecorder    -> ghi hình và upload chunk/final blob
  +-- useProctoring        -> phát hiện tín hiệu gian lận
  +-- AssignmentPanel      -> CodePanel | SandpackPanel | CognitivePanel
```

Không dùng router library; `src/main.jsx` tự quyết định màn hình dựa trên `window.location.pathname`.

## Route Chính

| Route | Màn hình | Mục đích |
| --- | --- | --- |
| `/` | `App.jsx` | Workspace HR với các tab Home, Interview, Result |
| `/interview/:id` | `InterviewRoom.jsx` | Phòng phỏng vấn của ứng viên |
| `/candidate/:id` | `CandidateProfile.jsx` | Hồ sơ ứng viên cho HR |

Các tab `Interview` và `Result` yêu cầu HR đã đăng nhập. Token được tạo bởi backend qua `/api/v1/auth/login` hoặc `/api/v1/auth/register`.

## API Client

Các lời gọi backend nằm chủ yếu trong:

- `src/utils/auth.js`: login, register, fetch current user, logout.
- `src/utils/interviews.js`: tạo interview, lấy slots, join room data, report proctoring, upload recording, tải PDF, SSE events, coding assistant.

Trong development, Vite proxy mọi request `/api/*` tới backend theo `configs/frontend-services.yml`.

## Cấu Hình

Frontend không cần `.env` riêng khi chạy local. Cấu hình không secret nằm trong `../configs/frontend-services.yml`:

```yaml
frontend:
  dev_port: 5173
  backend_url: "http://localhost:8000"

proctoring:
  enable_gaze: true
  enable_multi_face: true
  enable_phone: true
```

`vite.config.js` đọc file YAML này khi khởi động, cấu hình dev port/proxy và expose `__PROCTORING__` để hook `useProctoring` dùng.

## Chạy Local

```bash
cd frontend
npm install
npm run dev
```

Mở <http://localhost:5173>.

Các script khác:

```bash
npm run build
npm run preview
npm run lint
```

## Chạy Bằng Docker Compose

Từ repo root:

```bash
docker compose up -d --build frontend
```

Container frontend build app bằng Vite rồi phục vụ qua Nginx. Nginx proxy `/api` tới service `backend` trong Docker network.

## Cấu Trúc Thư Mục

```text
frontend/
├── index.html
├── vite.config.js
├── nginx.conf.template
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Interview.jsx
│   │   ├── InterviewRoom.jsx
│   │   ├── Result.jsx
│   │   ├── CandidateProfile.jsx
│   │   ├── LoginPage.jsx
│   │   └── RegisterPage.jsx
│   ├── components/
│   │   ├── AssignmentPanel.jsx
│   │   ├── CodePanel.jsx
│   │   ├── SandpackPanel.jsx
│   │   ├── CognitivePanel.jsx
│   │   └── CodeAssistant.jsx
│   ├── hooks/
│   │   ├── useLiveKit.js
│   │   ├── useCameraRecorder.js
│   │   └── useProctoring.js
│   ├── utils/
│   │   ├── auth.js
│   │   └── interviews.js
│   ├── constants/
│   └── data/
└── public/
```

## Ghi Chú Phát Triển

- Giữ API calls đi qua `src/utils/*` để tránh phân tán logic auth/proxy.
- `InterviewRoom.jsx` là màn hình realtime có nhiều trạng thái bất đồng bộ; khi sửa cần kiểm tra join room, data message, recording finalize và assignment restore.
- Proctoring là fire-and-forget; lỗi gửi event không được làm gián đoạn buổi phỏng vấn.
