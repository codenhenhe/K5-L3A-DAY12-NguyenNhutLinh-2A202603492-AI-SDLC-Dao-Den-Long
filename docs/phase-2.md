# Phase 2 — Ticket-02 và Test Contract v1.1

## Checklist

1. Đối chiếu bảng tuning Phần 1 và bảng màu Phần 3.8. **Đã đồng bộ hai bảng chuẩn.**
2. Dựng ba bản đồ, mô phỏng 60 tick/giây, cơ chế Lướt, rơi, Gió Lạc, Bùa Gió và gió mạnh. **Đã làm và chạy test.**
3. Mở rộng manifest, CLI, scenario, input, snapshot và sự kiện v1.1. **Đã làm và chạy test.**
4. Thêm luồng ba Đêm, HUD, âm thanh, pause và cài đặt. **Đã làm và kiểm tra menu, HUD, pause, chuỗi kết quả và lưu âm lượng trong Chromium.**
5. Chạy test hồi quy, đo hiệu năng và lưu bằng chứng. **Đã chạy headless và phát lại v1.0 ở tag Phase 1.**
6. Commit và push tag `phase-2` do người dùng thực hiện.

## Acceptance criteria

| Mục | Tiêu chí nghiệm thu | Kiểm tra và kết quả |
|---|---|---|
| Bản đồ và đèn | Đêm 1 có đảo 40 m và 5 đèn, Đêm 2 có hai đảo/cầu/bục nhảy và 6 đèn, Đêm 3 có 3 tầng/dốc/bục/tháp và 7 đèn tại tọa độ ticket | Test 3 layout, đi xuyên cầu, phóng/đáp đảo đích, dốc, vách, lên tầng 2 và chắn tháp |
| Thứ tự tick, tính điểm và Lướt | Pause xử lý trước đồng hồ. Nhặt trước nạp, nạp trước pulse, cướp trước hit, spawn cuối bước. Đúng công thức điểm Ticket-02. Cạnh nhấn Lướt tôn trọng thời lượng và hồi chiêu | Test sự kiện theo thứ tự, điểm nạp và thắng từng Đêm, Lướt giữ đúng số tick |
| Số liệu chuẩn | Nhặt 1 m XZ và 1,5 m theo Y. Khởi đầu 20 đom đóm và sinh ở bội của 240 tick. Tỏa Sáng dùng tâm ở Y + 0,8 m, đẩy 4 m trong 15 tick và choáng 120 tick. Hit rơi một nửa, recoil 60 tick, bất tử 90 tick. Rơi dưới Y = −10 và chờ 60 tick trước khi hồi sinh. | Test các mốc, phạm vi 3D, giới hạn sinh, vòng rơi đom đóm, vùng an toàn và ưu tiên kết thúc |
| Gió Lạc | Chỉ sinh tự động ở Đêm 2–3, lần đầu ở sim_tick 1200. Có thể cướp tối đa 3 và chỉ cướp một lần. Tỏa Sáng đuổi con đang chase hoặc thu lại số đom đóm bị cướp. Bất tử của Mây và đèn không chặn cướp | Test lịch 1200/2400, cướp trước hit, Tỏa Sáng trên hai trạng thái và chạm trong vùng an toàn |
| Bùa Gió | Nhặt như đom đóm, kéo dài 600 tick, tăng tốc lên 7,2 m/s, Lướt không hồi chiêu nhưng nhấn trong lần Lướt bị bỏ qua, xuất hiện lại sau 2700 tick | Test tốc độ, cạnh nhấn, khóa khi đang Lướt và hồi bùa |
| Chuỗi ba Đêm | Menu → lời Ông Đăng → chơi → kết quả. Thắng tiếp Đêm, thua thử lại, thắng Đêm 3 hiện Bình Minh và tổng điểm ba Đêm thắng | Đã kiểm tra trên Chromium bằng kịch bản đặt Mây cạnh đèn cuối, mang 10 đom đóm, các đèn khác đã sáng. Bấm E từng Đêm, chọn Đêm kế tiếp, màn Bình Minh hiện 3024 điểm. Test headless xác nhận điểm từng Đêm. Chưa chơi ba Đêm từ bản đồ mặc định tới thắng bằng tay |
| Tạm dừng | Esc hoặc P giữ nguyên sim_tick, đồng hồ, trạng thái, cooldown và lịch sinh. Menu có Tiếp tục, Chơi lại Đêm, Cài đặt, Về menu | Test headless giữ nguyên bộ đếm và mở đúng bốn nút trong Chromium |
| Cài đặt | Âm lượng đổi gain âm thanh. Độ nhạy đổi góc quay khi kéo chuột. Cả hai lưu và nạp lại qua localStorage | Đã kiểm tra âm lượng trong Chromium: đổi 0,45 thành 0,50, tải lại trang vẫn là 0,50, sau đó trả về 0,45. Kiểm tra độ nhạy qua mã xử lý kéo chuột |
| Âm thanh | Nhạc nền, âm nhặt/thắp/pulse/hit/nhảy/Lướt/thắng/thua/spawn và 10 giây cuối. Báo gió bằng âm thanh và lá bay trước 2 giây | Bộ âm Web Audio gắn với sự kiện. Test headless đo gió 2 m/s ở tick 1800 và tắt được gió bằng scenario. Chưa nghe thử từng hiệu ứng |
| HUD | Lửa trái, đồng hồ giữa báo đỏ ≤ 30 s, đèn và điểm phải, 10 ô đom đóm, cooldown Lướt/pulse, nhắc E và mũi tên chỉ đèn ngoài màn hình | HUD, ô đom đóm, đồng hồ và cooldown quan sát được trong Chromium. Chưa kiểm tra bằng trình duyệt từng trạng thái HUD |
| Bảng màu | Mỗi kênh nằm trong sai số 10% so với bảng chuẩn. Mức sáng môi trường bằng `0.15 + 0.55 × đèn sáng / tổng đèn` | Đã áp dụng bảng màu chuẩn và công thức sáng theo tiến độ. Chromium xác nhận màu điểm số RGB (242, 193, 78), tức `#F2C14E` |
| Contract v1.1 | `--night 1/2/3`, JSONL có đủ trường v1.1, tách tick/sim_tick, trạng thái Bóng Mực theo ticket, cùng đầu vào cho cùng JSONL | 33 test local đạt. Hai lần chạy scenario cơ chế khớp từng byte |
| Hiệu năng | Headless ≤ 30 giây cho mỗi Đêm, bản trình duyệt trung bình ≥ 30 FPS ở 1280×720 | Linux x86_64, Python 3.14.4, seed 42. Đêm 1: 18.000 tick / 0,370 s. Đêm 2: 19.800 tick / 0,640 s. Đêm 3: 21.600 tick / 0,743 s. Chromium đo 177,9 FPS trong 5 giây Đêm 1 mặc định ở 1280×720 |

