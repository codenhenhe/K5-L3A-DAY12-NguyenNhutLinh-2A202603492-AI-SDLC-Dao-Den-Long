# Đảo Đèn Lồng

Dẫn Mây qua Đảo Bến, Đảo Sương và Đảo Chuông. Gom đom đóm để thắp và châm dầu cho các Đèn Lồng Lớn. Giữ đảo sáng tới bình minh.

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
| E | Thắp, thắp lại hoặc châm dầu cho đèn gần nhất còn nhận ánh sáng |
| F | Tỏa sáng |
| Esc / P | Tạm dừng hoặc tiếp tục |

Đom đóm và Bùa Gió được nhặt tự động. Thắp lần đầu tốn 10 đom đóm, thắp lại tốn 5. Đèn sáng hao 1 dầu mỗi giây. Châm thêm 10 dầu mỗi đom đóm, đến tối đa 100. Đèn yếu nhấp nháy và Bóng Mực có thể hút dầu khi dưới 30. Sức chứa tăng 2 sau mỗi lần thắp thành công, tối đa 20.

Đêm 1/2/3 dài 4:00, 4:30 và 5:00. Khi bình minh đến, Mây phải còn sống và giữ lần lượt **3/5, 4/6 và 5/7 đèn sáng**. Bật **Bảng màu dễ phân biệt** trong Cài đặt để dùng viền xanh lam và cảnh báo trắng có biểu tượng.

Mỗi đom đóm đã nạp được 5 điểm. Thắp lần đầu được 100 điểm, thắp lại được 40. Mỗi Bóng Mực trúng Tỏa Sáng được 5 điểm, hoặc tổng 15 nếu nó đang hút dầu. Khi thắng, mỗi đèn sáng được 50 điểm cộng phần nguyên dầu còn lại và mỗi Ngọn Lửa còn lại được 50 điểm. Tổng điểm Bình Minh cộng ba Đêm thắng. Nếu thua, có thể chơi lại Đêm đó.

## Headless và kiểm chứng

```sh
python3 -m lantern headless --seed 42 --night 2 --ticks 1800 --out /tmp/lantern.jsonl
sh scripts/verify-phase-3.sh
```

`--night` nhận 1, 2, 3. Thêm `--scenario path.json` để đặt trạng thái ban đầu, `--inputs path.json` để phát lại điều khiển và `--snapshot-every N` để đổi chu kỳ snapshot. Xem [game.contract.json](game.contract.json) cho cấu hình hiện tại và [spec Phase 3](docs/phase-3.md) cho tiêu chí nghiệm thu và bằng chứng.

Hai bộ kiểm chứng cũ phát lại các tag gốc và luật tương ứng:

```sh
sh scripts/verify-phase-1.sh
sh scripts/verify-phase-2.sh
```

## Sáng tạo của tôi

Biển mây chuyển động, đom đóm lơ lửng và xung sáng lan trên nền đất. Mây có nón lá treo đèn nhỏ. Hình ảnh và âm thanh được dựng từ kết quả mô phỏng trong trình duyệt. Bộ kiểm chứng so sánh từng byte của hai lần phát lại cùng đầu vào.

[Hướng dẫn lab](GUIDE.md) · [Checkpoint](CHECKPOINTS.md) · [Quy cách nộp](SUBMISSION.md) · [Nguồn](CREDITS.md) · [Changelog](CHANGELOG.md)
