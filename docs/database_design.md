# Database Design

- users: id, name, email, password_hash, role, created_at
- videos: id, user_id, title, description, hashtags, video_url, file_path, caption, status, created_at
- comments: id, video_id, user_id, content, created_at
- caption_jobs: id, video_id, status, model_name, result, processing_time, created_at
