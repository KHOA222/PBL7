# API Design

## Auth
- POST `/api/auth/register`
- POST `/api/auth/login`
- GET `/api/auth/me`

## Videos
- GET `/api/videos`
- POST `/api/videos/upload`
- POST `/api/videos/{video_id}/caption`
- GET `/api/videos/{video_id}`
- GET `/api/videos/file/{filename}`

## Comments
- GET `/api/comments/video/{video_id}`
- POST `/api/comments/video/{video_id}`

## Video2Text
- POST `http://127.0.0.1:8001/video-to-text`
