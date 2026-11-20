# ADR — Nhiên liệu đèn và xét thắng tại bình minh

**Trạng thái:** Áp dụng ở Phase 3, Contract v1.2.

Mỗi đèn giữ trạng thái sáng/tắt, số đom đóm đã nạp, lịch sử từng sáng và số lần thắp lại. Dầu là số nguyên tính theo đơn vị 1/60. Một tick giảm một đơn vị nguyên do hao tự nhiên, cộng năm cho mỗi Bóng Mực đang hút. Chỉ đổi sang số thập phân một chữ số ở snapshot và sự kiện. Vùng an toàn, phép châm dầu và thưởng bình minh dùng số nguyên chưa làm tròn. Tick cạn dầu đặt đèn về tắt và xóa phần nạp. Đèn đã tắt nhớ lịch sử để lần sau chỉ cần 5 đom đóm.

Theo thứ tự Ticket-02, dầu hao và đèn cạn tắt ở bước 2, trước lần bấm tương tác. Vì vậy đèn đầy ở đầu tick có thể nhận dầu sau khi đã hao ở bước 2. Một đèn còn đầy tại lúc xét tương tác bị lọc khỏi danh sách chọn. Đèn phục hồi vùng an toàn ngay sau tương tác. Bóng Mực giữ trạng thái trước khi Tỏa Sáng kiểm tra điểm. Sau đó bước di chuyển xử lý việc bỏ hút nếu mục tiêu không còn yếu, và đẩy Bóng Mực khỏi vùng an toàn nếu cần.

Khi bước di chuyển kết thúc ở trạng thái hút, lần trừ dầu đầu tiên của lần hút đó diễn ra ở bước 2 của tick kế tiếp. Ghi `fuel_drain` sau từng 60 tick hút liên tiếp của mỗi Bóng Mực, với dầu còn lại sau tổng hao hụt của đèn trong tick đó. Pause giữ nguyên tất cả các bộ đếm này. Bóng Mực đang đuổi chỉ xét đèn sau khi rời trạng thái đuổi theo cự ly cũ. Bóng đang lang thang ưu tiên đèn yếu, rồi giữ hành vi đuổi và tìm đèn tắt khi không có đèn yếu.

Kết thúc đêm chỉ xảy ra khi hết Ngọn Lửa hoặc khi hết giờ. Kiểm tra Ngọn Lửa trước, sau đó mới kiểm đủ 60% đèn sáng ở cuối tick. Thưởng bình minh lấy số đèn và dầu sau toàn bộ cập nhật của tick cuối. Cả headless và phiên trình duyệt dùng cùng mô phỏng. Tùy chọn màu chỉ lưu ở trình duyệt. API trình duyệt có cờ đèn yếu và đèn có thể nhận để HUD không suy ngược từ dầu đã làm tròn.
