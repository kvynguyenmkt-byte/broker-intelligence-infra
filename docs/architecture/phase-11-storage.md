# Phase 11 — Storage

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Module: `storage`

## 1. Objective

Lưu trữ dữ liệu qua các tầng sao cho replay được mà không tốn thêm API, và chạy lại không sinh trùng. Ba yêu cầu cứng:

1. **Raw bất biến** — payload thô lưu nguyên trạng, write-once, không ghi đè (ADR-003).
2. **Không biến đổi** — `storage` chỉ lưu/đọc, không chuẩn hoá, không diễn giải (Phase 1 mục 2.3).
3. **Idempotent** — chạy lại một `run_id` không tạo dữ liệu trùng (ADR-006).

## 2. Architecture

### 2.1 Bốn kho

```
data/raw/<broker_slug>/<market_key>/<run_id>/        FetchEnvelope thô, write-once
data/normalized/<broker_slug>/<market_key>/<run_id>/ entity canonical đã chuẩn hoá
data/snapshots/<broker_slug>/<market_key>/<snapshot_id>.json  dataset có phiên bản
data/cache/                                          TTL cache theo loại dữ liệu
```

`data/raw`, `data/normalized`, `data/cache` đã nằm trong `.gitignore`.

### 2.2 Raw store — content-addressed, append-only

Mỗi `FetchEnvelope` lưu kèm hash nội dung. Ghi một lần; lần fetch sau trùng nội dung không ghi đè mà tham chiếu bản cũ. Đây là khoản tiết kiệm lớn nhất: DataForSEO tính tiền theo query, giữ raw cho phép replay toàn pipeline với logic chuẩn hoá mới, không tốn đồng API nào.

### 2.3 Cache — TTL theo loại, không dùng chung

Khoá cache = `capability + market_key + params_normalized + provider_id`. TTL theo `providers.yaml` (`cache_ttl_days`): ad_creative 3 ngày, SERP 7, backlink 14, keyword_volume 30... Dữ liệu quảng cáo biến động nhanh hơn backlink nhiều lần nên không dùng một TTL chung (ADR-008).

### 2.4 Snapshot registry

Một chỉ mục nhẹ ánh xạ `snapshot_id → { run_id, schema_version, created_at, entity_counts }`. Snapshot là ảnh dataset có phiên bản để agent phía sau tham chiếu ổn định; registry cho phép truy vết và dọn theo retention.

### 2.5 Retention

Raw tốn dung lượng, cần chính sách sớm: giữ raw N ngày rồi nén/archival; normalized theo số bản gần nhất mỗi market; snapshot giữ theo `schema_version`. Chính sách ở config, không hardcode.

## 3. Reasoning

**Vì sao raw bất biến?** Bạn sẽ đổi ý về cách chuẩn hoá. Giữ raw cho phép replay với logic mới mà không tốn API — trụ cột tiết kiệm của cả kiến trúc.

**Vì sao content-addressed?** Hash nội dung cho dedup tự nhiên và phát hiện thay đổi; cùng response không lưu hai lần.

**Vì sao TTL theo loại?** Một TTL chung hoặc quá phí (làm mới backlink mỗi 3 ngày) hoặc quá cũ (dùng ad creative 30 ngày). Gắn TTL vào bản chất biến động của dữ liệu.

## 4. Advantages

- Replay pipeline không tốn API nhờ raw bất biến.
- Dedup và phát hiện đổi nhờ content-addressing.
- Cache đúng nhịp biến động từng loại dữ liệu.
- Idempotent: chạy lại an toàn, hợp orchestration/resume.

## 5. Disadvantages

- Raw tốn dung lượng, buộc có retention sớm.
- Ba tầng store làm luồng đọc/ghi phức tạp hơn một DB đơn.
- Filesystem không lý tưởng cho truy vấn phức tạp (cần index riêng).

## 6. Tradeoffs

| Backend lưu trữ | A. Filesystem/object store + index | B. RDBMS | C. Data warehouse |
|---|---|---|---|
| Chi phí khởi tạo | Thấp | Trung bình | Cao |
| Hợp raw immutable | Cao | Trung bình | Trung bình |
| Truy vấn quan hệ | Trung bình (cần index) | Cao | Cao |
| Scale broker/market | Cao | Trung bình | Cao |

**Xếp hạng: A > B > C.** A hợp bản chất write-once của raw và rẻ để bắt đầu; thêm index cho truy vấn. B mạnh truy vấn nhưng raw blob trong DB là phản mẫu. C chỉ đáng khi đã có tải phân tích lớn — chưa cần bây giờ.

| Cache backend | Filesystem (bắt đầu) | Redis (khi song song cao) |
|---|---|---|
| Chọn | Mặc định, đơn giản | Nâng cấp khi nhiều worker tranh cache |

## 7. Best Practice

- Ghi raw một lần, không bao giờ ghi đè; mọi chuẩn hoá đọc từ raw.
- Content-address raw để dedup và phát hiện đổi.
- TTL theo loại từ `providers.yaml`, không dùng TTL chung.
- Đặt retention từ ngày đầu, cấu hình được.
- Khoá thư mục theo `broker_slug/market_key/run_id` nhất quán với `core.identity`.

## 8. Common Mistakes

1. Ghi đè raw khi fetch lại.
2. Chuẩn hoá ngay lúc lưu, không giữ raw (mất khả năng replay).
3. Dùng một TTL chung cho mọi loại dữ liệu.
4. Không có retention → đầy đĩa giữa chừng.
5. Khoá cache thiếu `market_key` → phân mảnh và cache miss.
6. Nhét raw blob vào RDBMS như dữ liệu truy vấn.

## 9. Checklist

- [x] Chốt bốn kho: raw / normalized / snapshots / cache
- [x] Chốt raw bất biến, content-addressed, append-only (ADR-019)
- [x] Chốt TTL cache theo loại từ `providers.yaml` (ADR-008)
- [x] Chốt snapshot registry có `schema_version`
- [x] Chốt chính sách retention cấu hình được
- [x] Chốt khoá thư mục theo `broker_slug/market_key/run_id`
- [ ] Hiện thực module `storage` — khi tới lượt theo mục 7
