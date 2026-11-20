# Đảo Đèn Lồng

Dẫn Mây qua Đảo Bến, Đảo Sương và Đảo Chuông. Gom đom đóm để thắp các Đèn Lồng Lớn trước khi Bóng Mực dập tắt lửa.

## Chơi

Cần Python 3.10 trở lên và trình duyệt desktop trên macOS hoặc Linux. Từ thư mục repo chạy:

```sh
python3 -m lantern play
```

Nếu trình duyệt chưa tự mở, vào `http://127.0.0.1:8765`. Nếu cổng mặc định đang được dùng, chạy `python3 -m lantern play --port 8766`.

| Phím | Thao tác |
|---|---|
| W A S D | Di chuyển theo hướng camera |
| ← → hoặc kéo chuột | Xoay camera |
| Space | Nhảy |
| Shift | Lướt |
| E | Nạp ánh sáng vào đèn gần nhất |
| F | Tỏa sáng |
| Esc / P | Tạm dừng hoặc tiếp tục |

Đom đóm và Bùa Gió được nhặt tự động. Ba Đêm lần lượt dài 5:00, 5:30 và 6:00. Mỗi đèn cần 10 đom đóm và có thể nạp nhiều lần. Đèn đã thắp ngăn Bóng Mực, còn Gió Lạc vẫn vào được để cướp đom đóm. Bùa Gió tăng tốc và bỏ thời gian hồi Lướt trong 10 giây. Tỏa Sáng tốn 3 đom đóm và hồi trong 3 giây. Nếu rơi khỏi đảo, Mây mất một Ngọn Lửa và đom đóm đang mang, rồi trở lại sau 1 giây nếu còn sống.

Mỗi đom đóm **đã nạp** được 10 điểm. Thắp đèn được 100 điểm, mỗi Bóng Mực trúng một lần Tỏa Sáng được 5 điểm. Khi thắng, mỗi giây nguyên còn lại được 2 điểm và mỗi Ngọn Lửa còn lại được 50 điểm. Tổng điểm Bình Minh cộng ba Đêm thắng. Nếu thua, có thể chơi lại Đêm đó.

## Headless và kiểm chứng

```sh
python3 -m lantern headless --seed 42 --night 2 --ticks 1800 --out /tmp/lantern.jsonl
sh scripts/verify-phase-2.sh
```

`--night` nhận 1, 2, 3. Thêm `--scenario path.json` để đặt trạng thái ban đầu, `--inputs path.json` để phát lại điều khiển và `--snapshot-every N` để đổi chu kỳ snapshot. Xem [game.contract.json](game.contract.json) cho cấu hình hiện tại và [spec Phase 2](docs/phase-2.md) cho tiêu chí nghiệm thu và bằng chứng.

Bộ kiểm chứng Phase 1 dùng tag `phase-1` để phát lại đúng Contract v1.0:

```sh
sh scripts/verify-phase-1.sh
```

## Sáng tạo của tôi

Biển mây chuyển động, đom đóm lơ lửng và xung sáng lan trên nền đất. Mây có nón lá treo đèn nhỏ. Hình ảnh và âm thanh được dựng từ kết quả mô phỏng trong trình duyệt. Bộ kiểm chứng so sánh từng byte của hai lần phát lại cùng đầu vào.

[Hướng dẫn lab](GUIDE.md) · [Checkpoint](CHECKPOINTS.md) · [Quy cách nộp](SUBMISSION.md) · [Nguồn](CREDITS.md)
