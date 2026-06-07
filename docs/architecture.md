# Architecture MVP

```mermaid
flowchart LR
    FE[Streamlit Frontend] --> BE[FastAPI Backend]
    BE --> DB[(SQLite/PostgreSQL)]
    BE --> FS[(Local uploads/S3 later)]
    BE --> AI[FastAPI Video2Text]
    AI --> BE
```

Giai đoạn đầu chạy local bằng 3 service: frontend, backend, video2text-service.
