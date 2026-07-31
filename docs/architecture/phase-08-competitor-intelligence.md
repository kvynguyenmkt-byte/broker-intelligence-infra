# Phase 8 — Competitor Intelligence

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `CompetitorProfile` (`prf_`)

## 1. Objective

Dựng hồ sơ định lượng cho từng đối thủ (từ Phase 3): authority, backlink, ước lượng traffic. Ba yêu cầu cứng:

1. **Không bao giờ lấy trung bình** — khi nhiều nguồn lệch nhau, chọn theo ưu tiên và ghi lại tất cả.
2. **Trần reliability** — traffic và authority không bao giờ `hard`, trần là `estimate`.
3. **Ghi nhận bất đồng** — lệch quá 3 lần thì gắn `low_agreement` và hạ confidence.

## 2. Architecture

### 2.1 Metric và nguồn ưu tiên

| Field | Unit | Reliability | Ưu tiên (`source_priority.yaml`) |
|---|---|---|---|
| `domain_authority` | `dr_or_as` | `estimate` | ahrefs → semrush (DR và AS là hai thang, KHÔNG quy đổi) |
| `referring_domain_count` | `domains` | `hard` | ahrefs → semrush |
| `organic_traffic_estimate` | `monthly_visits` | `estimate` | ahrefs → semrush → similarweb |
| `paid_traffic_estimate` | `monthly_visits` | `estimate` | semrush → similarweb |
| `total_traffic_estimate` | `monthly_visits` | `estimate` | similarweb → semrush |

### 2.2 Hợp nhất đa nguồn trong `Measurement`

`Measurement` mang sẵn cơ chế đa nguồn (dùng chung toàn hệ thống):

```
value            giá trị CHỌN theo source_priority.yaml (không phải trung bình)
provenance       nguồn thắng + conflicts[] ghi các nguồn khác
values_by_source[] toàn bộ giá trị từng nguồn
divergence_ratio max/min giữa các nguồn
low_agreement    true nếu divergence_ratio > 3.0 (source_priority.yaml)
```

Khi `low_agreement = true`, confidence bị trần 0.5 (`low_agreement_confidence_cap`).

## 3. Reasoning

**Vì sao không trung bình?** Trung bình một số hard và một số rác tạo ra con số không nguồn nào xác nhận, che mất bất đồng. Chọn theo ưu tiên + lưu tất cả giữ cả quyết định lẫn bằng chứng.

**Vì sao trần estimate?** SimilarWeb/Ahrefs DR/SEMrush AS đều là mô hình ước lượng, không phải số đo trực tiếp. Gán `hard` là nói dối về độ chắc chắn.

**Vì sao DR ≠ AS?** Domain Rating (Ahrefs) và Authority Score (SEMrush) là hai thang khác nhau; quy đổi lẫn nhau là bịa. Lưu kèm nguồn, không hợp nhất thành một thang.

## 4. Advantages

- Con số cuối luôn truy về một nguồn cụ thể, không phải trung bình mờ.
- Bất đồng giữa nguồn hiện rõ qua `divergence_ratio` và `low_agreement`.
- Reliability trung thực nhờ trần cứng cho traffic/authority.

## 5. Disadvantages

- Cần ≥2 nguồn để tính `divergence_ratio` → chi phí cao hơn.
- Người đọc phải hiểu `values_by_source` thay vì một con số duy nhất.
- Trần estimate có thể khiến metric mạnh trông "yếu" hơn thực tế.

## 6. Tradeoffs

| Hợp nhất nguồn | A. Chọn theo ưu tiên + lưu tất cả | B. Trung bình | C. Chỉ giữ một nguồn |
|---|---|---|---|
| Bảo toàn thông tin | Cao | Thấp | Thấp |
| Lộ bất đồng | Có | Không | Không |
| Chi phí | Trung bình | Thấp | Thấp |

**Xếp hạng: A > C > B.** A giữ cả quyết định lẫn bằng chứng và lộ bất đồng. C rẻ nhưng mất khả năng đối chiếu. B bị loại — trung bình che dấu xung đột, đúng thứ ta cần thấy.

## 7. Best Practice

- Luôn lưu `values_by_source[]` kể cả khi chỉ một nguồn.
- Chọn `value` theo `source_priority.yaml`, ghi các nguồn khác vào `conflicts`.
- Tính `divergence_ratio` và gắn `low_agreement` khi > 3 lần.
- Không quy đổi DR ↔ AS.
- Áp trần `estimate` cho mọi metric traffic/authority.

## 8. Common Mistakes

1. Lấy trung bình giữa các nguồn.
2. Gán `hard` cho traffic/authority.
3. Quy đổi DR sang AS hoặc ngược lại.
4. Bỏ `values_by_source`, chỉ giữ con số cuối.
5. Không tính `divergence_ratio`, bỏ sót bất đồng lớn.
6. Không hạ confidence khi `low_agreement`.

## 9. Checklist

- [x] Chốt không lấy trung bình, chọn theo `source_priority.yaml` (ADR-016)
- [x] Chốt `values_by_source[]` + `divergence_ratio` + `low_agreement`
- [x] Chốt trần `estimate` cho traffic/authority
- [x] Chốt DR và AS không quy đổi
- [x] Chốt `low_agreement_confidence_cap = 0.5`
- [x] Chốt entity `CompetitorProfile` trong `canonical.v1.json`
