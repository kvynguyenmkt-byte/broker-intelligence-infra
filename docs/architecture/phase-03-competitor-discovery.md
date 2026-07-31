# Phase 3 — Competitor Discovery

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `Competitor` (`cmp_`) trong `config/schemas/canonical.v1.json`

## 1. Objective

Phát hiện các domain đối thủ cho từng market và **phân lớp** chúng, tạo đầu vào cho Phase 5 (SERP), Phase 6 (Landing Page), Phase 8 (Competitor Intelligence). Ba yêu cầu cứng:

1. **Phân lớp bắt buộc** — mỗi đối thủ mang `competitor_class` ∈ `{direct_broker, affiliate_review, informational}`. Trong ngành forex, SERP bị site affiliate thống trị; danh sách không phân lớp là danh sách vô dụng.
2. **Loại nhiễu thương hiệu** — độ trùng lặp (`overlap`) phải tính **sau khi bỏ keyword thương hiệu**, nếu không mọi site review sẽ giả làm đối thủ trực tiếp.
3. **Không kết luận chủ quan** — chỉ thu thập tín hiệu khách quan và gắn nhãn theo luật, không xếp hạng "đối thủ đáng ngại nhất".

## 2. Architecture

### 2.1 Nguồn phát hiện và capability

| Nguồn | Capability | `seed_source` |
|---|---|---|
| `known_competitors[]` từ input | — | `user` (kèm `seed_validated`) |
| Trùng organic | `organic_competitors`, `organic_keywords` | `organic_overlap` |
| Trùng paid | `paid_competitors`, `paid_keywords` | `paid_overlap` |
| Hiện diện SERP | `serp_snapshot` (Phase 5) | `serp` |

Collector chỉ khai báo capability; tầng `providers` chọn nguồn theo `providers.yaml`.

### 2.2 Sáu bước xử lý

```
1. Gom seed (user + overlap + serp) → tập domain ứng viên
2. Chuẩn hoá domain bằng PSL, dedup theo registrable domain
3. Loại excluded_domains (domain nội bộ / affiliate của mình)
4. Tính overlap SAU khi bỏ keyword is_branded
5. Phân lớp bằng luật trên tín hiệu quan sát (classification_signals)
6. Cắt theo max_competitors, giữ top theo overlap_score
```

### 2.3 Phân lớp bằng luật, không bằng phán đoán

`classification_signals` là ba cờ khách quan, `competitor_class` suy ra theo thứ tự ưu tiên cố định:

| Tín hiệu | Nguồn |
|---|---|
| `matches_biased_url_pattern` | `source_priority.yaml` biased_source_signals (`/review`, `/danh-gia`, `/best-`, `/top-`, `/san-forex-uy-tin`) |
| `has_review_listicle_pattern` | Cấu trúc trang dạng bảng xếp hạng nhiều broker |
| `has_broker_license_reference` | Trang nhắc số giấy phép / cơ quan quản lý của **chính domain đó** |

Luật: có tín hiệu review/biased mạnh → `affiliate_review`; có tham chiếu giấy phép của chính mình và không phải listicle → `direct_broker`; còn lại → `informational`. Luật nằm ở config, không hardcode.

### 2.4 Overlap không nhiễu thương hiệu

`shared_keyword_count` và `overlap_score` (thang 0–1) tính trên tập keyword đã lọc `is_branded = false`. Cả hai là `Measurement` có `provenance`. `overlap_score` gắn `reliability: inferred` (hệ thống suy ra từ hai tập keyword).

## 3. Reasoning

**Vì sao đúng ba lớp?** Hai lớp (đối thủ / không) đánh mất phân biệt then chốt giữa broker thật và site affiliate — hai nhóm cần chiến lược đối chiếu hoàn toàn khác. Bốn lớp trở lên làm ranh giới nhoè và tăng lỗi phân loại mà không thêm giá trị quyết định.

**Vì sao bỏ keyword thương hiệu?** Site review xếp hạng "broker X" sẽ trùng toàn bộ keyword thương hiệu của X, tạo overlap giả 90%+. Bỏ nhánh branded mới lộ ra ai thực sự cạnh tranh trên nhu cầu generic.

**Vì sao phân lớp bằng luật?** Nhãn do model tự phán là nhận định chủ quan — vi phạm mandate. Luật trên tín hiệu quan sát thì tái lập được và kiểm toán được.

## 4. Advantages

- Danh sách đối thủ dùng được ngay cho Phase 8 vì đã phân lớp.
- Overlap phản ánh cạnh tranh thật, không bị site review làm nhiễu.
- Phân lớp tái lập, kiểm toán được qua `classification_signals`.
- Thêm nguồn phát hiện = thêm một `seed_source`, không đổi lõi.

## 5. Disadvantages

- Luật phân lớp cần bảo trì khi cấu trúc site affiliate thay đổi.
- `has_broker_license_reference` cần đọc nội dung trang → chi phí + độ trễ.
- Ngưỡng cắt `max_competitors` có thể bỏ sót đối thủ ngách volume thấp.

## 6. Tradeoffs

| Cách phân lớp | A. Luật trên tín hiệu | B. Mô hình ML | C. Con người gán nhãn |
|---|---|---|---|
| Tái lập | Cao | Trung bình | Thấp |
| Chi phí vận hành | Thấp | Cao (train + drift) | Rất cao |
| Kiểm toán | Dễ | Khó (hộp đen) | Dễ |
| Vi phạm mandate | Không | Rủi ro (suy diễn) | Không |

**Xếp hạng: A > C > B.** A tái lập, rẻ, kiểm toán được và không suy diễn chủ quan. C chính xác nhưng không scale tới hàng trăm broker. B bị loại vì hộp đen mâu thuẫn yêu cầu provenance và dễ trượt thành nhận định.

## 7. Best Practice

- Luôn bỏ `is_branded` trước khi tính bất kỳ overlap nào.
- Dedup domain bằng PSL, không bằng chuỗi.
- Gắn `seed_validated: false` cho competitor gợi ý không phân giải được, không loại bỏ.
- Ghi `classification_signals` đầy đủ kể cả khi đã suy ra `competitor_class`, để kiểm toán.
- Giữ luật phân lớp trong config, không hardcode trong collector.

## 8. Common Mistakes

1. Tính overlap gồm cả keyword thương hiệu → site review giả làm đối thủ trực tiếp.
2. Gộp broker thật và site affiliate vào một rổ.
3. Để model tự phán "đây là đối thủ mạnh".
4. Cắt domain bằng regex thay vì PSL.
5. Loại thẳng competitor gợi ý sai thay vì gắn cờ `seed_validated: false`.
6. Xếp hạng chủ quan competitor trong output.
7. Quên loại `excluded_domains` (affiliate của chính mình).

## 9. Checklist

- [x] Chốt ba lớp `direct_broker / affiliate_review / informational`
- [x] Chốt `seed_source` bốn giá trị + `seed_validated`
- [x] Chốt overlap tính sau khi bỏ `is_branded` (ADR-011)
- [x] Chốt `classification_signals` ba cờ khách quan
- [x] Chốt `overlap_score` là `Measurement` reliability `inferred`
- [x] Chốt dedup domain bằng PSL và loại `excluded_domains`
- [x] Chốt cắt theo `max_competitors` (ADR-009)
- [x] Chốt entity `Competitor` trong `canonical.v1.json`
