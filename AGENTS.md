# Đảo Đèn Lồng

- Đọc Ticket của phase hiện tại và spec tương ứng trong `docs/` trước khi thay đổi luật hoặc contract.
- Build bằng `python3 -m compileall -q lantern`. Chạy game bằng `python3 -m lantern play`.
- Chạy `sh scripts/verify-phase-2.sh` và `sh scripts/verify-phase-1.sh` khi kiểm tra Phase 2. Sửa test đỏ hoặc ghi rõ phần còn thiếu. Lưu đầu ra thật; không chỉnh JSONL bằng tay.
- `lantern/game.py` là mô phỏng chung của headless và trình duyệt. `lantern/maps.py` chứa bản đồ, tọa độ và địa hình. Trình duyệt xử lý điều khiển, dựng hình, HUD và âm thanh.
- `game.contract.json` là nguồn tuning cho mô phỏng. Giữ thứ tự xử lý mỗi tick 60 Hz, phân biệt tick ngoài với sim_tick và giữ định dạng JSONL cho đến khi ticket đổi contract.
- Giữ bằng chứng v1.0 gốc trong tag `phase-1`. Khi ticket thay luật, ghi rõ test được đổi và lý do trong tài liệu của phase.
