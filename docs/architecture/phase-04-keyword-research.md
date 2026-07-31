# Phase 4 — Keyword Research

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `Keyword` (`kw_`), `KeywordCluster` (`clu_`)
Lát cắt tối thiểu đã hiện thực: `src/research_agent/collectors/keyword_research/`.

## 1. Objective

Thu thập, chuẩn hoá và cấu trúc hoá keyword theo từng market, phục vụ Phase 5 (SERP) và các agent phía sau. Bốn yêu cầu cứng:

1. **Giữ biến thể có dấu/không dấu tách biệt** — `sàn forex uy tín` và `san forex uy tin` là hai keyword khác nhau, volume khác nhau, cùng intent (CLAUDE.md mục 6).
2. **Intent gồm `trust_check`** — bên cạnh bốn intent kinh điển, nhóm "scam / lừa đảo / uy tín / có nên" có volume rất lớn và hành vi khác hẳn commercial.
3. **Đo lường có provenance** — mọi metric là `Measurement`; thiếu thì `null` + `missing_reason`, không bịa 0.
4. **Cụm bằng cấu trúc** — không gắn nhãn cụm bằng prose do model sinh.

## 2. Architecture

### 2.1 Luồng

```
seed keywords + broker/aliases
  → fetch capability keyword_volume/cpc/competition (providers chọn nguồn)
  → parse → KeywordMetricRow (provider-agnostic)
  → normalize: keyword_raw, keyword_normalized (NFKC+casefold), has_diacritics
  → gắn is_branded (khớp cả khi bỏ dấu)
  → measurement search_volume / cpc / competition_index / keyword_trend
  → (enrichment) intent, cluster_id
```

### 2.2 Metric và reliability

| Field | Unit | Reliability | Nguồn ưu tiên (`source_priority.yaml`) |
|---|---|---|---|
| `search_volume` | `monthly_searches` | `hard` | google_keyword_planner → dataforseo → ahrefs → semrush |
| `cpc` | `usd` | `hard` | google_keyword_planner → dataforseo → semrush → ahrefs |
| `competition_index` | `index_0_100` | `hard` | google_keyword_planner → dataforseo → semrush |
| `keyword_trend` | `index_0_100` | `estimate` | google_trends → dataforseo |

`keyword_trend` bị trần `estimate` — Google Trends là chỉ số tương đối 0–100, không phải volume tuyệt đối.

### 2.3 Intent bằng lexicon theo market

`intent` ∈ `{informational, navigational, commercial, transactional, trust_check}`, gán bằng **lexicon theo ngôn ngữ** (`intent_method: lexicon`), không bằng phán đoán tự do:

| Intent | Tín hiệu mẫu (VN) |
|---|---|
| `trust_check` | lừa đảo, scam, uy tín, có nên, review, đánh giá |
| `transactional` | mở tài khoản, nạp tiền, đăng ký, rút tiền |
| `commercial` | sàn forex, broker, spread thấp, đòn bẩy |
| `navigational` | tên thương hiệu + login/app |
| `informational` | forex là gì, cách giao dịch |

Lexicon nằm ở config theo market; `swap-free / Islamic` là nhóm bắt buộc cho ID và MY (`markets.yaml`).

### 2.4 Cụm bằng cấu trúc

`KeywordCluster` không có nhãn prose. Danh tính cụm là `head_keyword_id`; thành viên là `member_keyword_ids[]`; phương pháp là `cluster_method` ∈ `{lexical_shared_token, serp_overlap}`. Điều này giữ cụm khách quan và tái lập.

## 3. Reasoning

**Vì sao tách biến thể dấu?** Volume và SERP của hai biến thể khác nhau thật; gộp lại là mất dữ liệu và sai phân bổ nhu cầu. Lưu `keyword_raw` + `keyword_normalized` + `has_diacritics` cho phép phân tích cả hai chiều.

**Vì sao thêm `trust_check`?** Trong forex, người dùng tìm "X lừa đảo" trước khi mở tài khoản. Nhét nhóm này vào `informational` hay `commercial` đều sai bản chất hành vi.

**Vì sao intent bằng lexicon?** Lexicon tái lập, kiểm toán, chỉnh theo market; model tự phán intent là nhận định không truy vết được.

**Vì sao cụm bằng cấu trúc?** Nhãn cụm do model sinh là text tự do — vi phạm mandate. Head keyword + phương pháp cố định giữ cụm là dữ liệu, không phải diễn giải.

## 4. Advantages

- Không mất dữ liệu do gộp mù biến thể.
- Intent phản ánh đúng vertical nhờ `trust_check`.
- Metric có provenance, thiếu thì trung thực để `null`.
- Cụm tái lập, không phụ thuộc chất lượng prose.

## 5. Disadvantages

- Lexicon cần bảo trì cho từng ngôn ngữ/market.
- Số record tăng gấp đôi ở thị trường có dấu (VN).
- Cụm bằng token đơn giản có thể thô hơn cụm ngữ nghĩa.

## 6. Tradeoffs

| Gán intent | A. Lexicon theo market | B. Model sinh nhãn | C. SERP-inferred |
|---|---|---|---|
| Tái lập | Cao | Thấp | Trung bình |
| Chi phí | Thấp | Trung bình | Cao (tốn SERP) |
| Bám vertical | Cao (chỉnh tay) | Trung bình | Cao |
| Vi phạm mandate | Không | Có | Không |

**Xếp hạng: A > C > B.** A rẻ, tái lập, chỉnh theo market; dùng `intent_method` để sau này bổ sung C cho ca mơ hồ. B bị loại vì tạo nhận định không truy vết.

## 7. Best Practice

- Luôn lưu `keyword_raw`, `keyword_normalized`, `has_diacritics` song song.
- `is_branded` khớp cả khi bỏ dấu (để `exness lừa đảo` vẫn nhận ra thương hiệu).
- Metric thiếu → `Measurement.missing` kèm lý do, không điền 0.
- Lexicon intent theo market, có nhóm `swap-free` cho ID/MY.
- Cụm bằng `head_keyword_id`, không bằng nhãn model.

## 8. Common Mistakes

1. Gộp biến thể có/không dấu.
2. Nhét `trust_check` vào `informational`.
3. Điền 0 cho volume thiếu.
4. Gán `search_volume` từ Google Trends (đó là index, không phải volume).
5. Đặt nhãn cụm bằng prose do model sinh.
6. Bỏ nhóm `swap-free` ở thị trường Hồi giáo.
7. Quên gắn `provenance` cho từng metric.

## 9. Checklist

- [x] Chốt `keyword_raw / keyword_normalized / has_diacritics`
- [x] Chốt năm intent gồm `trust_check`
- [x] Chốt `intent_method` (`lexicon` / `serp_inferred`)
- [x] Chốt metric là `Measurement`, `keyword_trend` trần `estimate`
- [x] Chốt cụm bằng `head_keyword_id` + `cluster_method` (ADR-012)
- [x] Chốt `is_branded` khớp cả khi bỏ dấu
- [x] Hiện thực lát cắt tối thiểu (search_volume/cpc/competition) + e2e VN-vi
