# Phase 3 — Ticket-03 “Đèn cạn dầu”

## Checklist

1. Đổi mô hình trạng thái đèn, tính dầu chính xác từng tick và thêm châm/thắp lại.
2. Thêm Bóng Mực hút dầu, vùng an toàn theo ngưỡng và thay điều kiện thắng, sức chứa, điểm.
3. Đồng bộ dữ liệu Test Contract v1.2, HUD, thanh dầu và bảng màu dễ phân biệt.
4. Cập nhật test bị thay thế, chạy lại phần không đổi và hai tag cũ. Lưu đầu vào và JSONL gốc.
5. Ghi [ADR](adr/phase-3-fuel-and-dawn.md) và [changelog](../CHANGELOG.md). Người dùng tự tạo commit, tag và push.

## Tiêu chí nghiệm thu và bằng chứng

| Mục | Kiểm chứng |
|---|---|
| Hao, hết dầu, châm và thắp lại | Test 100 dầu tắt đúng tick 6000, châm theo ceil trước khi chặn trần 100, loại đèn đầy, cùng tick cạn rồi thắp lại. Trace thắng có sự kiện cạn dầu và thắp lại ở tick 1, châm dầu ở tick 3. |
| Bóng Mực hút và vùng an toàn | Test ưu tiên đèn yếu và thứ tự ID, không đổi mục tiêu khi đuổi, cộng hai nguồn hút, mốc đúng 30, đẩy ra trong 30 tick và không gây hit. Test dừng hút khi đến gần Mây, đèn tắt, đi khỏi đèn hoặc được châm. |
| Bình minh và điểm | Test đủ hoặc thiếu đúng một đèn ở cả ba Đêm, không thắng sớm, đèn tắt hay mất lửa ở tick cuối được xét trước kết quả, điểm dựa trên dầu chưa làm tròn. Trace cùng scenario thắng 533 điểm với input, thua khi đứng yên, đều ở tick 120. |
| Sức chứa và điều kiện nhập | Test thắp/thắp lại tăng sức chứa, đèn đặt sẵn không tăng, chặn ở 20 và nhập scenario sai trả mã 2. |
| Giao diện và bảng màu | Chromium: bật tùy chọn, tải lại và xác minh vẫn bật. Đồng hồ cảnh báo có màu RGB (255, 255, 255) và biểu tượng ⚠. Trong cảnh kiểm tra Đêm 1, HUD hiện mục tiêu 3/5 và túi 3/12. Bấm E, túi còn 0/12 và dầu tăng từ khoảng 26 lên hơn 55. Đèn dùng thanh dầu, nhấp nháy 1 Hz khi yếu và phần giấy xẹp và có vết rách khi tắt. Kết quả bình minh được xác minh bằng CLI, chưa chơi hết một Đêm mặc định bằng tay. |
| Tính tất định và hồi quy | 47 test trên v1.2 đạt. Hai lượt trace thắng giống nhau từng byte. Hai tag gốc chạy lại đạt 15 test ở v1.0 và 33 test ở v1.1, với các JSONL đã lưu khớp từng byte. |

[Bằng chứng headless](proof/phase-3/) gồm scenario, input và hai đầu ra gốc. Chạy `sh scripts/verify-phase-3.sh` để chạy lại. Benchmark CLI tiếp tục kiểm tra toàn bộ 14.400, 16.200 và 18.000 tick của ba Đêm với cùng hạt giống mặc định và nhân vật được bảo vệ khỏi hit để không kết thúc sớm.

## Kiểm tra hồi quy và thay đổi test

- `test_partial_deposit_and_last_lantern_win` trở thành test nạp một phần và tiếp tục chơi sau khi thắp đèn cuối. Giữ kiểm tra mốc nạp và cạnh nhấn.
- `test_each_night_can_finish_and_scores_only_deposited_motes` chuyển sang kết thúc tại bình minh và công thức điểm v1.2. Bổ sung test độc lập cho ngưỡng thắng ở mỗi Đêm.
- Test hết choáng nay kiểm tra một snapshot `wander` trước khi có thể đuổi tiếp.
- Các test lý do thua nay đọc sự kiện `game_over`. Giữ test ưu tiên hết lửa ở tick bình minh, thêm trường hợp bị hit thật và hết dầu đúng tick cuối.
- Hai script cũ xem nguồn nguyên bản ở tag `phase-1` hoặc `phase-2` khi đang chạy ở v1.2. Không thay bằng chứng hay test ở các tag đã nộp. Chưa chạy bộ test ẩn của giảng viên.

## Nhật ký AI

Codex sửa theo Ticket-03, giữ một mô phỏng chung cho bản chơi và headless. Dùng test hiện có để phát hiện kỳ vọng v1.1 đã bị thay và ghi lý do trước khi cập nhật. Tách test biên cho thứ tự cạn dầu, hút, Tỏa Sáng và bình minh. Dùng renderer và âm thanh có sẵn. Ước lượng 20.000–35.000 token gồm ngữ cảnh và mã. Không có thống kê chi phí.
