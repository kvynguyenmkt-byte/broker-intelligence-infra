# Phase 2 — Input Design

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Hợp đồng: `config/schemas/input.v1.json`

## 1. Objective

Thiết kế lớp biên duy nhất mà thế giới bên ngoài chạm vào Research Agent:

1. **Rác không lọt vào** — input sai bị chặn tại biên, không bao giờ đến collector.
2. **Chuẩn hoá tuyệt đối** — `Exness`, `exness.com`, `https://www.Exness.com/vn/` quy về đúng một danh tính.
3. **Không suy đoán** — thiếu thông tin thì báo lỗi, tuyệt đối không tự điền.

Input contract là hợp đồng có phiên bản, không phải vài tham số truyền vào hàm.

## 2. Architecture

### 2.1 Sáu chặng xử lý

| Chặng | Việc | Thất bại |
|---|---|---|
| 1. Parse | Đọc JSON, kiểm kiểu | `E_PARSE` |
| 2. Schema validate | Đối chiếu `input.v1.json` | `E_SCHEMA` |
| 3. Normalize | Chuẩn hoá chuỗi, domain, mã vùng | Không fail, chỉ ghi nhận biến đổi |
| 4. Resolve market | Map country+language → location code từng provider | `E_MARKET_UNSUPPORTED` |
| 5. Business validate | Domain sống, market hợp lệ | Cảnh báo hoặc từ chối |
| 6. Materialize | Sinh `run_id`, `market_run_id`, `broker_slug`, plan tác vụ | — |

Chặng 3 và 4 là nơi giá trị thật nằm. Đa số lỗi dữ liệu bắt nguồn từ chuẩn hoá market cẩu thả.

### 2.2 Cấu trúc module

```
intake/
├── request_model.py
├── schema/input.v1.json
├── validators/{syntactic,semantic,policy}.py
├── normalizers/{text,url,locale}.py
├── market_resolver.py
├── identity.py
└── errors.py
```

`intake` không biết gì về collector hay provider, trừ capability matrix — để kiểm tra market có được hỗ trợ không trước khi tốn tiền.

## 3. Required Inputs

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `broker_name` | string | 2–120 ký tự |
| `broker_website` | string | URL hợp lệ |
| `markets[].country` | string | ISO 3166-1 alpha-2 HOA |
| `markets[].language` | string | BCP-47 thường |

`country` và `language` nằm trong `markets[]`, không ở cấp gốc (ADR-006).

## 4. Optional Inputs

| Trường | Mặc định | Mục đích |
|---|---|---|
| `broker_aliases[]` | `[]` | Tên thương hiệu phụ, bản địa hoá |
| `known_competitors[]` | `[]` | Gợi ý mồi, gắn `seed_source: "user"` |
| `excluded_domains[]` | `[]` | Loại trừ domain nội bộ / affiliate của mình |
| `modules[]` | tất cả | Bật/tắt collector để kiểm soát chi phí |
| `depth` | `standard` | `quick` \| `standard` \| `deep` |
| `max_competitors` | `20` | Trần Phase 3, cứng tối đa 50 |
| `freshness_policy` | `prefer_cache` | `force_refresh` \| `prefer_cache` \| `cache_only` |
| `cost_ceiling` | `null` | Vượt thì dừng trước khi gọi API |
| `dry_run` | `false` | Validate + ước tính chi phí, không gọi API |
| `provider_overrides` | `{}` | Ép provider cho một capability |
| `schema_version` | `1.0.0` | Phiên bản hợp đồng client mong đợi |
| `requested_by` | `null` | Audit |
| `notes` | `null` | Ghi chú tự do, **không bao giờ** vào dataset |

`cost_ceiling`, `freshness_policy` và `dry_run` là ba công cụ duy nhất ngăn một run vô tình đốt hết quota.

`compliance_context` không phải trường dữ liệu — nó nằm trong `modules[]` như collector bình thường (ADR-007).

## 5. Validation Rules

### 5.1 Cú pháp (từ chối cứng)

`E_REQUIRED_MISSING` · `E_TYPE` · `E_COUNTRY_INVALID` · `E_LANGUAGE_INVALID` · `E_URL_INVALID` · `E_MARKETS_EMPTY` · `E_MARKETS_LIMIT` (>20) · `E_SCHEMA_VERSION`

### 5.2 Ngữ nghĩa

| Luật | Mức | Hành vi |
|---|---|---|
| Domain không phân giải DNS | Cảnh báo | Chạy tiếp, `domain_reachable: false` |
| Domain trả 4xx/5xx | Cảnh báo | Chạy tiếp, hạ confidence landing page |
| Cặp country+language bất thường | Cảnh báo | `market_plausibility: low` |
| Market không provider nào hỗ trợ | Từ chối market | `E_MARKET_UNSUPPORTED`, market khác vẫn chạy |
| `broker_name` không có trên website | Cảnh báo | `brand_match: unverified` |
| Trùng market sau chuẩn hoá | Tự sửa | Dedup + log |
| Chi phí ước tính > `cost_ceiling` | Từ chối run | `E_COST_CEILING` + bảng chi phí |

