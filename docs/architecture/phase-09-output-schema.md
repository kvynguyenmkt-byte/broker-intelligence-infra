# Phase 9 — Output Schema

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Hợp đồng: `config/schemas/canonical.v1.json` (JSON Schema 2020-12)

## 1. Objective

Chốt hợp đồng đầu ra duy nhất mà mọi agent phía sau tiêu thụ. Bốn yêu cầu cứng:

1. **Quan hệ, không lồng** — tham chiếu chéo bằng ID, không nhúng trùng dữ liệu.
2. **Dùng chung `Measurement` và `Provenance`** — mọi entity chia sẻ đúng hai vật này.
3. **Cấm khuyến nghị bằng schema** — `additionalProperties: false` khắp nơi, không field text tự do do model sinh, linter chặn tên trường khuyến nghị.
4. **Có phiên bản** — `schema_version` bắt buộc.

## 2. Architecture

### 2.1 Bảy entity + tiền tố ID

| Entity | ID | Phase |
|---|---|---|
| `Competitor` | `cmp_` | 3 |
| `Keyword` | `kw_` | 4 |
| `KeywordCluster` | `clu_` | 4 |
| `SerpSnapshot` | `srp_` | 5 |
| `LandingPage` | `lp_` | 6 |
| `Ad` | `ad_` | 7 |
| `CompetitorProfile` | `prf_` | 8 |

ID tất định sinh bằng `core.identity.entity_id(prefix, *parts)` — cùng khoá tự nhiên → cùng ID → dedup và tham chiếu ổn định.

### 2.2 Gốc dataset

```
{
  schema_version   (bắt buộc)
  run_id, generated_at
  competitors[] keywords[] keyword_clusters[]
  serp_snapshots[] landing_pages[] ads[] competitor_profiles[]
}
```

Các mảng entity là **tuỳ chọn** ở gốc: một dataset bộ phận (chỉ keyword) vẫn hợp lệ — nhất quán triết lý fail-soft. Thiếu dữ liệu thì vắng mặt, không bịa.

### 2.3 Hai vật dùng chung

- `Measurement`: `value`, `unit`, `provenance`, `missing_reason`, và (đa nguồn) `values_by_source[]`, `divergence_ratio`, `low_agreement`.
- `Provenance`: `provider_id`, `endpoint`, `fetched_at`, `reliability` ∈ `{hard, estimate, inferred}`, `is_biased_source`, `conflicts[]`.

Entity dạng metric (Keyword, Competitor, CompetitorProfile) dùng `Measurement` theo từng trường. Entity dạng observed snapshot (SerpSnapshot, LandingPage, Ad) mang `Provenance` cấp entity, các trường là quan sát dưới provenance đó.

### 2.4 Cưỡng chế mandate

1. `additionalProperties: false` ở mọi object.
2. Linter (`tests/unit/test_schema_mandate.py`) chặn tên trường khớp `/(recommend|suggest|should|advice|best_|optimal|strategy|bid_|budget|draft|proposed)/i`.
3. Không field text tự do do model sinh: mọi chuỗi quan sát mang hậu tố `_observed` và có provenance.

## 3. Reasoning

**Vì sao quan hệ, không lồng?** Nhúng trùng (một keyword lặp trong nhiều SERP) làm dữ liệu phình và mâu thuẫn khi cập nhật. Tham chiếu ID giữ một nguồn sự thật cho mỗi entity.

**Vì sao entity mảng tuỳ chọn?** Run bộ phận (một market fail, một module tắt) vẫn phải xuất được dataset hợp lệ. Bắt buộc mọi mảng là ép bịa dữ liệu thiếu.

**Vì sao cưỡng chế bằng schema, không prompt?** Prompt bị lách; `additionalProperties:false` + linter thì không. Không có chỗ chứa khuyến nghị thì không có chỗ bịa.

## 4. Advantages

- Một nguồn sự thật cho mỗi entity, cập nhật không mâu thuẫn.
- Dataset bộ phận vẫn hợp lệ và dùng được.
- Mandate được cưỡng chế cơ học, không phụ thuộc kỷ luật người viết.
- Có phiên bản: agent phía sau không vỡ khi schema tiến hoá.

## 5. Disadvantages

- Người đọc phải join theo ID thay vì đọc cây lồng.
- Canonical là điểm nghẽn: đổi nó là đổi nhiều nơi.
- Mảng tuỳ chọn đẩy việc kiểm tra "đủ dữ liệu chưa" sang tầng validate (Phase 10).

## 6. Tradeoffs

| Mô hình output | A. Quan hệ + ID | B. Lồng cây | C. Bảng phẳng |
|---|---|---|---|
| Không trùng lặp | Cao | Thấp | Trung bình |
| Dễ cập nhật | Cao | Thấp | Trung bình |
| Dễ đọc trực tiếp | Trung bình | Cao | Cao |

**Xếp hạng: A > C > B.** A không trùng và dễ cập nhật — quan trọng nhất khi replay và merge nhiều nguồn. C dễ đọc nhưng lặp dữ liệu. B dễ đọc nhất nhưng nhân bản và mâu thuẫn khi cập nhật, hỏng ở quy mô nhiều broker.

## 7. Best Practice

- Viết `canonical.v1.json` trước collector; sinh code từ schema, không ngược.
- Tham chiếu ID, không nhúng entity khác.
- Mọi metric qua `Measurement`; thiếu thì `null` + `missing_reason`.
- `schema_version` từ ngày đầu; đổi phá vỡ thì tăng major.
- Giữ linter mandate xanh như một cổng CI.

## 8. Common Mistakes

1. Nhúng trùng entity thay vì tham chiếu ID.
2. Tạo `Measurement` song song khác nhau giữa module.
3. Thêm field text tự do do model sinh.
4. Bỏ `additionalProperties: false` ở một object con.
5. Đặt tên trường mang tính khuyến nghị (bị linter chặn).
6. Bắt buộc mọi mảng entity → ép bịa dữ liệu thiếu.
7. Quên `schema_version`.

## 9. Checklist

- [x] Chốt bảy entity và tiền tố ID (ADR-017)
- [x] Chốt dùng chung `Measurement` / `Provenance`
- [x] Chốt tham chiếu chéo bằng ID, không lồng trùng
- [x] Chốt mảng entity tuỳ chọn ở gốc (fail-soft)
- [x] Chốt `additionalProperties:false` khắp nơi + linter mandate
- [x] Chốt không field text tự do do model sinh
- [x] Viết `config/schemas/canonical.v1.json` thật (JSON Schema 2020-12)
- [x] Contract test xác nhận keyword dataset validate với schema
