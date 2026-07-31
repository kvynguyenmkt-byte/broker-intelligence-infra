# Phase 1 — System Architecture

Trạng thái: ✅ Chốt · Ngày: 2026-07-31

## 1. Objective

Thiết kế khung kiến trúc với ba đặc tính bắt buộc:

1. **Deterministic collection** — cùng input cho ra dataset cùng cấu trúc, kèm dấu vết nguồn gốc từng trường.
2. **Provider-agnostic** — thêm/bớt nhà cung cấp không chạm logic nghiệp vụ.
3. **Interpretation-free** — mọi hành vi khuyến nghị bị chặn ở tầng kiến trúc, không phải bằng lời nhắc.

Điểm 3 quan trọng nhất. Cấm bằng prompt sẽ bị lách; cấm bằng schema thì không. Output contract không có field nào chứa được khuyến nghị — không có chỗ chứa thì không có chỗ bịa.

## 2. Architecture

### 2.1 Nguyên tắc nền tảng

| Nguyên tắc | Thực thi |
|---|---|
| Layered pipeline | Mỗi tầng chỉ biết tầng liền kề, giao tiếp qua data contract |
| Provenance-first | Mọi giá trị có `source`, `fetched_at`, `reliability` |
| Raw is immutable | Payload thô lưu nguyên trạng, không ghi đè |
| Idempotent runs | Chạy lại một `run_id` không tạo dữ liệu trùng |
| Fail-soft | Một provider chết không sập run, chỉ hạ confidence |
| Contract versioning | Output có `schema_version` |

### 2.2 Bảy tầng

```
Lớp tiếp nhận            Hợp đồng đầu vào, chuẩn hoá thị trường
        ↓
Bộ điều phối tác vụ      DAG, retry, checkpoint, idempotent
        ↓
Trừu tượng nhà cung cấp  Adapter, fallback, cache, quota
        ↓
Lớp thu thập             Sáu collector nghiệp vụ độc lập
        ↓
Chuẩn hoá và hợp nhất    Dedup, provenance, độ tin cậy
        ↓
Kiểm định chất lượng     Schema, luật nghiệp vụ, QA gate
        ↓
Lưu trữ và hợp đồng ra   Snapshot, versioning, JSON API
```

Điểm mấu chốt: tầng thu thập không bao giờ gọi thẳng API. Nó khai báo "cần keyword metrics cho market VN-vi", tầng trừu tượng quyết định gọi DataForSEO trước, Ahrefs sau, SEMrush cuối. Đây là thứ cho phép scale lên hàng trăm broker mà không viết lại nghiệp vụ.

### 2.3 Module và trách nhiệm

| Module | Trách nhiệm duy nhất | Không được làm |
|---|---|---|
| `core` | Kiểu dữ liệu, provenance, ID, lỗi, logging, cấu hình | Gọi mạng |
| `intake` | Nhận, validate, normalize input; phân giải market | Suy đoán thị trường thiếu |
| `providers` | Adapter + capability matrix + rate limit + cache + retry | Hiểu nghiệp vụ forex |
| `collectors` | 6 module nghiệp vụ + `compliance_context` | Chọn provider |
| `normalize` | Map payload thô → canonical model | Loại bỏ dữ liệu |
| `resolve` | Dedup, entity resolution, merge, chấm confidence & freshness | Bịa giá trị thiếu |
| `validate` | Schema validation, business rules, QA gate | Sửa dữ liệu sai |
| `storage` | Raw store, normalized store, snapshot registry, cache | Biến đổi dữ liệu |
| `output` | Lắp ráp dataset cuối, export, quản lý `schema_version` | Thêm nhận định |
| `orchestration` | DAG, phụ thuộc, checkpoint, resume, song song hoá | Chứa logic nghiệp vụ |
| `observability` | Metrics, cost meter, audit log, run report | Ảnh hưởng kết quả |
| `compliance_context` | Dữ kiện pháp lý & chính sách quảng cáo tài chính theo market | Tư vấn pháp lý |

