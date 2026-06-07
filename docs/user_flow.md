# User Flow

1. User đăng ký/đăng nhập.
2. User upload video.
3. Backend lưu file vào `uploads/` và lưu metadata vào DB.
4. User xem video trên Home Feed.
5. User bấm sinh mô tả video.
6. Backend gọi Video2Text service.
7. Caption được lưu vào DB và hiển thị lại trên feed.
