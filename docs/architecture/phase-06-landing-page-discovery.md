# Phase 6 — Landing Page Discovery

Trạng thái: ✅ Chốt · Ngày: 2026-07-31 · Entity: `LandingPage` (`lp_`)

## 1. Objective

Nhận diện và chuẩn hoá trang đích quảng cáo mà đối thủ dùng, làm đầu vào cho Phase 7 (ads). Ba yêu cầu cứng:

1. **Bắt subdomain riêng** — landing page quảng cáo thường nằm ở `lp.`, `go.`, `promo.` và bị `noindex`.
2. **Tách tham số affiliate nhưng ghi lại** — bỏ tracking khỏi `url_canonical`, nhưng lưu danh sách `stripped_params[]` để không mất thông tin.
3. **Theo redirect tới đích cuối** — ghi cả `redirect_chain[]`.

## 2. Architecture

### 2.1 Chuẩn hoá URL landing page

```
url_original         giữ nguyên URL quan sát
→ theo redirect_chain[] tới đích cuối
→ tách query affiliate → stripped_params[] (ref, aff, clickid, utm_*, ...)
url_canonical        URL sạch, không tracking
destination_domain   registrable domain đích (PSL)
```

Danh sách tham số affiliate lấy từ `source_priority.yaml` `affiliate_query_params`. Tách bằng PSL cho domain, không cắt chuỗi.

### 2.2 Tín hiệu trang

| Field | Ý nghĩa |
|---|---|
| `is_dedicated_subdomain` | true nếu subdomain kiểu `lp/go/promo` |
| `subdomain_label` | nhãn subdomain quan sát (`lp`, `go`, ...) |
| `is_noindex` | trang chặn index |
| `http_status`, `is_reachable` | trạng thái truy cập |
| `observed_title` | tiêu đề trang nguyên văn (quan sát, không model sinh) |

`LandingPage` mang `Provenance` cấp entity (`fetched_at`, reliability `hard` cho dữ kiện quan sát; nếu chỉ suy từ link thì `inferred`).

## 3. Reasoning

**Vì sao bắt subdomain riêng?** Trang đích quảng cáo tách khỏi site chính để A/B test và tránh ảnh hưởng SEO; bỏ qua chúng là bỏ qua đúng trang quan trọng nhất cho phân tích ads.

**Vì sao tách nhưng ghi lại tham số?** `url_canonical` cần sạch để dedup và so khớp; nhưng tham số affiliate cho biết mạng lưới đối tác — mất chúng là mất tình báo. Hai mục tiêu, hai field.

**Vì sao theo redirect?** Link quảng cáo thường qua nhiều chặng tracking; chỉ đích cuối mới là trang thật, nhưng chuỗi trung gian tiết lộ nhà cung cấp tracking.

## 4. Advantages

- Không bỏ sót trang đích quảng cáo nằm ở subdomain riêng.
- `url_canonical` sạch cho phép dedup và so khớp chính xác.
- Giữ được tình báo affiliate qua `stripped_params` và `redirect_chain`.

## 5. Disadvantages

- Fetch trang thật tốn độ trễ và có rào cản (bot, geo).
- Trang `noindex` có thể đổi/biến mất nhanh; TTL 7 ngày.
- Điều khoản sử dụng của một số provider hạn chế lưu trữ nội dung bên thứ ba (việc pháp lý con người quyết).

## 6. Tradeoffs

| Xử lý tham số | A. Tách + ghi lại | B. Giữ nguyên URL | C. Bỏ hẳn tham số |
|---|---|---|---|
| Dedup chính xác | Cao | Thấp | Cao |
| Giữ tình báo affiliate | Cao | Cao | Không |
| Phân mảnh cache | Không | Cao | Không |

**Xếp hạng: A > C > B.** A vừa dedup sạch vừa giữ tình báo. C sạch nhưng vứt mất dữ liệu affiliate. B giữ đủ nhưng phân mảnh cache và hỏng dedup vì mỗi click là một URL khác.

## 7. Best Practice

- Tách affiliate param bằng danh sách trong config, cập nhật khi thấy tham số mới.
- Registrable domain đích bằng PSL.
- Luôn ghi `redirect_chain` kể cả khi chỉ một chặng.
- `observed_title` chỉ lưu nguyên văn; không tóm tắt, không diễn giải.
- Tôn trọng TTL và điều khoản provider khi lưu nội dung.

## 8. Common Mistakes

1. Bỏ qua subdomain `lp/go/promo`.
2. Ghi đè `url_original` bằng `url_canonical`.
3. Vứt tham số affiliate mà không ghi lại.
4. Không theo redirect, dùng URL tracking làm đích.
5. Cắt domain đích bằng regex.
6. Tóm tắt nội dung trang bằng model (tạo text tự do).

## 9. Checklist

- [x] Chốt `url_canonical` / `url_original` / `destination_domain`
- [x] Chốt `stripped_params[]` + `redirect_chain[]` (ADR-014)
- [x] Chốt `is_dedicated_subdomain` / `subdomain_label` / `is_noindex`
- [x] Chốt `observed_title` là nguyên văn quan sát
- [x] Chốt provenance cấp entity, TTL 7 ngày
- [x] Chốt entity `LandingPage` trong `canonical.v1.json`