Nguyên tắc phân mức: chỉ từ chối khi tiếp tục sẽ tạo **dữ liệu sai**. Nếu chỉ tạo **dữ liệu yếu**, hãy chạy và hạ điểm tin cậy. Từ chối quá tay khiến người dùng học cách bỏ qua validation.

## 6. Normalization Rules

### 6.1 Chuỗi
Unicode NFKC, trim, gộp khoảng trắng, loại ký tự vô hình. `broker_name` giữ chữ hoa gốc để hiển thị, sinh song song `broker_name_normalized` dạng casefold để so khớp.

### 6.2 Domain

```
Input:  https://WWW.Exness.com/vn/trading/?utm_source=x#top
  → hạ chữ thường host → bỏ w3 → IDN punycode
  → tách registrable domain bằng Public Suffix List
  → bỏ query, fragment, tracking
Kết quả:
  broker_domain        = "exness.com"
  broker_url_canonical = "https://exness.com/"
  broker_url_original  = "https://WWW.Exness.com/vn/trading/?utm_source=x#top"
```

Bắt buộc dùng Public Suffix List. `co.uk`, `com.vn`, `co.id` sẽ phá mọi logic cắt chuỗi thủ công, và ba đuôi này xuất hiện dày đặc trong thị trường mục tiêu.

### 6.3 Market

```
country:  "vn" | "Vietnam" | "VNM"      → "VN"
language: "VI" | "vi-VN" | "Vietnamese" → "vi"
market_key = "VN-vi"
```

`market_key` là khoá cache, khoá thư mục, khoá dedup. Một chuẩn duy nhất, không ngoại lệ.

### 6.4 Danh tính sinh ra

```
broker_slug   = slugify(broker_domain)              → "exness-com"
run_id        = run_{YYYYMMDD}T{HHmm}Z_{broker_slug}
market_run_id = {run_id}__{market_key}
```

`run_id` không chứa market, `market_run_id` chứa. Đây là điều cho phép một market fail mà run vẫn tiếp tục.

## 7. Error Handling

```json
{
  "error_code": "E_MARKET_UNSUPPORTED",
  "severity": "error",
  "field_path": "markets[2].country",
  "received": "XK",
  "message": "Không provider nào hỗ trợ market này.",
  "remediation": "Bỏ market XK hoặc bổ sung provider hỗ trợ.",
  "is_retryable": false
}
```

`remediation` là bắt buộc. Thông báo lỗi không nói được cách sửa là thông báo lỗi chưa hoàn thành.

Chiến lược: trả **toàn bộ** lỗi một lượt, không dừng ở lỗi đầu. Lỗi cấp market cô lập trong market đó. Lỗi cấp run chặn trước khi gọi API dòng nào. Run bị từ chối vẫn ghi audit log.

## 8. Example Payload

Tối thiểu:

```json
{
  "schema_version": "1.0.0",
  "broker_name": "Exness",
  "broker_website": "https://www.exness.com",
  "markets": [{ "country": "VN", "language": "vi" }]
}
```

Sau chuẩn hoá (nội bộ, không phải hợp đồng đối ngoại):

```json
{
  "run_id": "run_20260731T0930Z_exness-com",
  "broker": {
    "broker_slug": "exness-com",
    "broker_name": "Exness",
    "broker_name_normalized": "exness",
    "broker_domain": "exness.com",
    "broker_url_canonical": "https://exness.com/",
    "domain_reachable": true,
    "brand_match": "verified"
  },
  "market_runs": [{
    "market_run_id": "run_20260731T0930Z_exness-com__VN-vi",
    "market_key": "VN-vi",
    "provider_locations": {
      "dataforseo": { "location_code": 1028581, "language_code": "vi" },
      "ahrefs": { "country": "vn" },
      "google_trends": { "geo": "VN" }
    },
    "status": "ready"
  }],
  "estimated_cost": { "currency": "USD", "amount": 18.4, "api_calls": 214 }
}
```

Khối `provider_locations` là lý do tồn tại của `market_resolver`. DataForSEO dùng `location_code` dạng số, Ahrefs dùng mã nước, Google Trends dùng `geo`. Nếu mỗi collector tự map, sáu tháng sau bạn sẽ có ba bảng map lệch nhau.

## 9. Edge Cases

