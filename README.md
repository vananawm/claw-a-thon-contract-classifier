# Agent Phân Loại Hợp Đồng — Claw-a-thon 2026

AI Agent giúp đội pháp chế **rà soát hàng loạt hợp đồng**: đối chiếu với bộ template
chuẩn và **nhận diện hợp đồng trọng yếu** bằng model **Qwen 3.5 (GreenNode MaaS)**,
rồi đề xuất quy trình review phù hợp.

## Agent làm gì

- **Đối chiếu template (tùy chọn):** tính % tương đồng của mỗi hợp đồng với từng template.
  Khi có template, phân vào 3 nhóm: *Giống từ 70% trở lên*, *Hợp đồng trọng yếu*,
  *Không theo template*.
- **Nhận diện trọng yếu (luôn chạy):** dựa trên **danh sách hợp đồng trọng yếu của công ty**
  (game licensing, IP, payment gateway, DPA, exclusivity, MFN, MoU/LOI, hợp đồng ≥3 năm /
  auto-renew...). Model Qwen đọc nội dung và phân loại, có fallback dò từ khóa khi không gọi được model.
- **Có thể chạy KHÔNG cần template:** chỉ cần upload hợp đồng → agent phân *Trọng yếu /
  Không trọng yếu*.
- **Ghi chú quy trình review cho từng hợp đồng:**
  - Trọng yếu → **"Bắt buộc phải có legal review"**
  - Không trọng yếu → **"Review theo quy trình được ban hành"**
- **Xuất kết quả:** danh sách theo nhóm, loại + lý do (AI), và **báo cáo Excel** + gói zip tải về.

## Use case

Đội pháp chế nhận cả lô hợp đồng cần rà soát. Thay vì mở từng file để so với template và
tự đánh giá mức độ rủi ro, agent đọc cả lô, đối chiếu template, nhận diện hợp đồng trọng yếu
theo tiêu chí của công ty và đề xuất quy trình review — nhanh, nhất quán, có thể lặp lại.

> **Khác gì Claude/ChatGPT?** Model tổng quát chỉ trả lời từng câu hỏi và không nhớ template,
> không thao tác file, không tạo báo cáo có cấu trúc. Agent này đóng gói trọn quy trình
> nghiệp vụ pháp chế — và *dùng* model Qwen làm lõi bên trong.

## Hai cách dùng

### 1) Web app (deploy lên GreenNode AgentBase)
```bash
pip install -r requirements.txt
python app.py            # mở http://localhost:8080
```
- Khu 1: upload template/hợp đồng mẫu (**tùy chọn**, có thể bỏ trống).
- Khu 2: upload hợp đồng cần phân tích.
- Nhận kết quả theo nhóm + cột Quy trình review + tải báo cáo Excel/zip.

### 2) Chế độ folder (chạy local, batch)
Đặt hợp đồng vào `contracts/LG-xxxx/`, template vào `template/`, rồi:
```bash
python classify_contracts.py
```
Kết quả ghi ra `Result/R-<timestamp>/` theo nhóm + báo cáo.

## Cấu trúc

| File | Vai trò |
|---|---|
| `classifier.py` | Lõi: đọc file, chuẩn hóa, tính % giống, nhận diện trọng yếu (Qwen + danh sách), gắn note |
| `app.py` | Web app upload (Flask) — bản deploy lên AgentBase |
| `classify_contracts.py` | Bản chạy theo folder (batch/local) |

## Cấu hình (biến môi trường)

| Biến | Ý nghĩa |
|---|---|
| `GREENNODE_API_KEY` | API Key MaaS để gọi model Qwen (đưa qua file `.env`, không commit) |
| `GREENNODE_MODEL` | Mã model, mặc định `qwen/qwen3-5-27b` |
| `GREENNODE_BASE_URL` | Endpoint MaaS (OpenAI-compatible) |

## Lưu ý dữ liệu & bảo mật
- Chỉ dùng hợp đồng **công khai / giả lập / đã ẩn danh**. Không dùng dữ liệu thật của
  khách hàng, đồng nghiệp hay dữ liệu nội bộ mật.
- **Không commit** API Key / Client Secret (`.env`, `.greennode.json` đã bị chặn trong `.gitignore`).

## Hướng phát triển (roadmap)
- Kết nối **eform / SharePoint / Drive** để agent tự kéo hợp đồng về phân tích.
- Chỉ ra **điều khoản khác biệt** so với template cho nhóm "Giống ≥70%".
- Lưu trữ template bền vững qua nhiều phiên.
