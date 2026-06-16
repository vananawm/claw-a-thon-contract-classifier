# Agent Phân Loại Hợp Đồng — Claw-a-thon 2026

AI Agent giúp đội pháp chế **đối chiếu hợp đồng với bộ template chuẩn** và tự động
phân loại thành 3 nhóm:

1. **Giống từ 70% trở lên** — khớp template (có thể có chỉnh sửa nhỏ).
2. **Hợp đồng trọng yếu** — loại quan trọng như NDA, License Agreement.
3. **Không theo template** — không khớp template nào và không thuộc nhóm trọng yếu.

## Use case

Đội pháp chế nhận hàng loạt hợp đồng cần rà soát. Thay vì mở từng file để so với
template, agent đọc cả lô, tính **% giống** với từng template, nhận diện hợp đồng
trọng yếu (dùng model AI), sắp xếp vào đúng nhóm và **xuất báo cáo** — nhanh, nhất
quán, lặp lại được.

> **Khác gì Claude/ChatGPT?** Model tổng quát chỉ trả lời từng câu hỏi và không nhớ
> template, không thao tác file, không tạo thư mục hay xuất báo cáo có cấu trúc.
> Agent này đóng gói trọn quy trình nghiệp vụ — và *dùng* model AI làm lõi bên trong.

## Hai cách dùng

### 1) Web app (deploy lên AgentBase)
```bash
pip install -r requirements.txt
python app.py            # mở http://localhost:8080
```
- Khu 1: upload template/hợp đồng mẫu (tùy chọn giữ lại cho lần sau).
- Khu 2: upload hợp đồng cần phân loại.
- Nhận kết quả theo nhóm + tải báo cáo Excel và gói kết quả (.zip).

### 2) Chế độ folder (chạy local, batch)
Đặt hợp đồng vào `contracts/LG-xxxx/`, template vào `template/`, rồi:
```bash
python classify_contracts.py
```
Kết quả ghi ra `Result/R-<timestamp>/` với 4... 3 folder con theo nhóm + báo cáo.

## Cấu trúc

| File | Vai trò |
|---|---|
| `classifier.py` | Lõi phân loại dùng chung (đọc file, chuẩn hóa, tính % giống, phân nhóm) |
| `app.py` | Web app upload (Flask) — bản deploy lên AgentBase |
| `classify_contracts.py` | Bản chạy theo folder (batch/local) |

## Lưu ý dữ liệu & bảo mật
- Chỉ dùng hợp đồng **công khai / giả lập / đã ẩn danh**. Không dùng dữ liệu thật
  của khách hàng, đồng nghiệp hay dữ liệu nội bộ mật.
- **Không commit** API Key / Client Secret lên GitHub (đã chặn trong `.gitignore`).

## Hướng phát triển (roadmap)
- Kết nối **eform / SharePoint / Drive** để agent tự kéo hợp đồng về phân tích.
- Lưu trữ template bền vững (object storage) qua nhiều phiên.
- Chỉ ra **điều khoản khác biệt** so với template cho nhóm "Giống ≥70%".
