# Changelog

## Phase 4 — v1.0.0 / Test Contract v1.3

- Thêm benchmark Chromium 1280×720, soak headless cùng tiến trình và xuất bảng xếp hạng. Giữ luật mô phỏng và JSONL của v1.2.
- Thêm đổi phím, phụ đề cảnh báo, giảm chuyển động, chữ lớn và bảng xếp hạng local lưu SQLite.
- Thêm chế độ Chọn bản đồ để luyện tập riêng từng Đêm, tách khỏi điểm chiến dịch.
- Đóng gói bản Python chạy độc lập, thêm số đo, ảnh, demo, retro và giấy phép.


## Phase 3 — Test Contract v1.2

### Thay đổi phá vỡ tương thích

- Thời lượng ba Đêm là 240/270/300 giây. Thắp đủ đèn không kết thúc Đêm. Chỉ thắng tại bình minh nếu còn lửa và giữ đủ 3/5, 4/6 hoặc 5/7 đèn sáng.
- Điểm nạp giảm còn 5 mỗi đom đóm. Châm dầu được tính điểm, thắp lại thưởng 40, Tỏa Sáng trúng Bóng Mực đang hút cho tổng 15. Thưởng thời gian bị bỏ, thay bằng thưởng đèn, dầu và lửa còn lại khi thắng.
- Đèn đã sáng hao dầu, có thể được châm, tắt và thắp lại. Đèn dưới 30 dầu mất vùng an toàn. Bóng Mực có trạng thái `drain` và về `wander` khi hết choáng.
- Sức chứa tăng theo số lần thắp và thắp lại thành công. `tuning.carry_capacity` là sức chứa ban đầu.
- Snapshot thêm `fuel`, `ever_lit`, `relit_count` ở đèn và `capacity` ở người chơi. Scenario thêm các tùy chọn `lit`, `fuel`, `ever_lit`, `successful_lights` và `target_lantern_id`. Kịch bản cũ đặt `lit: true` mà không đặt dầu sẽ bắt đầu với 100 dầu.
- Sự kiện mới `refuel`, `lantern_out`, `fuel_drain`. `lantern_lit` thêm cờ `relight`. Sự kiện kết thúc chuẩn hóa thành `game_over` với `state`, `score` và `reason`. Lý do `all_lanterns`/thắng sớm được thay bằng `dawn_survived`. Định dạng dòng `end` giữ nguyên.

### Giao diện

- Thanh dầu trên đèn sáng, nhấp nháy 1 Hz khi yếu. Đèn tắt xẹp 20% phần giấy và có vết rách.
- HUD ghi số đèn cần lúc bình minh và sức chứa động. Cài đặt bảng màu dễ phân biệt được lưu giữa các lần mở.

## Phase 2 — Test Contract v1.1

- Mở rộng từ Đêm 1 sang chiến dịch ba Đêm. Chuẩn hóa thông số, bảng màu, bản đồ và điểm.
- Thêm Lướt, Gió Lạc, Bùa Gió, cầu, bục nhảy, gió mạnh, pause, HUD, âm thanh và cài đặt.

## Phase 1 — Test Contract v1.0

- Game 3D Đảo Bến, nhặt đom đóm, thắp 5 đèn, Tỏa Sáng, thắng/thua và chơi lại.
- Headless 60 tick/giây, scenario/input JSON có thể phát lại và đầu ra JSONL.
