# CLAUDE.md — Research Agent (Google Ads Intelligence for Forex/CFD/Crypto Brokers)

Đây là file ràng buộc cho mọi phiên làm việc trên repo này. Đọc trước khi sửa bất kỳ file nào.

---

## 1. Mandate của hệ thống

Research Agent nhận vào: `broker_name`, `broker_website`, `markets[]` (country + language).
Trả ra: một dataset nghiên cứu có cấu trúc, phục vụ các agent khác phía sau.

### Agent này TUYỆT ĐỐI KHÔNG được làm

- Viết nội dung quảng cáo Google Ads (headline, description, CTA mới)
- Đề xuất cấu trúc campaign / ad group
- Đề xuất bid, budget, chiến lược đặt giá
- Đưa ra khuyến nghị, nhận định, xếp hạng chủ quan
- Tư vấn pháp lý

Nó CHỈ thu thập, chuẩn hoá, kiểm định và cấu trúc hoá dữ liệu.

### Cơ chế cưỡng chế (không phải bằng lời nhắc)

1. Mọi JSON Schema đặt `additionalProperties: false`.
2. Có linter chặn tên trường khớp regex:
   `/(recommend|suggest|should|advice|best_|optimal|strategy|bid_|budget|draft|proposed)/i`
3. Không tồn tại field tự do dạng text do model sinh ra trong output contract.

Nếu một yêu cầu buộc phải thêm field vi phạm, đó là dấu hiệu yêu cầu sai — dừng lại và hỏi, đừng thêm field.

---

## 2. Nguyên tắc kiến trúc bất di bất dịch

| Nguyên tắc | Thực thi |
|---|---|
| Layered pipeline | Mỗi tầng chỉ biết tầng liền kề |
| Provenance-first | Mọi giá trị đo được đều có `provenance` |
| Raw is immutable | Payload thô lưu nguyên trạng, không ghi đè, cho phép replay |
| Idempotent runs | Chạy lại cùng `run_id` không sinh dữ liệu trùng |
| Fail-soft | Provider chết → hạ confidence, không sập run |
| No fabrication | Thiếu dữ liệu thì để `null` + ghi lý do. Không bao giờ điền `0` hay `"unknown"` |
| Contract versioning | Mọi output có `schema_version` |

**Collector không bao giờ gọi API trực tiếp.** Nó khai báo nhu cầu theo capability, tầng `providers` chọn nguồn theo `config/providers.yaml`.

---

## 3. Ba nhãn độ tin cậy (chỉ ba, không có nhãn thứ tư)

| Nhãn | Nghĩa |
|---|---|
| `hard` | Lấy trực tiếp từ nguồn có thẩm quyền |
| `estimate` | Ước lượng do nhà cung cấp tính toán |
| `inferred` | Suy ra từ dữ liệu khác trong hệ thống |

Ràng buộc cứng: mọi metric traffic/authority (SimilarWeb, Ahrefs DR, SEMrush AS) **không bao giờ** được gán `hard`. Trần của chúng là `estimate`.

---

## 4. Quy ước đặt tên

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Field JSON | `snake_case` tiếng Anh | `search_volume` |
| Boolean | `is_` / `has_` | `is_branded` |
| Thời gian | `_at`, ISO 8601 UTC | `fetched_at` |
| Đếm | `_count` | `referring_domain_count` |
| Điểm số | `_score`, thang 0–1 | `confidence_score` |
| Country | ISO 3166-1 alpha-2 HOA | `VN` |
| Language | BCP-47 thường | `vi` |
| Market key | `{COUNTRY}-{language}` | `VN-vi` |
| Broker slug | từ domain, gạch ngang | `exness-com` |
| Run ID | `run_{YYYYMMDD}T{HHmm}Z_{broker_slug}` | `run_20260731T0930Z_exness-com` |
| Market run ID | `{run_id}__{market_key}` | `..._exness-com__VN-vi` |
| Class Python | `PascalCase`, adapter hậu tố `Adapter` | `DataForSeoAdapter` |
| Provider ID | `snake_case` cố định | `dataforseo` |

Một khái niệm = một tên duy nhất trong toàn hệ thống. Không tồn tại song song `traffic` / `visits` / `sessions`.

---

## 5. Bảo mật và chi phí

- Credentials CHỈ đọc từ biến môi trường. Không hardcode, không commit, không in ra log:
  `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `AHREFS_API_TOKEN`, `SEMRUSH_API_KEY`
- DataForSEO tính tiền theo query. Trước mỗi run lớn: in bảng ước tính số call + chi phí, chờ xác nhận.
- `dry_run: true` phải chạy được toàn bộ validate + ước tính chi phí mà không gọi API dòng nào.
- Mặc định `freshness_policy: prefer_cache`. TTL theo loại dữ liệu, xem `config/providers.yaml`.

---

## 6. Chuẩn hoá dữ liệu — hai cái bẫy chết người

**Domain:** bắt buộc dùng Public Suffix List, không bao giờ cắt chuỗi bằng regex.
`.com.vn`, `.co.id`, `.co.th`, `.com.my` xuất hiện dày đặc trong thị trường mục tiêu và sẽ phá mọi logic tự viết.

**Tiếng Việt có dấu:** `sàn forex uy tín` và `san forex uy tin` là HAI keyword khác nhau, volume khác nhau, cùng intent.
Lưu cả `keyword_raw` và `keyword_normalized`, thêm cờ `has_diacritics`. Không gộp mù.

---

## 7. Thứ tự hiện thực (bắt buộc theo thứ tự này)

Không xây 12 module rồi mới chạy thử. Xây một lát cắt dọc mỏng trước:

1. `core` — types, provenance, identity, errors
2. `intake` — theo `docs/architecture/phase-02-input-design.md`
3. **Một** adapter duy nhất: `dataforseo`
4. **Một** collector duy nhất: `keyword_research`
5. Chạy end-to-end: 1 broker × 1 market (`VN-vi`), có output JSON hợp lệ
6. Chỉ khi luồng trên thông mới nhân rộng sang adapter và collector còn lại

Lý do: canonical model gần như chắc chắn sai ở lần đầu. Phát hiện lúc có 1 collector rẻ hơn nhiều so với lúc có 6.

---

## 8. Kiểm thử

- Mọi adapter phải có contract test chạy trên fixture đã ghi lại, chạy offline, không tốn quota.
- Fixture đặt tại `tests/fixtures/{provider_id}/{endpoint}.json`.
- Contract test đỏ = nhà cung cấp đổi format. Không được "sửa cho xanh" bằng cách nới lỏng assertion.

---

## 9. Trạng thái dự án

Đã chốt thiết kế: Phase 1–12 (đầy đủ, System Architecture → Scalability).

Mã nguồn: lát cắt dọc đầu tiên đã thông end-to-end offline —
`core/` + `intake/` + `providers/` (DataForSeoAdapter) + `collectors/keyword_research/`,
xuất JSON hợp lệ theo `config/schemas/canonical.v1.json`. Các collector còn lại
(Phase 3, 5, 6, 7, 8) chưa hiện thực; theo mục 7, chỉ nhân rộng sau khi lát cắt được review.

Xem `docs/architecture/README.md` để biết nhật ký quyết định và việc còn lại.
Xem `HANDOFF.md` để biết cách tiếp tục.