Chạy `sh scripts/verify-phase-2.sh` để tái lập các kết quả headless. [Đầu vào scenario](proof/phase-2/mechanics.scenario.json), [điều khiển](proof/phase-2/mechanics.inputs.json) và [JSONL gốc](proof/phase-2/mechanics.jsonl) tái hiện nhặt bùa, cướp, hit, trả lại đom đóm, pause, tiếp tục và Lướt. Để xem FPS, chạy game local rồi nối `?benchmark=1` vào địa chỉ trình duyệt. Chỉ số xuất hiện sau 5 giây chơi.

## Cách xử lý các chi tiết còn mở

- Bóng Mực có 30 tick hiện hình. Đợt đầu ở sim_tick 300 có hai con, các đợt sau mỗi 8/7/6 giây theo Đêm. Dùng cự ly 12/18 m để bắt đầu và bỏ đuổi.
- Tương tác đèn đo bán kính 3D từ chân Mây đến chân đèn để không nạp xuyên tầng. Nhặt, nhận hit và vùng an toàn dùng khoảng cách XZ cùng điều kiện chênh cao được nêu trong bảng, nếu có.
- Trần 30 được kiểm tra lúc sinh đom đóm từ điểm chuẩn. Đom đóm đã bị đánh rơi vẫn xuất hiện đủ số lượng và được tính vào trần của lượt sinh tự nhiên tiếp theo. Khi có đom đóm rơi trên đất, tọa độ Y lấy từ mặt địa hình.
- Tên Đêm 2 và 3, lời Ông Đăng, vị trí xuất phát Đêm 3 ngoài chân vách và cách thể hiện hình ảnh/âm thanh là lựa chọn của dự án.
- Snapshot tick 0 được ghi trước sự kiện `night_start` cùng tick. Tick tiếp tục khôi phục mô phỏng sau khi ghi `resumed`. Đom đóm thường có `ttl_s: null`. Gió Lạc đã biến mất được loại khỏi mảng.

## Hồi quy và nhật ký AI

Chạy `sh scripts/verify-phase-1.sh` để lấy bản v1.0 chính xác từ tag local `phase-1` và phát lại bằng chứng cũ. 15 test gốc đạt. Ở v1.1, chỉnh các test cũ cho luật mới đã được nêu trong Ticket-02: tính điểm khi nạp thay cho lúc nhặt, Bóng Mực xuất hiện theo lịch, rơi ở mép đảo, thêm sự kiện mở Đêm và giảm sức chứa. Những test còn lại kiểm tra lại điều khiển, tick, nhảy, kịch bản, vùng an toàn, Tỏa Sáng và tính tất định. Bộ test ẩn của giảng viên chưa được chạy.

Codex triển khai từ Ticket-02, dùng lại renderer và chung mô phỏng thay vì duy trì hai bản luật. Bộ test đầu tiên phát hiện năm kỳ vọng v1.0 đã hết hiệu lực. Ví dụ, test cũ đòi Bóng Mực có ở tick 0 trong khi đề v1.1 cho sinh ở tick 300. Giữ nguyên bài kiểm tra v1.0 trong tag và chỉnh kỳ vọng v1.1 theo từng thay đổi cụ thể. Ước tính 20.000–35.000 token gồm ngữ cảnh và mã, không có đo chi phí.

Sau khi nhận hai bảng chuẩn, chạy lại các ca biên. Test rơi phát hiện sai số tích lũy tại Y = −10 có thể làm mất lửa sớm đúng một tick. Thêm so sánh có dung sai và test kiểm tra cả ngưỡng rơi lẫn mốc hồi sinh.