| Tình huống | Xử lý |
|---|---|
| Broker nhiều domain theo vùng | Nhận domain chính; vùng lưu ở aliases, Phase 3 phát hiện thêm |
| Website redirect sang domain khác | Đi theo redirect, dùng đích cuối, ghi cả chuỗi redirect |
| Tên thương hiệu khác website (mua lại) | `brand_match: unverified`, chạy tiếp |
| Nước đa ngôn ngữ (MY: ms/en/zh) | Khai báo nhiều market riêng, không gộp |
| Broker offshore không hiện diện bản địa | Vẫn chạy, `compliance_context` ghi nhận |
| Tên broker trùng thương hiệu khác ngành | Dùng domain làm định danh gốc |
| Ký tự đặc biệt / phi Latin | NFKC + punycode, giữ bản gốc để hiển thị |
| Provider hết quota giữa run | Market chuyển `partial`, không phải `failed` |
| Chạy lại trong ngày | `freshness_policy` quyết định |
| Competitor gợi ý không tồn tại | Không từ chối, đánh dấu `seed_validated: false` |

## 10. Reasoning

**Vì sao chỉ 4 trường bắt buộc?** Mọi trường bắt buộc thêm vào là một rào cản sử dụng và một cơ hội nhập sai. Thứ gì agent tự khám phá được thì không hỏi người dùng.

**Vì sao `markets[]`?** Ngoài lý do chi phí, nó buộc thiết kế đa thị trường ngay từ ngày đầu. Bắt đầu bằng một market sẽ để lại đầy giả định ngầm về "market hiện tại", gỡ ra sau rất đắt.

**Vì sao gợi ý competitor vẫn phải kiểm chứng?** Tin tuyệt đối là cho input quyền ghi thẳng vào dataset không qua provenance — phá nguyên tắc lõi.

**Vì sao `notes` không vào dataset?** Nó là văn bản tự do do người viết, có thể chứa nhận định. Cho vào là mở cửa hậu cho khuyến nghị lọt vào output.

## 11. Advantages

Rào cản sử dụng thấp · chi phí kiểm soát trước khi gọi API · lỗi trả một lượt kèm cách sửa · một market hỏng không sập run · chuẩn hoá tập trung nên cache hit cao · hợp đồng có phiên bản.

## 12. Disadvantages

`market_resolver` cần bảng ánh xạ location từng provider, bảo trì thủ công · Public Suffix List là phụ thuộc ngoài, cần cập nhật định kỳ · ước tính chi phí luôn có sai số · tách `run_id`/`market_run_id` làm checkpoint phức tạp hơn · kiểm tra domain sống thêm độ trễ ở biên.

## 13. Tradeoffs

| Quyết định | Lựa chọn khác | Vì sao chọn |
|---|---|---|
| `markets[]` | Một market/run | Tái dùng dữ liệu cấp broker, tiết kiệm API |
| Trả hết lỗi một lượt | Fail-fast | Trải nghiệm sửa lỗi tốt hơn nhiều |
| Cảnh báo với domain chết | Từ chối | Broker mới / đang bảo trì vẫn nghiên cứu được |
| `broker_slug` từ domain | Từ tên | Domain là định danh duy nhất, tên thì trùng |
| `compliance_context` là module | Trường input | Không nhận dữ liệu chưa kiểm chứng |
| Trần 20 market | Không giới hạn | Bảo vệ thời gian chạy và checkpoint |

## 14. Best Practice

- Viết `input.v1.json` trước, sinh code model từ schema, không làm ngược
- Chuẩn hoá domain bằng Public Suffix List, không bao giờ bằng regex tự viết
- Luôn giữ song song giá trị gốc và giá trị chuẩn hoá
- Mặc định `prefer_cache`, in chi phí trước mọi run
- Test biên bằng bảng edge case, đặc biệt `.com.vn` và `.co.id`
- Không nhận credentials qua payload
- Ghi audit log cả run bị từ chối

## 15. Common Mistakes

1. Cắt domain bằng chuỗi thay vì PSL
2. Ghi đè giá trị gốc bằng giá trị chuẩn hoá
3. Fail-fast ở lỗi đầu tiên
4. Cho phép `country` dạng tên đầy đủ mà không chuẩn hoá
5. Tin `known_competitors[]` vô điều kiện
6. Không kiểm tra market có provider hỗ trợ
7. Nhét market vào `run_id`
8. Quên `schema_version`
9. Gộp nước đa ngôn ngữ thành một market
10. Cho `notes` chảy vào dataset

## 16. Checklist

- [x] Xác nhận `markets[]`
- [x] Xác nhận `compliance_context` là module
- [x] Chốt 4 trường bắt buộc, 13 trường tuỳ chọn
- [x] Chốt chuẩn hoá domain bằng PSL
- [x] Chốt `market_key = {COUNTRY}-{language}`
- [x] Chốt công thức `run_id` và `market_run_id`
- [x] Chốt bảng mã lỗi và mức độ
- [x] Chốt trả toàn bộ lỗi một lượt
- [x] Chốt `freshness_policy: prefer_cache` + TTL theo loại (ADR-008)
- [x] Chốt trần 20 market / 50 competitor gợi ý (ADR-009)
- [x] Chốt bổ sung `dry_run` (ADR-010)
- [x] Viết `config/schemas/input.v1.json`
