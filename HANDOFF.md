# HANDOFF — Chuyển dự án sang Claude Code

## 1. Cài đặt trong 4 bước

```bash
# 1. Giải nén bundle vào thư mục repo (hoặc repo trống mới)
unzip research-agent-handoff.zip -d ./research-agent
cd research-agent

# 2. Khởi tạo git — bắt buộc, để Claude Code theo dõi thay đổi
git init && git add -A && git commit -m "chore: import architecture handoff (phase 1-2)"

# 3. Đặt credentials vào shell profile của bạn, KHÔNG đặt trong repo
export DATAFORSEO_LOGIN="..."
export DATAFORSEO_PASSWORD="..."
export AHREFS_API_TOKEN="..."
export SEMRUSH_API_KEY="..."

# 4. Mở Claude Code tại thư mục này
claude
```

Claude Code tự đọc `CLAUDE.md` ở gốc repo. Không cần dán lại luật.

---

## 2. Bundle này chứa gì

```
research-agent/
├── CLAUDE.md                                   # ràng buộc cho mọi phiên — đọc trước
├── HANDOFF.md                                  # file này
├── docs/architecture/
│   ├── README.md                               # nhật ký quyết định + trạng thái
│   ├── phase-01-system-architecture.md         # ĐÃ CHỐT
│   └── phase-02-input-design.md                # ĐÃ CHỐT
└── config/
    ├── schemas/input.v1.json                   # hợp đồng đầu vào, dùng được ngay
    ├── providers.yaml                          # capability matrix + fallback + TTL
    ├── source_priority.yaml                    # thứ tự ưu tiên nguồn theo metric
    └── markets.yaml                            # ánh xạ market → location code từng provider
```

Chưa có: Phase 3–12 và toàn bộ mã nguồn. Mục 3 và 4 dưới đây là cách tạo chúng.

---

## 3. Prompt tiếp tục thiết kế (Phase 3 → 9)

Dán nguyên khối này vào Claude Code ở phiên đầu tiên nếu bạn muốn hoàn tất phần thiết kế trước khi code:

```
Đọc CLAUDE.md, docs/architecture/README.md, phase-01 và phase-02.

Bạn là AI System Architect tiếp quản dự án này. Phase 1 và 2 đã chốt, không sửa.
Hãy viết tiếp Phase 3 đến Phase 9, mỗi phase là một file riêng trong
docs/architecture/ theo đúng quy ước đặt tên file đã có.

Các phase:
  3. Competitor Discovery
  4. Keyword Research
  5. SERP Research
  6. Landing Page Discovery
  7. Ad Intelligence
  8. Competitor Intelligence
  9. Output Schema (kèm config/schemas/canonical.v1.json thật, JSON Schema 2020-12)

Mỗi phase BẮT BUỘC có đủ 9 mục, viết bằng tiếng Việt, tên trường bằng tiếng Anh:
  Objective / Architecture / Reasoning / Advantages / Disadvantages /
  Tradeoffs / Best Practice / Common Mistakes / Checklist

Ràng buộc:
- Không viết code hiện thực ở giai đoạn này, chỉ thiết kế.
- Không vi phạm mandate ở CLAUDE.md mục 1.
- Mọi entity phải dùng chung đối tượng Measurement và Provenance.
- Dừng sau mỗi phase, chờ tôi xác nhận rồi mới sang phase kế.
- Nếu có nhiều phương án, so sánh, xếp hạng, giải thích vì sao chọn.

Bắt đầu từ Phase 3.
```

### Các quyết định thiết kế then chốt cần giữ ở Phase 3–9

Ghi lại để phiên Claude Code không đi chệch:

- **Phase 3:** phân loại đối thủ thành 3 lớp — `direct_broker`, `affiliate_review`, `informational`. Trong ngành forex, SERP bị site affiliate thống trị; không phân lớp thì danh sách đối thủ vô dụng. Khi tính overlap phải **loại bỏ keyword thương hiệu**, nếu không mọi site review sẽ giả làm đối thủ trực tiếp.
- **Phase 4:** thêm intent `trust_check` (scam / lừa đảo / có uy tín không) bên cạnh 4 intent kinh điển. Đây là nhóm volume rất lớn trong vertical này và hành vi khác hẳn commercial.
- **Phase 5:** `device` là một chiều bắt buộc của SERP snapshot. Ads mobile và desktop khác nhau đáng kể. Dùng `block_rank` + `rank_in_block`, không dùng "position" đơn lẻ.
- **Phase 6:** landing page quảng cáo thường nằm ở subdomain riêng (`lp.`, `go.`, `promo.`) và noindex. Phải tách tham số affiliate khỏi URL canonical nhưng ghi lại danh sách đã tách.
- **Phase 7:** đây là nơi mandate dễ bị vi phạm nhất. `ad_creative` chỉ lưu nguyên văn đã quan sát kèm nguồn. Phân tích pattern chỉ trả về tần suất và nhãn phân loại, **không bao giờ** trả về câu quảng cáo mới.
- **Phase 8:** không bao giờ lấy trung bình giữa các nguồn. Lưu `values_by_source[]`, chọn theo `source_priority.yaml`, tính `divergence_ratio`; lệch quá 3 lần thì gắn `low_agreement` và hạ confidence.
- **Phase 9:** chuẩn hoá kiểu quan hệ, tham chiếu chéo bằng ID, không lồng trùng dữ liệu. Tiền tố ID: `cmp_`, `kw_`, `clu_`, `srp_`, `lp_`, `ad_`, `prf_`.

---

## 4. Prompt bắt đầu hiện thực

Chỉ dùng sau khi Phase 9 đã chốt:

```
Đọc CLAUDE.md mục 7 và làm đúng thứ tự đó.

Bước 1: hiện thực module core/ (types, provenance, identity, errors, logging)
kèm unit test. Chưa động tới network.

Dừng lại cho tôi review trước khi sang intake/.
```

---

## 5. Việc cần con người quyết, agent không tự làm được

- Mua quota DataForSEO / Ahrefs / SEMrush và đặt biến môi trường.
- Xác nhận danh sách market ưu tiên thực tế (hiện `config/markets.yaml` mới seed 6 nước SEA).
- Rà soát điều khoản sử dụng của từng nhà cung cấp trước khi lưu trữ dài hạn nội dung quảng cáo và nội dung trang của bên thứ ba.
- Nhờ luật sư bản địa xác minh phần dữ kiện pháp lý trước khi bất kỳ nội dung hay campaign nào lên sóng. Module `compliance_context` chỉ tổng hợp thông tin công khai, không phải tư vấn pháp lý.
