# custom-tools

Project mới tách riêng từ app cũ, ưu tiên **tính năng 2 và 3**:

- ✅ Feature 2: **Viết lại nội dung** (`/api/v1/rewrite`)
- ✅ Feature 3: **Lấy nội dung YouTube** (`/api/v1/youtube/extract`)
- ⏳ Feature 1 (VBEE): để triển khai sau

Project được tổ chức theo chuẩn có thể đưa lên GitHub và chạy Docker.

---

## 1) Tech stack

- Python 3.11
- FastAPI
- yt-dlp
- Docker + docker-compose

---

## 2) Cấu trúc thư mục

```text
custom-tools/
├─ app/
│  ├─ api/
│  │  ├─ router.py
│  │  └─ v1/
│  │     ├─ rewrite.py
│  │     └─ youtube.py
│  ├─ core/
│  │  └─ config.py
│  ├─ models/
│  │  └─ schemas.py
│  ├─ services/
│  │  ├─ rewrite_service.py
│  │  └─ youtube_service.py
│  └─ main.py
├─ .github/workflows/ci.yml
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ requirements.txt
└─ README.md
```

---

## 3) Cấu hình môi trường

File `.env` đã được tạo với placeholder. Bạn cần thay:

- `GEMINI_API_KEY` (nếu muốn rewrite bằng Gemini thật)

Nếu chưa có key, API rewrite vẫn chạy ở chế độ fallback local.

---

## 4) Chạy bằng Docker

```bash
docker compose up --build
```

API chạy tại: `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

---

## 5) API usage

### 5.1 Health check

`GET /health`

---

### 5.2 Feature 2 - Viết lại nội dung

`POST /api/v1/rewrite`

Body mẫu:

```json
{
  "text": "Nội dung gốc cần viết lại...",
  "style": "engaging",
  "language": "vi",
  "preserve_keywords": ["YouTube", "AI"]
}
```

Styles hỗ trợ: `natural`, `concise`, `engaging`, `formal`, `seo`

---

### 5.3 Feature 3 - Lấy nội dung YouTube

`POST /api/v1/youtube/extract`

Body mẫu:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "include_transcript": true,
  "language_priority": ["vi", "en"]
}
```

Kết quả trả về metadata + transcript (nếu có subtitle/caption khả dụng).

---

## 6) Lộ trình tiếp theo

- Thêm Feature 1 (VBEE) thành `/api/v1/vbee/tts`
- Thêm auth (API key/JWT)
- Thêm logging + rate limit + retry policy
- Thêm test tự động cho service layer

---

## 7) Lưu ý bảo mật

- Không commit API key thật vào repo.
- Chỉ dùng `.env` local, và rotate key nếu từng lộ.
