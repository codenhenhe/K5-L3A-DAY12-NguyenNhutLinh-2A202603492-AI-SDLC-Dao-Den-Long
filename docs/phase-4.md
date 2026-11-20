# Phase 4 — Bình minh: phát hành v1.0.0

1. Giữ luật gameplay của v1.2, thêm lệnh bench và soak cho v1.3.
2. Lưu bảng xếp hạng trên đĩa, hoàn thiện đổi phím, phụ đề, giảm chuyển động và chữ lớn.
3. Lưu kết quả bench, soak, hồi quy và kiểm tra giao diện.
4. Chuẩn bị gói chạy, ảnh minh họa, video demo, README, LICENSE và retro.
5. Đăng tag `phase-4` và GitHub Release `v1.0.0` từ bản local đã kiểm chứng. Bước này do người dùng thực hiện.

| Tiêu chí | Bằng chứng và kết quả |
|---|---|
| Benchmark | Lệnh chính thức seed 42, 3 giây khởi động và 30 giây đo. Canvas 1280×720, Đêm 1 có đúng 200 Bóng Mực wander, 100 đom đóm và 3 đèn đầy. Test xác nhận sinh đúng số lượng, giữ dầu và Bóng Mực vẫn di chuyển. Máy local đo **233,705 FPS trung bình**, **36,583 FPS 1% thấp**, **506 ms tải**, **7.007 khung**, p95 **16,8 ms**. |
| Soak | Seed 7, 10 Đêm trong một tiến trình, không crash. RSS hiện tại từ **17,02 MB lên 17,04 MB**. Cả 10 Đêm kết thúc với `lost` bằng input ngẫu nhiên. |
| Xếp hạng | Test top 10, UTC có múi giờ, thứ tự khi bằng điểm và seed số nguyên. Chromium rút ngắn Đêm để kích hoạt thua, lưu tên thử rồi tải lại thấy mục trong bảng. Fixture dùng thư mục dữ liệu tạm. Server tính tổng các Đêm đã thắng trước khi lưu. |
| Tiếp cận | Chromium báo W trùng phím Đi tới khi gán cho Nhảy, nhận K, giữ K và chế độ giảm chuyển động khi tải lại, chữ lớn 22,5 px, nút khôi phục trả Nhảy về Space. CSS cơ sở đặt 18 px. Phụ đề dựa vào sự kiện spawn, đồng hồ, trạng thái gió và đèn yếu. |
| Hồi quy | 53 test đạt trên v1.3 từ bản clone GitHub sạch. Chạy 15/33/47 test trên tag v1.0/v1.1/v1.2. Replay v1.3 khớp bằng chứng v1.2 từng byte. Bộ test ẩn của giảng viên chưa được chạy. |
| Đóng gói | Tệp Python 3.10+ tải từ Release khớp với bản build từ mã nguồn đã gắn tag. Đã kiểm tra lệnh headless và khởi động Đêm 1 từ gói. |
| Demo | MP4 1280×720 H.264 dài khoảng 28 giây, có menu và đoạn chơi Đêm 1 ghi từ commit `5ca1d18`, kết quả 53 test, replay headless, benchmark đã lưu và soak chạy lại từ bản clone sạch. |

Chromium đã vào Đảo Chuông qua mục Chọn bản đồ, rồi đổi sang Đảo Sương từ menu tạm dừng và hiển thị đúng mục tiêu theo bản đồ. Bộ kiểm chứng có ca luyện tập chơi lại được và không lưu điểm xếp hạng.

Số đo trên Intel Core 5 210H, khoảng 14,6 GiB RAM, Linux x86_64, Chrome 157.0.8103.78. Renderer dùng cờ Chromium để tắt vsync và giới hạn FPS. RSS đỉnh benchmark là `null` theo ngoại lệ web do Chromium tách nhiều tiến trình. Không dùng số đo máy local để khẳng định kết quả trên máy chấm.

Soak dùng bộ tạo số ngẫu nhiên riêng ở từng Đêm với seed `seed + index`, index bắt đầu từ 0. Bảng xếp hạng lưu seed chiến dịch ban đầu, các Đêm sau dùng seed ban đầu cộng số thứ tự Đêm trừ một. SQLite sắp ở UTC và dùng thứ tự chèn nếu cùng thời gian. Cài đặt giao diện lưu ở trình duyệt, tách khỏi mô phỏng và dữ liệu headless.

## Nhật ký AI

Phase 4 ước khoảng **25.000–45.000 token** cho ngữ cảnh, mã và phản hồi. Đây là ước tính dựa trên khối lượng các lượt triển khai, kiểm chứng và hoàn thiện giao diện. Không có số token hoặc chi phí đo trực tiếp. Tái sử dụng renderer Canvas, mô phỏng headless và các bộ kiểm chứng theo tag để giảm phần ngữ cảnh và mã phải tạo lại.

[Log kiểm chứng](proof/phase-4/verification.txt) · [Benchmark](../bench.json) · [Soak](../soak.json) · [Video demo](demo/demo.mp4) · [Retro](retro.md) · [Ghi chú phát hành](release-v1.0.0.md)
