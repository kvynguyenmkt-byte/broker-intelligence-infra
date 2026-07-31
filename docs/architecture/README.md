# Kiến trúc Research Agent — Chỉ mục và nhật ký quyết định

Cập nhật: 2026-07-31

## Trạng thái các phase

| Phase | Nội dung | Trạng thái | File |
|---|---|---|---|
| 1 | System Architecture | ✅ Chốt | `phase-01-system-architecture.md` |
| 2 | Input Design | ✅ Chốt | `phase-02-input-design.md` |
| 3 | Competitor Discovery | ✅ Chốt | `phase-03-competitor-discovery.md` |
| 4 | Keyword Research | ✅ Chốt | `phase-04-keyword-research.md` |
| 5 | SERP Research | ✅ Chốt | `phase-05-serp-research.md` |
| 6 | Landing Page Discovery | ✅ Chốt | `phase-06-landing-page-discovery.md` |
| 7 | Ad Intelligence | ✅ Chốt | `phase-07-ad-intelligence.md` |
| 8 | Competitor Intelligence | ✅ Chốt | `phase-08-competitor-intelligence.md` |
| 9 | Output Schema | ✅ Chốt | `phase-09-output-schema.md` |
| 10 | Validation | ✅ Chốt | `phase-10-validation.md` |
| 11 | Storage | ✅ Chốt | `phase-11-storage.md` |
| 12 | Scalability | ✅ Chốt | `phase-12-scalability.md` |

Mã nguồn: lát cắt dọc đầu tiên (`CLAUDE.md` mục 7) đã thông end-to-end, offline.

| Bước | Module | Trạng thái |
|---|---|---|
| 1 | `core` (types, provenance, identity, errors, logging) | ✅ Xong + unit test |
| 2 | `intake` (6 chặng, PSL, market_resolver) | ✅ Xong + unit test |
| 3 | `providers` (base, registry, DataForSeoAdapter, AhrefsAdapter) | ✅ Xong + contract test |
| 4 | `collectors/keyword_research` (Phase 4) | ✅ Xong + e2e |
| 5 | `collectors/competitor_discovery` (Phase 3) | ✅ Xong + e2e (overlap loại branded) |
| 6 | `collectors/serp_research` (Phase 5) | ✅ Xong + e2e (device + mô hình khối) |
| 7 | End-to-end 1 broker × 1 market (VN-vi) → JSON hợp lệ | ✅ Xong (test offline trên fixture) |
| 8 | Collector còn lại: landing_page, ad_intelligence, competitor_intelligence | ⬜ Chưa hiện thực |
| 9 | Module `resolve/validate/storage/output/orchestration/observability` | ⬜ Chưa hiện thực |

`config/schemas/canonical.v1.json` đã là **hợp đồng đầy đủ** (Phase 9 chốt): bảy entity
`cmp_/kw_/clu_/srp_/lp_/ad_/prf_` + `Measurement`/`Provenance` dùng chung. Đã hiện thực
`Keyword` (Phase 4), `Competitor` (Phase 3), `SerpSnapshot` (Phase 5); phần còn lại chờ
collector tương ứng.

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

### ADR-011 — Phân lớp đối thủ và overlap không nhiễu thương hiệu (Phase 3)
Đối thủ phân ba lớp `direct_broker / affiliate_review / informational` bằng luật trên
tín hiệu quan sát (`classification_signals`), không bằng phán đoán model. Overlap tính
**sau khi loại keyword `is_branded`** — nếu không, site review trùng toàn bộ keyword
thương hiệu sẽ giả làm đối thủ trực tiếp.

### ADR-012 — Intent `trust_check` và cụm keyword bằng cấu trúc (Phase 4)
Thêm intent `trust_check` (scam/lừa đảo/uy tín) bên cạnh bốn intent kinh điển — nhóm
volume lớn, hành vi khác commercial. Intent gán bằng lexicon theo market (`intent_method`),
không bằng model. Cụm nhận diện bằng `head_keyword_id` + `cluster_method`, KHÔNG bằng
nhãn prose do model sinh (tránh field text tự do).