### 2.4 Cấu trúc thư mục

```
research-agent/
├── CLAUDE.md
├── config/
│   ├── settings.yaml
│   ├── providers.yaml
│   ├── source_priority.yaml
│   ├── markets.yaml
│   └── schemas/{input,canonical,output}.v1.json
├── src/research_agent/
│   ├── core/          {types,provenance,identity,errors,logging}.py
│   ├── intake/        request_model.py validators/ normalizers/ market_resolver.py
│   ├── providers/     base.py registry.py rate_limiter.py cache.py cost_meter.py impl/
│   ├── collectors/    competitor_discovery/ keyword_research/ serp_research/
│   │                  landing_page_discovery/ ad_intelligence/
│   │                  competitor_intelligence/ compliance_context/
│   ├── normalize/
│   ├── resolve/       deduplicator.py entity_resolver.py merger.py confidence.py freshness.py
│   ├── validate/  storage/  output/  orchestration/  observability/
├── data/
│   ├── raw/<broker_slug>/<market>/<run_id>/
│   ├── normalized/<broker_slug>/<market>/<run_id>/
│   ├── snapshots/<broker_slug>/<market>/<snapshot_id>.json
│   └── cache/
└── tests/{unit,contract,fixtures}/
```

`tests/contract/` và `tests/fixtures/` là thứ khiến hệ thống sống lâu. Khi nhà cung cấp đổi format response, contract test đỏ ngay thay vì để dữ liệu rác lặng lẽ chảy vào dataset.

### 2.5 Quy ước đặt tên

Xem `CLAUDE.md` mục 4. Quy tắc gốc: một khái niệm chỉ có đúng một tên trong toàn hệ thống. Từ điển tên nằm ở `config/schemas/canonical.v1.json`, mọi module đọc từ đó.

### 2.6 Bảy thành phần tái sử dụng

1. `ProviderAdapter` — interface thống nhất: `capabilities()`, `fetch()`, `cost_estimate()`, `health()`
2. `FetchEnvelope` — vỏ bọc mọi kết quả gọi API: payload thô + metadata + trạng thái
3. `Provenance` — gắn vào từng trường
4. `SourcePriorityMerger` — khi hai nguồn mâu thuẫn, chọn theo cấu hình và **ghi lại xung đột**
5. `ConfidenceScorer` / `FreshnessScorer` — hai điểm độc lập
6. `Deduplicator` — chuẩn hoá khoá tự nhiên rồi hash
7. `CostMeter` — đếm call và chi phí, in trước khi chạy

Envelope tối thiểu:

```json
{
  "value": 12100,
  "unit": "monthly_searches",
  "provenance": {
    "provider_id": "dataforseo",
    "endpoint": "keywords_data/google_ads/search_volume",
    "fetched_at": "2026-07-31T09:30:00Z",
    "reliability": "hard",
    "conflicts": []
  }
}
```

## 3. Reasoning

**Vì sao phân tầng?** Rủi ro lớn nhất không phải hiệu năng mà là dữ liệu bẩn lan truyền. Khi thu thập và chuẩn hoá trộn lẫn, một thay đổi nhỏ ở API sẽ làm hỏng dataset mà không ai phát hiện.

**Vì sao tầng trừu tượng bắt buộc?** Yêu cầu "tool này thiếu thì dùng tool khác" chính là fallback chain. Rải rác trong code nghiệp vụ, nó thành ác mộng ở broker thứ 30.

**Vì sao raw bất biến?** Vì bạn sẽ đổi ý về cách chuẩn hoá. Giữ raw cho phép replay với logic mới mà không tốn thêm đồng API nào.

**Vì sao tách confidence và freshness?** Gộp là mất thông tin, agent phía sau không ra quyết định đúng được.

## 4. Advantages

