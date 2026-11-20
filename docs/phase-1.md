# Phase 1 — PRD-0 và Test Contract v1.0

## Checklist

- [x] Đọc PRD-0 và Test Contract, chốt giả định và tiêu chí kiểm chứng.
- [x] Xây mô phỏng 60 tick/giây, màn Đêm 1 với camera 3D và chế độ headless dùng chung mô phỏng.
- [x] Chạy test, chơi thử trên Linux, lưu đầu ra nguyên gốc cho ván thắng và thua.
- [x] Ghi hướng dẫn chạy, nguồn, cách tính điểm, nhật ký AI và lệnh kiểm chứng.
- [ ] Chốt commit và xác nhận tag phase-1 trên GitHub.

## Yêu cầu và bằng chứng

| Yêu cầu | Cách kiểm chứng | Kết quả |
|---|---|---|
| Màn Đêm 1, đảo tròn, 5 đèn, camera góc nhìn thứ ba, Mây có nón lá và đèn nhỏ | Mở game trên Chromium trong Codex, quan sát cảnh và HUD | Đã thấy cảnh 3D, nón lá, đèn nhỏ và bộ đếm 0/5 |
| Di chuyển, nhảy, nhặt và nạp đom đóm | W và E trong Chromium, các bài kiểm tra hướng di chuyển, cạnh nhấn, độ cao, bán kính và nạp dần | HUD ghi 40 điểm và 4/5 đom đóm đã nạp; test qua |
| Bóng Mực đuổi, mất lửa, vùng an toàn, tỏa sáng | Test va chạm, miễn nhiễm, tỏa sáng hướng vào và lướt qua vùng an toàn, thắp đèn khi Bóng Mực đang choáng | Cú đẩy dừng trước mép vùng an toàn, Bóng Mực vẫn choáng. Đèn mới thắp xua Bóng Mực ra ngoài cả vùng chồng lấn |
| Thắng, thua, điểm và chơi lại | CLI phát lại bản đồ mặc định seed 12. Kiểm tra màn thua và bấm Chơi lại trong Chromium | Thắp 5 đèn và thắng ở tick 1148 với 1220 điểm. Ván đứng yên thua ở tick 711. Chơi lại đặt HUD về 3 lửa, 0 điểm và 4 phút |
| Hợp đồng JSONL | Test CLI, so các mốc tick và đếm sự kiện, kiểm tra scenario rỗng và JSON không hợp lệ, chạy hai lần cùng seed và input | 15 bài kiểm tra đạt. Scenario rỗng cho đầu ra giống mặc định. File chứa `NaN`, `Infinity` hoặc `-Infinity` trả mã 2 và ghi lỗi ra stderr. Hai đầu ra thắng giống nhau theo từng byte |

Đầu vào phát lại và đầu ra gốc nằm trong [docs/proof/phase-1](proof/phase-1/). Ván thắng dùng input đã ghi từ một lượt chạy tự động trên bản đồ mặc định, không dùng scenario ghi đè. Ván thua không cấp input. Chạy lại bằng `sh scripts/verify-phase-1.sh`. Chưa chơi hết ván thắng bằng bàn phím và chưa thử trên macOS.

## Giả định

- Python 3.10 trở lên, không cần gói Python ngoài thư viện chuẩn. Canvas chiếu phối cảnh từ không gian XYZ. Python chạy toàn bộ mô phỏng cho CLI và trình duyệt.
- Nhặt tự động, đèn nhận tối đa số ánh sáng còn thiếu và cho nạp từng phần. E chọn đèn chưa sáng gần nhất, xử lý theo thứ tự ID nếu ngang nhau.
- Đêm 1 dài 240 giây. Hết giờ hoặc hết lửa sẽ thua. Nếu vừa thắp đèn cuối trong một bước, ván thắng trước khi xử lý va chạm của Bóng Mực. Thời gian thưởng tính theo giây nguyên còn lại.
- Bóng Mực có thể chạm vào Mây đang nhảy vì contract đo va chạm theo XZ. Va chạm không rơi đom đóm và không có dash. Rìa đảo áp dụng cho cả bản chơi và headless. Nếu scenario đặt Mây sẵn ngoài rìa, Mây đứng nguyên khi không di chuyển và có thể đi về phía đảo.
- Đèn đã thắp chặn cú đẩy của tỏa sáng ở rìa vùng an toàn. Bóng Mực trúng xung vẫn bị choáng và được tính điểm.
- Mảng motes/shades có mặt trong scenario sẽ thay danh sách mặc định. Đèn không được liệt kê giữ trạng thái mặc định.
- Dùng tên sự kiện `mote_picked` theo ví dụ trong contract. PRD-0 đã nhận không quy định tên của các sự kiện còn lại, nên chọn `jumped`, `lantern_deposited`, `lantern_lit`, `pulse`, `shade_stunned`, `player_hit`, `game_won` và `game_lost`.

## Nhật ký AI

| Công việc và lời nhắc chính | Kết quả, lỗi và cách phát hiện | Điều chỉnh | Ước tính |
|---|---|---|---|
| Codex — “liệt kê các bước để hoàn thiện phase 1 và thực hiện” theo PRD-0 người dùng cung cấp | Một kịch bản nạp đèn hai lần ban đầu thất bại vì đom đóm được đặt cách điểm dừng xa hơn bán kính nhặt | Tính lại vị trí trong kịch bản, giữ nguyên logic game. Dùng cùng một lõi mô phỏng và thêm lệnh kiểm chứng vào AGENTS.md và CI | Khoảng 15.000–25.000 token gồm ngữ cảnh và mã, không có số đo chi phí. Dùng thư viện chuẩn, mô hình dựng từ mã và chạy bộ kiểm chứng cục bộ |
