# Constraints

- Lock theo `projectId`: Đảm bảo mỗi dự án chỉ xử lý 1 tác vụ pipeline tại một thời điểm để tránh race conditions.
- Không tin tưởng số lượng Gemini trả về: Backend phải tự kiểm tra, cắt bớt (truncate) hoặc từ chối nếu dữ liệu đầu ra từ Gemini vượt quá số lượng cho phép (tối đa 2 nhân vật, 1 chương).
- Tránh Over-engineering: Ưu tiên thiết kế đơn giản, phẳng, lưu trữ dữ liệu dạng JSON file trực tiếp trên disk thay vì thiết lập CSDL phức tạp.