- Thêm provider = một file adapter + một dòng config
- Thêm collector mới (Meta Ads, TikTok Ads) = một thư mục, tái dùng toàn bộ lõi
- Chạy lại và resume được, run lỗi không tốn lại tiền API
- Kiểm toán được: mọi con số truy ngược về một lời gọi API cụ thể
- Kiểm soát chi phí từ kiến trúc, không phải vá sau
- Song song hoá tự nhiên theo broker và market
- Test offline bằng fixture, phát triển không đốt quota

## 5. Disadvantages

- Chi phí khởi tạo cao: 12 module trước khi thấy dòng dữ liệu đầu tiên
- Nhiều lớp gián tiếp, debug đường đi một trường cần đọc qua vài tầng
- Canonical model là điểm nghẽn, đổi nó là đổi nhiều nơi
- Lưu raw tốn dung lượng, cần chính sách retention sớm
- Tầng trừu tượng có thể che tính năng đặc thù mạnh của một provider
- Với 1–2 broker, đây là over-engineering. Chỉ trả lãi từ khoảng broker thứ 10

## 6. Tradeoffs

| | A. Đơn khối | B. Modular + abstraction | C. Microservices + event bus |
|---|---|---|---|
| Thời gian ra bản đầu | 1–2 tuần | 4–6 tuần | 10–14 tuần |
| Chi phí thêm provider | Cao | Rất thấp | Thấp |
| Chi phí vận hành | Rất thấp | Thấp | Cao |
| Scale 100+ broker | Kém | Tốt | Rất tốt |
| Độ dễ debug | Tốt đầu, tệ sau | Tốt | Khó |
| Phù hợp đội nhỏ | Có | Có | Không |

**Xếp hạng: B > C > A.** B đạt gần hết lợi ích của C với một phần nhỏ chi phí vận hành, và nâng cấp B → C sau này chỉ là thay lời gọi hàm bằng message queue. C thua vì chưa có tải để biện minh — xây event bus khi chưa biết collector nào là nút thắt là tối ưu hoá mù. A bị loại vì mâu thuẫn trực tiếp với yêu cầu hàng trăm broker.

## 7. Best Practice

- Viết `canonical.v1.json` trước khi viết dòng collector đầu tiên
- Mọi adapter có contract test chạy offline trên fixture
- Credentials chỉ từ biến môi trường
- In ước tính chi phí trước mỗi run lớn, chờ xác nhận
- Trường quan trọng cần ≥2 nguồn độc lập; xung đột ghi vào `conflicts`
- Đánh dấu nguồn thiên lệch: site review broker hầu hết do affiliate viết, gắn cờ `biased_source`
- Ghi `schema_version` từ ngày đầu
- Một collector = một trách nhiệm. Tên module cần chữ "and" là đang làm hai việc

## 8. Common Mistakes

1. Gọi API trực tiếp trong collector
2. Chuẩn hoá ngay lúc fetch, không giữ raw
3. Điền `0` hoặc `"unknown"` cho dữ liệu thiếu
4. Trộn confidence với freshness
5. Đặt tên khác nhau cho cùng khái niệm giữa các module
6. Để agent nhận xét trong field mô tả
7. Bỏ qua chuẩn hoá market → cache miss và phân mảnh
8. Không có rate limiter → bị chặn giữa run
9. Không versioning output → agent phía sau vỡ
10. Dedup theo chuỗi thô thay vì khoá đã chuẩn hoá

## 9. Checklist

- [x] Chốt phương án kiến trúc B
- [x] Chốt 12 module và ranh giới trách nhiệm
- [x] Chốt cấu trúc thư mục
- [x] Chốt quy ước đặt tên
- [x] Chốt 3 nhãn reliability
- [x] Chốt raw bất biến
- [x] Chốt tách confidence / freshness
- [x] Chốt thêm `compliance_context`
- [x] Chốt cấm khuyến nghị bằng schema
- [x] Chốt biến môi trường cho credentials
- [ ] Chốt runtime triển khai (đề xuất Python 3.11+) — xác nhận khi bắt đầu code
