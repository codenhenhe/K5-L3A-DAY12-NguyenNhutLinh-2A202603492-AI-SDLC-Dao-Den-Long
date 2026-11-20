# Đảo Đèn Lồng v1.0.0

Ba Đêm với cơ chế duy trì dầu đèn tới bình minh. Bản phát hành thêm bảng xếp hạng local, đổi phím, phụ đề bằng chữ, chữ lớn và giảm chuyển động. Test Contract v1.3 có thêm benchmark và soak, giữ mô phỏng v1.2.

## Chạy bản phát hành

Tải **dao-den-long-v1.0.0.pyz** rồi chạy `python3 dao-den-long-v1.0.0.pyz`. Cần Python 3.10+ và trình duyệt desktop trên Linux hoặc macOS. Dùng `python3 dao-den-long-v1.0.0.pyz play --port 0` nếu cổng mặc định bị chiếm.

## Tạo Release trên GitHub

Sau khi đã xem và commit bản local, gắn rồi push tag `phase-4`. Push `main` để bản clone mặc định có đủ game, README và video. Tạo Release **v1.0.0** với tag phát hành `v1.0.0` trỏ cùng commit. Đính kèm hai tệp:

- `dist/dao-den-long-v1.0.0.pyz`, được tạo bằng `python3 scripts/build_release.py`.
- `docs/demo/demo.mp4`, video chơi và kết quả kiểm chứng.

[Changelog](../CHANGELOG.md) · [Kiểm chứng Phase 4](phase-4.md)
