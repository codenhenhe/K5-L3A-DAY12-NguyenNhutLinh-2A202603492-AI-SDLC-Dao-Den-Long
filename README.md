# Đảo Đèn Lồng

Đêm 1 · Đảo Bến. Dẫn Mây qua hòn đảo giữa biển mây, gom đom đóm và thắp cả năm Đèn Lồng Lớn trước khi Bóng Mực dập tắt lửa.

## Chơi

Cần Python 3.10 trở lên và một trình duyệt desktop trên macOS hoặc Linux. Từ thư mục repo:

```sh
python3 -m lantern play
```

Nếu trình duyệt chưa tự mở, vào `http://127.0.0.1:8765`. Chọn **Bắt đầu**. Có thể chọn **Chơi lại** sau khi ván kết thúc.

| Phím | Thao tác |
|---|---|
| W A S D | Di chuyển theo hướng camera |
| ← → | Xoay camera |
| Space | Nhảy |
| E | Nạp đom đóm cho đèn chưa sáng gần nhất |
| F | Tỏa sáng, tốn hai đom đóm và làm choáng Bóng Mực ở gần |

Đom đóm được nhặt tự động trong tầm, tối đa 12. Mỗi đèn cần 5 đom đóm và có thể nạp nhiều lần. Đèn đã thắp tạo vùng an toàn. Mây có ba ngọn lửa, mất một ngọn khi bị chạm và có 1,25 giây miễn nhiễm sau đó. Không rơi khỏi đảo, không rơi đom đóm khi bị chạm và không có dash. Hết lửa hoặc hết 4 phút thì thua.

Điểm gồm 10 cho mỗi đom đóm nhặt được, 100 cho mỗi đèn thắp được và 25 cho mỗi lần làm choáng một Bóng Mực. Khi thắng, cộng điểm theo số giây nguyên còn lại và 50 cho mỗi ngọn lửa còn lại.

## Headless và kiểm chứng

```sh
python3 -m lantern headless --seed 12 --night 1 --ticks 1800 --out /tmp/lantern.jsonl
sh scripts/verify-phase-1.sh
```

Thêm `--scenario path.json` để đặt trạng thái ban đầu, `--inputs path.json` để chạy theo các frame điều khiển và `--snapshot-every N` để đổi chu kỳ snapshot. Cấu hình chính thức nằm trong [game.contract.json](game.contract.json). Xem [tiêu chí, giả định và bằng chứng](docs/phase-1.md).

## Sáng tạo của tôi

Đảo tròn cách điệu với biển mây chuyển động, đom đóm lơ lửng và xung sáng lan trên nền đất. Mây có nón lá treo đèn nhỏ. Các hiệu ứng được vẽ từ snapshot, nên ánh sáng, chuyển động trang trí và camera không làm thay đổi kết quả headless. Bộ kiểm chứng so sánh hai lần phát lại cùng một ván mặc định theo từng byte.

[Tài liệu lab](GUIDE.md) · [Checkpoint](CHECKPOINTS.md) · [Quy cách nộp](SUBMISSION.md) · [Nguồn](CREDITS.md)
