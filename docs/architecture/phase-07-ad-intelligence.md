# Phase 7 — Ad Intelligence

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `Ad` (`ad_`)

> **Đây là nơi mandate dễ bị vi phạm nhất.** Agent này TUYỆT ĐỐI KHÔNG viết headline/description/CTA mới. Cơ chế cưỡng chế là schema: `Ad` không có field nào chứa được câu quảng cáo do model sinh (CLAUDE.md mục 1, ADR-002/015).

## 1. Objective

Ghi nhận quảng cáo đối thủ đang chạy để hiểu bối cảnh thị trường, làm đầu vào cho các agent hoạch định phía sau. Ba yêu cầu cứng:

1. **Chỉ lưu nguyên văn quan sát** — mọi text quảng cáo mang hậu tố `_observed` và có `provenance`.
2. **Phân tích pattern chỉ trả tần suất + nhãn phân loại khách quan** — không bao giờ sinh câu quảng cáo mới.
3. **Nguồn có thẩm quyền trước** — `ads_transparency` là nguồn ưu tiên cho ad creative.

## 2. Architecture

### 2.1 Entity `Ad`

| Field | Ý nghĩa |
|---|---|
| `advertiser_domain` | domain nhà quảng cáo (PSL) |
| `headline_observed`, `description_observed`, `display_url_observed` | nguyên văn quan sát, có thể null |
| `source` | `ads_transparency` \| `semrush` \| `dataforseo` |
| `first_seen_at`, `last_seen_at` | vòng đời quan sát |
| `landing_page_id` | tham chiếu `lp_` |
| `observed_flags` | cờ hiện diện khách quan |
| `provenance` | cấp entity |

Nguồn ưu tiên theo `source_priority.yaml` `ad_creative`: `ads_transparency → semrush → dataforseo`. TTL 3 ngày — ad creative biến động nhanh nhất.

### 2.2 Pattern = tần suất + cờ hiện diện

`observed_flags` là các boolean kiểm tra sự hiện diện khách quan của yếu tố, KHÔNG phải đánh giá:

```
mentions_regulation        có nhắc cơ quan quản lý / giấy phép
mentions_bonus_or_promo    có nhắc thưởng / khuyến mãi
mentions_leverage          có nhắc đòn bẩy
mentions_swap_free         có nhắc tài khoản swap-free / Islamic
```

Phân tích tổng hợp chỉ được trả **tần suất** các cờ này trên tập ad (đếm), không được trả câu quảng cáo gợi ý. Không có field nào cho "ad nên viết".

## 3. Reasoning

**Vì sao cưỡng chế bằng schema?** Cấm bằng prompt sẽ bị lách qua thời gian; schema không có chỗ chứa câu mới thì không có chỗ để bịa. Đây là ADR-002 áp dụng vào điểm rủi ro cao nhất.

**Vì sao chỉ cờ hiện diện?** "Có nhắc đòn bẩy" là dữ kiện kiểm chứng được; "đòn bẩy là góc bán tốt nhất" là khuyến nghị. Cờ boolean giữ ở phía dữ kiện.

**Vì sao `ads_transparency` trước?** Đây là nguồn có thẩm quyền nhất, phản ánh ad thật đang chạy; SEMrush/DataForSEO là bổ sung khi Transparency Center phủ không đủ market.

## 4. Advantages

- Không thể vô tình sinh nội dung quảng cáo — chặn ở tầng schema.
- Dữ liệu ad kiểm toán được: mọi câu chữ truy về nguồn và thời điểm.
- Cờ hiện diện cho phép phân tích tần suất mà không cần diễn giải.

## 5. Disadvantages

- Độ phủ `ads_transparency` không đều giữa các quốc gia; phải ghi nhận khi market thiếu dữ liệu.
- TTL 3 ngày → chi phí làm mới cao.
- `observed_flags` cần từ điển nhận dạng theo ngôn ngữ, phải bảo trì.

## 6. Tradeoffs

| Phân tích ad | A. Nguyên văn + cờ hiện diện | B. Sinh pattern/gợi ý | C. Chỉ lưu link ad |
|---|---|---|---|
| Tuân mandate | Tuyệt đối | Vi phạm | Tuyệt đối |
| Giá trị phân tích | Cao | Cao nhưng cấm | Thấp |
| Kiểm toán | Dễ | Khó | Dễ |

**Xếp hạng: A > C > B.** A cho giá trị phân tích tối đa trong ranh giới mandate. C an toàn nhưng nghèo thông tin. B bị loại tuyệt đối — sinh gợi ý quảng cáo là vượt mandate lõi.

## 7. Best Practice

- Mọi text ad lưu nguyên văn với `_observed` + `provenance`; không chỉnh sửa.
- Khi market không có dữ liệu Transparency, ghi nhận rõ ràng thay vì để trống mập mờ.
- `observed_flags` dùng từ điển theo ngôn ngữ trong config.
- Phân tích tổng hợp chỉ xuất tần suất/đếm, không xuất câu mới.
- Liên kết `landing_page_id` thay vì nhúng nội dung trang.

## 8. Common Mistakes

1. Thêm field kiểu `suggested_headline` / `ad_draft` (vi phạm mandate — bị linter chặn).
2. "Chuẩn hoá" câu quảng cáo thành mẫu rồi coi là dữ liệu.
3. Bỏ qua ghi nhận market thiếu dữ liệu Transparency.
4. Trộn nguồn ad mà không ghi `source`.
5. Dùng ad creative quá TTL 3 ngày như còn hiệu lực.
6. Diễn giải "góc quảng cáo" thành nhận định trong output.

## 9. Checklist

- [x] Chốt mọi text ad là `_observed` + provenance
- [x] Chốt `observed_flags` là cờ hiện diện khách quan, không nhận định
- [x] Chốt phân tích pattern chỉ trả tần suất/đếm (ADR-015)
- [x] Chốt nguồn ưu tiên `ads_transparency`, TTL 3 ngày
- [x] Chốt schema `Ad` KHÔNG có field chứa câu quảng cáo mới
- [x] Chốt ghi nhận market thiếu dữ liệu thay vì để trống
