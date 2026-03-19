# custom-tools

Project riêng cho 2 tính năng đã chốt từ app local:

- ✅ **Feature 2: Viết lại nội dung** (Gemini + fallback local)
- ✅ **Feature 3: Lấy nội dung YouTube** (video/playlist + transcript + export)
- ⏳ Feature 1 (VBEE): triển khai sau

Project đã sẵn sàng theo chuẩn GitHub + Docker, có worker queue cho tác vụ YouTube nặng và SQLite để lưu lịch sử.

---

## 1) Tech stack

- Python 3.11
- FastAPI
- yt-dlp
- Redis + RQ (worker queue)
- SQLite (log/history)
- Docker + docker-compose

---

## 2) Kiến trúc chính

- **Backend**: FastAPI (`app/main.py`)
- **Workers**: RQ worker (`app/worker/run_worker.py`) xử lý YouTube jobs
- **Storage**: SQLite (`app/core/db.py`) lưu rewrite runs + youtube jobs
- **Export files**: `.txt / .json / .srt` trong thư mục `EXPORT_DIR`

---

## 3) Chạy bằng Docker

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Redis: nội bộ qua `redis://redis:6379/0`

---

## 4) Biến môi trường

Các biến chính trong `.env` / `.env.example`:

- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `REDIS_URL`
- `SQLITE_PATH`
- `EXPORT_DIR`
- `YOUTUBE_MAX_PLAYLIST_ITEMS`
- `YOUTUBE_JOB_TIMEOUT_SECONDS`

> Nếu chưa có `GEMINI_API_KEY`, feature rewrite vẫn chạy bằng fallback local.

---

## 5) API – Feature 2: Viết lại nội dung

### `POST /api/v1/rewrite`

Body mẫu:

```json
{
  "text": "Nội dung gốc cần viết lại...",
  "style": "engaging",
  "language": "vi",
  "preserve_keywords": ["YouTube", "AI"],
  "variant_count": 3
}
```

`variant_count`: từ 1 đến 3.

Output gồm:

- `variants`: 1–3 phiên bản rewrite
- `comparison`: so sánh word/char count và số keywords giữ được
- tự động lưu lịch sử vào SQLite

---

## 6) API – Feature 3: Lấy nội dung YT

### A. Chạy đồng bộ (trả kết quả ngay)

`POST /api/v1/youtube/extract`

Body mẫu:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "include_transcript": true,
  "language_priority": ["vi", "en"],
  "max_items": 10,
  "export_formats": ["txt", "json", "srt"]
}
```

### B. Chạy qua worker queue (khuyến nghị)

1. `POST /api/v1/youtube/jobs` (enqueue)
2. `GET /api/v1/youtube/jobs/{job_id}` (status/result)
3. `GET /api/v1/youtube/jobs/{job_id}/exports/{fmt}` (download file export)

Hỗ trợ URL video và playlist (giới hạn theo `max_items`).

---

## 7) Rủi ro đã xử lý trong thiết kế

- Video private / age-restricted / no subtitle: job có trạng thái `failed` hoặc trả transcript rỗng
- YouTube thay đổi cấu trúc: cô lập logic tại `youtube_service.py`
- Tác vụ nặng: đưa vào queue worker thay vì block API

---

## 8) Cấu trúc thư mục

```text
app/
├─ api/
│  ├─ router.py
│  └─ v1/
│     ├─ rewrite.py
│     └─ youtube.py
├─ core/
│  ├─ config.py
│  └─ db.py
├─ models/
│  └─ schemas.py
├─ services/
│  ├─ export_service.py
│  ├─ rewrite_service.py
│  └─ youtube_service.py
└─ worker/
   ├─ queue.py
   ├─ jobs.py
   └─ run_worker.py
```

---

## 9) Lưu ý bảo mật

- Không commit API key thật.
- Key cũ từ app local nên được rotate nếu từng lộ.
- Dùng `.env` local hoặc secret store cho production.
