# Phase 10 — Validation

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Module: `validate`

## 1. Objective

Cổng chất lượng cuối trước khi dataset rời hệ thống. Ba yêu cầu cứng:

1. **Phát hiện, không sửa** — `validate` chỉ ra lỗi, KHÔNG bao giờ tự sửa dữ liệu sai (Phase 1 mục 2.3). Sửa lặng lẽ là cách dữ liệu bẩn sống sót.
2. **Cưỡng chế mandate** — không field khuyến nghị, không text tự do do model sinh.
3. **Toàn vẹn tham chiếu** — mọi ID tham chiếu phải trỏ tới entity tồn tại.

## 2. Architecture

### 2.1 Ba lớp kiểm định

```
1. Schema validation   đối chiếu canonical.v1.json (Draft 2020-12)
2. Business rules       luật nghiệp vụ trên dữ liệu đã hợp lệ cấu trúc
3. QA gate              ngưỡng chất lượng tổng thể → pass | warn | block
```

### 2.2 Business rules (mẫu, tất cả tái lập)

| Luật | Vi phạm |
|---|---|
| `Measurement.value = null` phải kèm `missing_reason` | `E_FABRICATION_GUARD` |
| Traffic/authority không được `reliability: hard` | `E_RELIABILITY_CAP` |
| Mọi metric có mặt phải có `provenance` | `E_PROVENANCE_MISSING` |
| ID tham chiếu (`cluster_id`, `keyword_id`, `landing_page_id`, `ad_id`, `competitor_id`) trỏ tới entity tồn tại | `E_DANGLING_REF` |
| `overlap_score` tính trên tập đã loại `is_branded` | `E_BRAND_LEAK` |
| Tên trường khớp regex khuyến nghị | `E_MANDATE_FIELD` |
| `market_key` khớp `{COUNTRY}-{language}` | `E_MARKET_KEY_FORMAT` |

### 2.3 QA gate — ngưỡng, không phán xét

QA gate tính chỉ số khách quan theo run/market và so ngưỡng cấu hình:

| Chỉ số | Ý nghĩa |
|---|---|
| `missing_ratio` | tỉ lệ `Measurement` khuyết |
| `low_agreement_ratio` | tỉ lệ metric `low_agreement` |
| `biased_source_ratio` | tỉ lệ nguồn `is_biased_source` |
| `market_coverage` | số market có dữ liệu / số market yêu cầu |

Kết quả gate: `block` (dữ liệu sai cấu trúc hoặc tham chiếu gãy), `warn` (chất lượng yếu nhưng dùng được), `pass`. Gate không sinh nhận định, chỉ so ngưỡng.

### 2.4 Báo cáo, không biến đổi

`validate` xuất một `ValidationReport` (danh sách vi phạm + chỉ số QA) tách khỏi dataset. Dataset không bị chỉnh; run bị `block` vẫn ghi audit log.

## 3. Reasoning

**Vì sao không sửa?** Sửa tự động che mất nguyên nhân gốc và tạo dữ liệu không nguồn. Trả lỗi kèm vị trí để tầng phát sinh (collector/normalize) sửa đúng chỗ.

**Vì sao tách QA gate khỏi business rules?** Business rules là đúng/sai nhị phân; QA gate là chất lượng theo ngưỡng. Gộp lại làm mờ ranh giới "sai" và "yếu".

**Vì sao kiểm tham chiếu?** Output quan hệ (ADR-017) chỉ đúng nếu mọi ID trỏ tới thật; một `cluster_id` gãy làm hỏng mọi agent join phía sau.

## 4. Advantages

- Dữ liệu bẩn bị chặn ở cổng, không lặng lẽ chảy ra.
- Mandate được kiểm mỗi run, không chỉ lúc viết schema.
- `ValidationReport` cho biết chính xác cần sửa gì ở đâu.

## 5. Disadvantages

- Validation chặt có thể `block` run gần-đủ-tốt, cần chỉnh ngưỡng.
- Kiểm tham chiếu toàn cục tốn bộ nhớ ở dataset lớn.
- Ngưỡng QA cần hiệu chỉnh theo vertical/market.

## 6. Tradeoffs

| Vị trí kiểm | A. Tại output (cổng cuối) | B. Tại mỗi write | C. Ngoài luồng (offline) |
|---|---|---|---|
| Bắt lỗi sớm | Trung bình | Cao | Thấp |
| Chi phí | Thấp | Cao | Thấp |
| Chặn được rác ra ngoài | Cao | Cao | Không |

**Xếp hạng: A > B > C.** A là cổng bắt buộc rẻ và đủ chặn rác ra ngoài; bổ sung vài luật rẻ tại write (B) cho phản hồi sớm. C hữu ích để giám sát nhưng không chặn được nên không thay được A.

| Chính sách gate | Fail-closed (block khi nghi ngờ) | Fail-open (warn, vẫn ra) |
|---|---|---|
| Chọn | Lỗi cấu trúc / tham chiếu gãy | Chất lượng yếu (missing/low_agreement) |

Nguyên tắc kế thừa Phase 2: chỉ `block` khi tiếp tục tạo **dữ liệu sai**; chỉ **yếu** thì `warn` và hạ confidence.

## 7. Best Practice

- Không bao giờ sửa dữ liệu trong `validate`; chỉ báo cáo.
- Chạy linter mandate như một luật validation, không chỉ như test.
- Kiểm toàn vẹn tham chiếu cho mọi `*_id`.
- Ngưỡng QA để ở config, không hardcode.
- Ghi audit cả run bị `block`.

## 8. Common Mistakes

1. "Sửa cho xanh" bằng cách điền giá trị mặc định.
2. Gộp business rule và QA gate làm một.
3. Bỏ kiểm tham chiếu → ID gãy lọt ra ngoài.
4. Nới lỏng assertion để qua gate thay vì sửa nguồn.
5. Chặn run vì dữ liệu chỉ *yếu* (nên `warn`).
6. Ngưỡng QA hardcode, không chỉnh được theo market.

## 9. Checklist

- [x] Chốt `validate` chỉ phát hiện, không sửa (ADR-018)
- [x] Chốt ba lớp: schema / business rules / QA gate
- [x] Chốt kiểm toàn vẹn tham chiếu `*_id`
- [x] Chốt linter mandate là một luật validation
- [x] Chốt phân biệt `block` (sai) và `warn` (yếu)
- [x] Chốt `ValidationReport` tách khỏi dataset, audit run bị block
- [ ] Hiện thực module `validate` — khi tới lượt theo mục 7
