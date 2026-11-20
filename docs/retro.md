# Retro — Đảo Đèn Lồng

## Kết quả qua bốn phase

| Phase | Kết quả | Bài học |
|---|---|---|
| 1 | Một màn 3D và headless v1.0. 15 test gốc đạt, replay thắng và thua đúng byte. | Tách mô phỏng khỏi giao diện ngay đầu giúp dùng cùng luật trong game và bài chấm. |
| 2 | Ba Đêm, bản đồ chuẩn và Contract v1.1. 33 test gốc đạt. | Một ticket bổ sung dữ liệu có thể thiếu bảng. Ghi giả định tạm, đợi bảng chuẩn rồi khóa bằng test. |
| 3 | Dầu đèn, bình minh và v1.2. 47 test ở tag Phase 3 đạt. | Trạng thái phải được cập nhật đúng thứ tự. Dầu dạng nguyên 1/60 tránh tranh chấp ở mốc 30 và tick cạn. |
| 4 | Benchmark, soak, bảng xếp hạng, cài đặt tiếp cận và gói v1.0.0. 52 test ở mã v1.3 đạt. | Đo renderer thật và tách các phép đo khỏi gameplay. Gói chạy cần được kiểm tra cùng mã nguồn. |

Tôi thấy AI hiệu quả nhất khi có một kịch bản nhỏ và kết quả dự kiến rõ. Từ Phase 1, bản test nạp đèn hai lần từng thất bại vì AI đặt đom đóm ngoài tầm nhặt. Chạy bản giả lập theo từng tick cho thấy vị trí đom đóm là nguyên nhân. Trong Phase 2, bước tích phân làm Y tại mép rơi thấp hơn −10 rất ít do sai số. Test sát biên phát hiện việc mất Ngọn Lửa sớm một tick. Trong Phase 3, bản kiểm chứng đầu tiên giả định sự kiện kết thúc luôn là dòng áp chót. Replay có thêm snapshot đúng chu kỳ sau sự kiện, nên phải tìm sự kiện theo tên. Phase 4, lần mở Chromium đầu tiên thoát trước khi trả số. Lưu lỗi của browser vào thư mục benchmark tạm giúp phân biệt lỗi khởi động với số đo thực.

Điểm yếu là bộ test tự viết dễ lặp lại giả định của mã. So sánh replay và kiểm tra độc lập theo điều kiện sát biên hữu ích hơn chỉ chạy lại các test cũ. Chúng tôi chưa có bộ test ẩn hoặc máy chấm chính thức, nên số liệu local chỉ cho thấy hành vi trên cấu hình thử.

`AGENTS.md` giúp nhiều nhất vì giữ lệnh và quy tắc chung ở đúng chỗ. Ba tag gốc làm mốc để chạy lại test và so JSONL nguyên bản mà không đổi checkout. Các script Phase 4 kết hợp hồi quy, soak và chạy thử gói v1.0.0. Kiểm tra giao diện bằng trình duyệt thật bổ sung phần JSONL không thể xác nhận, chẳng hạn trùng phím và lưu cài đặt.

Ước lượng tổng khoảng 80.000–140.000 token, gồm ngữ cảnh, mã và phản hồi. Không có dữ liệu chi phí thực tế. Tiết kiệm bằng mô phỏng chung, thư viện chuẩn, renderer hiện có, ca kiểm thử tối thiểu và chỉ dùng trình duyệt cho hành vi nhìn thấy được. Nếu làm lại, tôi sẽ dựng fixture UI sớm hơn, kiểm tra ngay trình duyệt phục vụ benchmark ở Phase 2, giữ artifact gốc theo từng tag và dùng các tiêu chí nghiệm thu để chốt test trước khi viết logic.
