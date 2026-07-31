# Phase 5 — SERP Research

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `SerpSnapshot` (`srp_`), `SerpResult`

## 1. Objective

Chụp lại trang kết quả tìm kiếm cho từng keyword để biết ai chiếm ô quảng cáo và organic, làm đầu vào cho Phase 3 (hiện diện SERP), Phase 6 (landing page) và Phase 7 (ads). Ba yêu cầu cứng:

1. **`device` là chiều bắt buộc** — ads mobile và desktop khác nhau đáng kể; một snapshot không nói rõ device là dữ liệu mơ hồ.
2. **Mô hình vị trí theo khối** — dùng `block_rank` + `rank_in_block`, không dùng "position" đơn lẻ.
3. **Tách quảng cáo khỏi organic** — `is_ad` rõ ràng, không trộn hai loại vào một thứ hạng.

## 2. Architecture

### 2.1 Khoá và chiều

Một `SerpSnapshot` khoá bởi `(keyword_id, device)`. `device` ∈ `{mobile, desktop}`. TTL 7 ngày (`providers.yaml`). Nguồn: capability `serp_snapshot` (dataforseo → semrush).

### 2.2 Mô hình vị trí

```
SerpResult:
  block_type    ∈ {ads_top, ads_bottom, organic, local_pack, shopping, other}
  block_rank    thứ tự khối trên trang (1 = trên cùng)
  rank_in_block thứ hạng trong khối
  is_ad         true nếu là quảng cáo
  domain, url
  landing_page_id (lp_), ad_id (ad_)  — tham chiếu chéo, có thể null
```

`block_rank + rank_in_block` phân biệt được "quảng cáo #1 ở đỉnh" với "organic #1" — hai thứ có vị trí thị giác và giá trị khác hẳn, mà "position = 1" đơn lẻ gộp làm một.

### 2.3 Provenance cấp entity

`SerpSnapshot` là observed snapshot: mang một `Provenance` ở cấp entity (`captured_at`, provider, reliability `hard` cho vị trí quan sát được). Các trường trong `SerpResult` là quan sát dưới provenance đó, không cần Measurement riêng.

## 3. Reasoning

**Vì sao `device` bắt buộc?** Google trả bố cục ads khác nhau theo device; số ô quảng cáo trên mobile thường ít hơn và thứ tự khác. Không cố định device thì so sánh theo thời gian trở nên vô nghĩa.

**Vì sao mô hình khối?** SERP hiện đại là nhiều khối xếp chồng, không phải danh sách phẳng. "Position 3" có thể là ad hoặc organic tuỳ trang. Tách khối giữ đúng ngữ nghĩa vị trí.

**Vì sao tách `is_ad`?** Trộn ads và organic vào một thứ hạng làm hỏng mọi phân tích share-of-voice quảng cáo ở Phase 7.

## 4. Advantages

- So sánh theo thời gian nhất quán vì cố định `(keyword, device)`.
- Giữ đúng ngữ nghĩa vị trí, không đánh đồng ad với organic.
- Tham chiếu chéo tới landing page và ad, không lồng trùng dữ liệu.

## 5. Disadvantages

- Nhân đôi số lần chụp (mobile + desktop) → tăng chi phí.
- SERP biến động trong ngày; một snapshot chỉ là một lát thời gian.
- Phân loại `block_type` phụ thuộc format response của provider.

## 6. Tradeoffs

| Mô hình vị trí | A. Khối (block_rank+rank_in_block) | B. Position phẳng | C. Toạ độ pixel |
|---|---|---|---|
| Đúng ngữ nghĩa | Cao | Thấp | Cao |
| Ổn định giữa provider | Cao | Trung bình | Thấp |
| Chi phí xử lý | Thấp | Rất thấp | Cao |

**Xếp hạng: A > C > B.** A giữ ngữ nghĩa khối mà vẫn ổn định và rẻ. C chính xác thị giác nhưng phụ thuộc render, không provider nào trả ổn định. B rẻ nhất nhưng đánh mất phân biệt ad/organic — hỏng ngay ở Phase 7.

## 7. Best Practice

- Luôn chụp cả `mobile` và `desktop`, coi thiếu một device là dữ liệu chưa đủ.
- Ghi `captured_at` chính xác, tôn trọng TTL 7 ngày.
- Không suy ra thứ hạng thiếu; khối nào provider không trả thì bỏ trống.
- Liên kết `ad_id`/`landing_page_id` thay vì nhúng nội dung ad/lp vào SERP.

## 8. Common Mistakes

1. Bỏ chiều `device`.
2. Dùng một số "position" đơn lẻ cho cả ads và organic.
3. Trộn ads vào thứ hạng organic.
4. Nhúng nguyên nội dung landing page vào SerpResult (lồng trùng).
5. Bỏ qua TTL, dùng snapshot cũ như mới.
6. Suy đoán thứ hạng cho khối provider không trả.

## 9. Checklist

- [x] Chốt `device` là chiều bắt buộc (ADR-013)
- [x] Chốt `block_rank` + `rank_in_block`, bỏ position đơn lẻ
- [x] Chốt `block_type` enum và cờ `is_ad`
- [x] Chốt tham chiếu chéo `landing_page_id` / `ad_id`
- [x] Chốt provenance cấp entity, TTL 7 ngày
- [x] Chốt entity `SerpSnapshot` / `SerpResult` trong `canonical.v1.json`
