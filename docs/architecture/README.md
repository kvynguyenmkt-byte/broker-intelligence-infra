# Kiến trúc Research Agent — Chỉ mục và nhật ký quyết định

Cập nhật: 2026-07-31

## Trạng thái các phase

| Phase | Nội dung | Trạng thái | File |
|---|---|---|---|
| 1 | System Architecture | ✅ Chốt | `phase-01-system-architecture.md` |
| 2 | Input Design | ✅ Chốt | `phase-02-input-design.md` |
| 3 | Competitor Discovery | ⬜ Chưa viết | — |
| 4 | Keyword Research | ⬜ Chưa viết | — |
| 5 | SERP Research | ⬜ Chưa viết | — |
| 6 | Landing Page Discovery | ⬜ Chưa viết | — |
| 7 | Ad Intelligence | ⬜ Chưa viết | — |
| 8 | Competitor Intelligence | ⬜ Chưa viết | — |
| 9 | Output Schema | ⬜ Chưa viết | — |
| 10 | Validation | ⬜ Chưa viết | — |
| 11 | Storage | ⬜ Chưa viết | — |
| 12 | Scalability | ⬜ Chưa viết | — |

Mã nguồn: lát cắt dọc đầu tiên (`CLAUDE.md` mục 7) đã thông end-to-end, offline.

| Bước | Module | Trạng thái |
|---|---|---|
| 1 | `core` (types, provenance, identity, errors, logging) | ✅ Xong + unit test |
| 2 | `intake` (6 chặng, PSL, market_resolver) | ✅ Xong + unit test |
| 3 | `providers` (base, registry, DataForSeoAdapter) | ✅ Xong + contract test |
| 4 | `collectors/keyword_research` | ✅ Xong |
| 5 | End-to-end 1 broker × 1 market (VN-vi) → JSON hợp lệ | ✅ Xong (test offline trên fixture) |
| 6 | Nhân rộng adapter/collector còn lại | ⬜ Chỉ làm sau khi luồng trên được review |

`config/schemas/canonical.v1.json` hiện là **lát cắt tối thiểu** của Phase 9 (chỉ
`Provenance`/`Measurement`/`Keyword`). Phase 9 đầy đủ (cmp_/srp_/lp_/ad_/prf_) vẫn
chưa chốt — cần hoàn tất trước khi mở các collector còn lại.

Việc con người còn nợ (HANDOFF mục 5): điền `location_code` thật vào
`config/markets.yaml` từ endpoint `/locations`, và nạp credentials provider. Code
đã chạy + test offline không cần hai thứ này; **chạy thật** thì cần.

---

## Nhật ký quyết định (ADR rút gọn)

Mỗi quyết định dưới đây đã được chốt và không mở lại trừ khi có dữ kiện mới.

### ADR-001 — Kiến trúc modular với tầng trừu tượng nhà cung cấp
Chọn phương án B (modular + provider abstraction) thay vì monolith (A) hay microservices (C).
Lý do: đạt gần hết lợi ích của C với một phần nhỏ chi phí vận hành, và nâng cấp B → C sau này
chỉ là thay lời gọi hàm bằng message queue vì orchestration đã tách sẵn.

### ADR-002 — Cấm khuyến nghị bằng schema, không bằng prompt
Prompt có thể bị lách, JSON Schema thì không. `additionalProperties: false` ở mọi nơi,
cộng linter chặn tên trường mang tính khuyến nghị. Xem `CLAUDE.md` mục 1.

### ADR-003 — Raw payload bất biến
Lưu nguyên trạng response từ API, không bao giờ ghi đè. Cho phép replay toàn bộ pipeline
với logic chuẩn hoá mới mà không tốn thêm chi phí API. Đây là khoản tiết kiệm lớn nhất
trong cả kiến trúc, vì DataForSEO tính tiền theo query.

### ADR-004 — Tách confidence và freshness thành hai điểm số
Một con số từ nguồn tốt nhưng cũ 6 tháng khác hoàn toàn một ước lượng thô nhưng mới hôm qua.
Gộp thành một điểm là mất thông tin.

### ADR-005 — Thêm module `compliance_context`
Forex/CFD là vertical bị Google Ads kiểm soát riêng, yêu cầu chứng nhận nhà quảng cáo theo
từng quốc gia. Không thu thập dữ kiện này thì agent phía sau sẽ lập kế hoạch cho thị trường
không thể chạy được. Module chỉ thu thập dữ kiện công khai, không kết luận, không tư vấn pháp lý.

### ADR-006 — Một run xử lý một broker × nhiều market
Input dùng mảng `markets[]`. Lý do: cùng một broker chạy nhiều nước chia sẻ phần khám phá
đối thủ cấp thương hiệu và profile domain; ép thành nhiều run riêng là trả tiền API nhiều lần
cho phần trùng nhau. `run_id` đánh ở cấp broker, `market_run_id` ở cấp thị trường, để một
market lỗi không kéo sập cả run.

### ADR-007 — Ngữ cảnh pháp lý không phải trường input
Người dùng không được khai báo tình trạng pháp lý qua payload. Nếu cho phép, đó là dữ liệu
chưa kiểm chứng lọt vào dataset, vi phạm nguyên tắc "never assume data". Agent tự thu thập.

### ADR-008 — `freshness_policy` mặc định là `prefer_cache`, TTL theo loại dữ liệu
Không dùng một TTL chung. Dữ liệu quảng cáo biến động nhanh hơn dữ liệu backlink nhiều lần.
Bảng TTL nằm ở `config/providers.yaml`.

| Loại dữ liệu | TTL |
|---|---|
| Ad creative (Transparency Center) | 3 ngày |
| SERP snapshot | 7 ngày |
| Landing page | 7 ngày |
| Backlink / authority | 14 ngày |
| Keyword volume | 30 ngày |
| Traffic estimate | 30 ngày |
| Compliance context | 30 ngày |

### ADR-009 — Trần quy mô mỗi run
20 market, 50 competitor gợi ý, 20 competitor giữ lại mỗi market (cứng tối đa 50).
Trần keyword theo `depth`: `quick` 300 / `standard` 1500 / `deep` 5000 mỗi market.
Lý do: bảo vệ thời gian chạy, checkpoint và ngân sách API. Vượt trần thì chia nhiều run.

### ADR-010 — Bổ sung chế độ `dry_run`
Chạy đủ validate, chuẩn hoá, phân giải market và in bảng ước tính chi phí, không gọi API
dòng nào. Đây là hàng rào cuối trước khi đốt quota.

---

## Ba nhãn độ tin cậy

`hard` (lấy trực tiếp) · `estimate` (nhà cung cấp ước lượng) · `inferred` (hệ thống suy ra).

Không có nhãn thứ tư. Mọi metric traffic và authority bị chặn trần ở `estimate`.

---

## Quy ước viết tài liệu phase

Mỗi file phase phải có đủ 9 mục, theo đúng thứ tự:

1. Objective — 2. Architecture — 3. Reasoning — 4. Advantages — 5. Disadvantages
— 6. Tradeoffs — 7. Best Practice — 8. Common Mistakes — 9. Checklist

Văn bản tiếng Việt, tên trường và mã lỗi tiếng Anh. Mọi phương án thay thế phải được
so sánh, xếp hạng và giải thích lý do chọn.