### ADR-013 — SERP theo device và mô hình khối (Phase 5)
`device` (`mobile`/`desktop`) là chiều BẮT BUỘC của `SerpSnapshot` — ads hai device
khác nhau đáng kể. Vị trí dùng `block_rank` + `rank_in_block`, không dùng "position"
đơn lẻ; `is_ad` tách quảng cáo khỏi organic.

### ADR-014 — Landing page: subdomain riêng và tách-nhưng-ghi tham số (Phase 6)
Trang đích quảng cáo thường ở subdomain `lp/go/promo` và `noindex`. Tách tham số
affiliate khỏi `url_canonical` NHƯNG lưu `stripped_params[]` và `redirect_chain[]` —
sạch để dedup mà không mất tình báo affiliate.

### ADR-015 — Ad chỉ lưu nguyên văn, cấm sinh nội dung (Phase 7)
Điểm rủi ro mandate cao nhất. Mọi text ad mang hậu tố `_observed` + provenance; phân
tích pattern chỉ trả tần suất và cờ hiện diện khách quan (`observed_flags`). Schema `Ad`
CỐ TÌNH không có field chứa câu quảng cáo mới — cưỡng chế ADR-002 tại điểm nóng.

### ADR-016 — Không bao giờ lấy trung bình giữa nguồn (Phase 8)
Nhiều nguồn lệch nhau: chọn `value` theo `source_priority.yaml`, lưu `values_by_source[]`,
tính `divergence_ratio`; lệch > 3 lần thì `low_agreement=true` và trần confidence 0.5.
Traffic/authority trần `estimate`; DR và AS là hai thang KHÔNG quy đổi.

### ADR-017 — Output quan hệ, tham chiếu bằng ID (Phase 9)
Bảy entity (`cmp_/kw_/clu_/srp_/lp_/ad_/prf_`) tham chiếu chéo bằng ID tất định, không
lồng trùng dữ liệu. Dùng chung `Measurement` và `Provenance`. Mảng entity tuỳ chọn ở gốc
để dataset bộ phận vẫn hợp lệ (fail-soft). `additionalProperties:false` + linter mandate
là hai cổng cưỡng chế.

### ADR-018 — Validation phát hiện, không sửa (Phase 10)
`validate` gồm ba lớp: schema (canonical.v1.json), business rules, QA gate. Chỉ báo lỗi,
KHÔNG bao giờ tự sửa — sửa lặng lẽ là cách dữ liệu bẩn sống sót. Kiểm toàn vẹn tham chiếu
mọi `*_id`. Phân biệt `block` (dữ liệu sai/tham chiếu gãy) và `warn` (chất lượng yếu); chỉ
`block` khi tiếp tục tạo dữ liệu sai. Linter mandate là một luật validation.

### ADR-019 — Lưu trữ ba tầng, raw bất biến content-addressed (Phase 11)
Bốn kho: `raw` (write-once, content-addressed, cho replay không tốn API), `normalized`,
`snapshots` (có `schema_version`), `cache` (TTL theo loại từ `providers.yaml`). `storage`
không biến đổi dữ liệu. Retention cấu hình được, đặt từ ngày đầu vì raw tốn dung lượng.

### ADR-020 — Checkpoint theo market, nâng cấp B→C khi có tải (Phase 12)
Đơn vị checkpoint/song song là `market_run_id`; một market fail chuyển `partial`, không
sập run; resume dùng raw cache nên không gọi lại API. Song song ba trục broker/market/
collector, tôn trọng `rate_limit` từng provider. Giữ `orchestration` không chứa nghiệp vụ
để nâng DAG in-process → hàng đợi message chỉ khi có tải biện minh (ADR-001).

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
