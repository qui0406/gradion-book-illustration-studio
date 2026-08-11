# Project Context

Mục tiêu dự án: Technical Assessment - Web app biến nội dung sách thành chân dung nhân vật + minh họa chương, dùng Gemini API, pipeline 5 bước: Style → Characters → Portraits → Chapters → Illustrations.

Ràng buộc cứng:
- Tối đa 2 nhân vật, tối đa 1 chương — validate ở BACKEND
- Chỉ nhân vật người lớn (adult characters)
- Gửi nội dung sách cho Gemini CHỈ 1 LẦN, tái dùng qua chat session/file reference
- KHÔNG auto-retry Gemini call trong loop, chỉ user-triggered retry
- Portraits/illustrations sinh TUẦN TỰ, ghi tiến độ ngay sau mỗi ảnh
- Illustration phải dùng lại ảnh portrait làm input để giữ nhân vật nhất quán
