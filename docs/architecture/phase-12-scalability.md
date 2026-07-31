# Phase 12 — Scalability

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Module: `orchestration`

## 1. Objective

Chạy hàng trăm broker × nhiều market, song song, resume được, kiểm soát chi phí, mà không viết lại nghiệp vụ. Ba yêu cầu cứng:

1. **Checkpoint & resume** — run lỗi giữa chừng tiếp tục được, không tốn lại tiền API.
2. **Song song hoá tự nhiên** — theo broker, theo market, theo collector độc lập.
3. **Chi phí kiểm soát từ kiến trúc** — quota, rate limit, `cost_ceiling` là hàng rào, không vá sau.

## 2. Architecture

### 2.1 DAG tác vụ

```
intake
  ├─ competitor_discovery ─┐
  └─ keyword_research ─────┼─ serp_research ─┬─ landing_page_discovery ─┐
                           │                 └─ ad_intelligence ────────┤
                           └─ compliance_context      competitor_intelligence
                                                              │
                                                    validate ─┴─ output
```

Mỗi node khai báo phụ thuộc; orchestration chạy node sẵn sàng song song, không chứa logic nghiệp vụ.

### 2.2 Đơn vị checkpoint

`market_run_id` là đơn vị checkpoint và song song. Một market fail chuyển `partial`, không kéo sập `run` (ADR-006). Resume đọc checkpoint + raw cache (Phase 11) nên không gọi lại API cho phần đã xong.

### 2.3 Ba trục song song

| Trục | Đơn vị | Chia sẻ |
|---|---|---|
| Broker | `run_id` | độc lập hoàn toàn |
| Market | `market_run_id` | chia sẻ khám phá cấp broker |
| Collector | node DAG | độc lập theo phụ thuộc |

Dữ liệu cấp broker (profile domain, đối thủ thương hiệu) dùng lại giữa các market cùng broker — lý do dùng `markets[]` một run (ADR-006).

### 2.4 Quota, rate limit, retry

- Giới hạn concurrency theo `providers.yaml` `rate_limit` (`requests_per_minute`, `concurrent`) — không vượt để tránh bị chặn giữa run.
- `CostMeter` đếm call + chi phí, in trước run lớn, chặn khi vượt `cost_ceiling` (ADR-010, `dry_run`).
- Retry theo `providers.yaml`: tối đa 3 lần, backoff mũ, chỉ retry `429/5xx/timeout`, không retry `4xx`.

### 2.5 Đường nâng cấp B → C

Kiến trúc modular (ADR-001) cho phép nâng từ DAG in-process (B) lên hàng đợi message (C) chỉ bằng thay lời gọi hàm bằng message queue, vì `orchestration` đã tách khỏi nghiệp vụ. Chưa xây C khi chưa có tải biện minh — tối ưu hoá mù là lãng phí.

## 3. Reasoning

**Vì sao checkpoint theo market?** Đó là ranh giới cô lập lỗi tự nhiên; một provider hết quota chỉ làm một market `partial`, phần còn lại vẫn tiến.

**Vì sao song song ba trục?** Broker độc lập cho fan-out rộng; market chia sẻ dữ liệu broker để tiết kiệm; collector song song trong ràng buộc DAG rút ngắn wall-clock.

**Vì sao chưa dùng message queue?** Xây event bus khi chưa biết collector nào là nút thắt là tối ưu hoá mù (Phase 1 mục 6). Modular giữ cửa mở nâng cấp khi có dữ liệu tải thật.

## 4. Advantages

- Resume không tốn lại API nhờ checkpoint + raw cache.
- Song song hoá tự nhiên theo broker/market/collector.
- Chi phí chặn từ kiến trúc: quota, rate limit, `cost_ceiling`.
- Nâng B → C khi cần mà không đụng nghiệp vụ.

## 5. Disadvantages

- Điều phối DAG + checkpoint phức tạp hơn chạy tuần tự.
- Song song cao làm tranh chấp cache và quota provider.
- Tách `run_id`/`market_run_id` khiến trạng thái resume nhiều mảnh.

## 6. Tradeoffs

| Orchestration | A. DAG in-process | B. Airflow/Prefect | C. Hàng đợi message tự xây |
|---|---|---|---|
| Thời gian ra bản đầu | Thấp | Trung bình | Cao |
| Scale 100+ broker | Tốt | Rất tốt | Rất tốt |
| Chi phí vận hành | Thấp | Trung bình | Cao |
| Hợp đội nhỏ | Có | Trung bình | Không (chưa có tải) |

**Xếp hạng: A > B > C.** A đủ cho quy mô hiện tại, rẻ vận hành, và vì `orchestration` đã tách nên nâng cấp sau không phải viết lại nghiệp vụ. B là bước kế hợp lý khi cần lịch biểu/giám sát mạnh. C chỉ đáng khi đã xác định nút thắt thật.

## 7. Best Practice

- Checkpoint theo `market_run_id`; một market fail không sập run.
- Tôn trọng `rate_limit` từng provider; giới hạn worker theo `concurrent`.
- In `CostMeter` và chờ xác nhận trước run lớn; `dry_run` là hàng rào cuối.
- Retry đúng chính sách; không retry `4xx`.
- Giữ `orchestration` không chứa logic nghiệp vụ để chừa đường B → C.

## 8. Common Mistakes

1. Checkpoint theo `run_id` thay vì `market_run_id` → một market lỗi kéo sập cả run.
2. Bỏ rate limiter → bị provider chặn giữa run.
3. Gọi lại API cho phần đã có trong raw cache.
4. Retry cả lỗi `4xx` (vô ích, tốn quota).
5. Xây message queue khi chưa có tải (tối ưu hoá mù).
6. Nhét logic nghiệp vụ vào orchestration, khoá luôn đường nâng cấp.

## 9. Checklist

- [x] Chốt DAG tác vụ và phụ thuộc
- [x] Chốt checkpoint/resume theo `market_run_id` (ADR-020)
- [x] Chốt ba trục song song broker/market/collector
- [x] Chốt rate limit + concurrency theo `providers.yaml`
- [x] Chốt `CostMeter` + `cost_ceiling` + `dry_run` là hàng rào chi phí
- [x] Chốt retry theo `providers.yaml`, không retry `4xx`
- [x] Chốt giữ đường nâng cấp B → C (ADR-001)
- [ ] Hiện thực `orchestration` — khi tới lượt theo mục 7
