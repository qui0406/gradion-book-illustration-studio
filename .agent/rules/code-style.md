# Code Style Guidelines

- Backend (FastAPI):
  - Sử dụng Python type hints chuẩn xác và Pydantic schemas cho tất cả dữ liệu vào/ra.
  - Cấu trúc module rõ ràng: `app/routes/`, `app/services/`, `app/models/`.
  - Phân tách rõ ràng giữa HTTP Controller (routes) và Business Logic (services).

- Frontend (React + Vite):
  - Viết Functional Components gọn gàng, sử dụng React Hooks.
  - Cấu trúc thư mục theo tính năng: `pages/`, `components/`, `hooks/`, `api/`.
  - Quản lý API calls thông qua Axios instance tập trung tại `api/client.js`.
