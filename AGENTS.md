# Đảo Đèn Lồng

- Đọc Ticket của phase hiện tại và spec tương ứng trong `docs/` trước khi thay đổi luật hoặc contract.
- Build bằng `python3 -m compileall -q lantern`. Chạy game bằng `python3 -m lantern play`.
- Chạy `sh scripts/verify-phase-4.sh` cho v1.3. Các script kiểm chứng Phase 1–3 tự dùng tag tương ứng khi chạy ở phase sau. Sửa test đỏ hoặc ghi rõ phần còn thiếu. Lưu đầu ra thật; không chỉnh JSONL bằng tay.
- `lantern/game.py` là mô phỏng chung của headless và trình duyệt. `lantern/maps.py` chứa bản đồ, tọa độ và địa hình. Trình duyệt xử lý điều khiển, dựng hình, HUD và âm thanh.
- `game.contract.json` là nguồn tuning cho mô phỏng. Giữ thứ tự xử lý mỗi tick 60 Hz, phân biệt tick ngoài với sim_tick và giữ định dạng JSONL cho đến khi ticket đổi contract.
- Giữ bằng chứng gốc trong các tag `phase-1`, `phase-2`. Dầu v1.2 dùng đơn vị nguyên 1/60, chỉ làm tròn lúc xuất JSONL. Khi ticket thay luật, ghi rõ test được đổi và lý do trong tài liệu của phase.

- Khi sửa benchmark, chạy đúng `python3 -m lantern bench --seed 42 --duration 30 --out bench.json`. Soak dùng seed 7 và 10 Đêm. Không chỉnh số đo bằng tay. Bản release chạy `python3 scripts/build_release.py`.
