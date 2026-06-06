# P2-14: Submission Format Check for ICDM 2026 Applied Track

## Status update 2026-06-06 - Stage 3.16/P0-02B

- H-row purged split gate da PASS cho paper-core SGD evidence.
- `artifacts/split_audit.csv` hien ghi `explicit_purge_rows=50`, `horizon_overlap_rows=0`, `status=PASS` cho BTC-USDT va ETH-USDT train/validation boundaries.
- Audit chi tiet: `audits/audit_stage3_16_purged_evidence_gate_v001.md`.
- `Paper_ICDM_2026/paper_applied_singleblind.tex` da duoc cut theo `fix_v1.md`, build thanh PDF `4` trang va dung purged SGD core evidence.
- Audit chi tiet: `audits/audit_stage3_17_fix_v1_applied_track_cut_v001.md`.
- Trang/format gate: PASS cho file candidate single-blind.
- Upload readiness: PARTIAL, vi author placeholders van can duoc thay bang thong tin that truoc khi nop Applied Track.

## Mục tiêu

File này khóa quyết định format submission cho bản paper ICDM 2026 hiện tại. Trọng tâm là tránh lỗi giữa Applied Track single-blind và Research Track triple-blind, đồng thời giữ một bản anonymous backup nếu submission portal yêu cầu ẩn danh.

## Nguồn hướng dẫn đã kiểm

- ICDM 2026 Applied Track CFP: `https://icdm2026.neu.edu.cn/CallforAppliedTrack/list.htm`
  - Applied Track dùng IEEE 2-column format.
  - Giới hạn submission: tối đa 10 trang, bao gồm bibliography và appendices.
  - Submission là **single-blind**.
  - Applied Track nhận benchmark, dataset mới, và phân tích thực nghiệm toàn diện.
- ICDM 2026 Research Track CFP: `https://icdm2026.neu.edu.cn/CallforResearchTrack/list.htm`
  - Research Track dùng **triple-blind**.
  - Author names, affiliations, funding, acknowledgements, và thông tin nhận diện phải bị ẩn.
- Ngày kiểm tra: 2026-06-05.

## Quyết định submission hiện tại

Paper `CryptoRegimeShift-LOB` nên nộp theo **ICDM 2026 Applied Track** vì contribution chính là benchmark/evaluation/failure-analysis cho L2 crypto LOB. Vì Applied Track là single-blind, bản submit chính nên hiển thị tác giả, affiliation, và email.

Tuy nhiên vẫn giữ một bản anonymous backup vì:

- submission portal có thể cấu hình nhầm hoặc yêu cầu file ẩn danh;
- nếu đổi sang Research Track, Research Track yêu cầu triple-blind;
- backup giúp kiểm tra nhanh các rủi ro nhận diện.

## Kết quả kiểm tra build hiện tại

- `paper_applied_singleblind.tex`: build được bằng `tectonic.exe`, nhưng PDF hiện có 13 trang.
- `paper_anonymous_backup.tex`: build được bằng `tectonic.exe`, nhưng PDF hiện có 13 trang.
- `main.tex`: PDF hiện có 13 trang.
- Kết luận format: **NOT submission-ready** theo giới hạn 10 trang của Applied Track. Cần một bước rút gọn paper riêng trước khi upload.
- Các warning TeX hiện chủ yếu là underfull/overfull box và warning rerun/BibTeX của Tectonic; chúng không chặn build nhưng nên kiểm tra lại sau khi rút còn 10 trang.

## Gate h-row purged split

`fix_v1.md` yêu cầu dừng submission nếu chưa có kết quả h-row purged split. Gate hiện tại **không pass**:

- `artifacts/split_audit.csv` ghi `explicit_purge_rows=0`, `horizon_overlap_rows=50`, `WARN_BOUNDARY_OVERLAP` cho BTC-USDT train và validation boundaries.
- `artifacts/split_audit.csv` ghi `explicit_purge_rows=0`, `horizon_overlap_rows=50`, `WARN_BOUNDARY_OVERLAP` cho ETH-USDT train và validation boundaries.
- `outputs/paper_assets/table_19_chronological_split_audit.csv` lặp lại cùng trạng thái.

Kết luận khoa học: **NOT submission-ready**. Không được đổi wording trong paper thành purged split, không được rút gọn thành bản nộp, và không được thay số liệu nếu chưa regenerate toàn bộ forecasting/execution/stress/bootstrap/cross-asset artifacts dưới purged protocol.

## Follow-up bắt buộc trước khi submission

1. Rerun split với `purge_horizon_events=true` và `purge_gap_events=50`.
2. Rerun các artifact paper-facing phụ thuộc split: forecasting, policy tuning, execution/RSEP, stress, bootstrap, và asset-held-out.
3. Regenerate split audit để tất cả train/validation boundaries có `horizon_overlap_rows=0` và `status=PASS`.
4. Sau khi purged artifacts pass, mới áp dụng cut-to-10-page từ `fix_v1.md`.
5. Move claim maps, reproducibility checklist, regime sensitivity, model-selection ledger, và ablation details sang artifact text thay vì main PDF.

## File TeX cần dùng

- `Paper_ICDM_2026/paper_applied_singleblind.tex`
  - Dùng cho Applied Track nếu portal giữ đúng single-blind.
  - Author block đang có placeholder `TODO_AUTHOR_NAME`, `TODO_AFFILIATION`, `TODO_EMAIL`.
  - Phải thay placeholder bằng thông tin thật trước khi submit.
- `Paper_ICDM_2026/paper_anonymous_backup.tex`
  - Dùng nếu portal yêu cầu anonymous hoặc nếu chuyển sang Research Track.
  - Giữ `Anonymous Authors`.
  - Không thêm acknowledgement, funding, affiliation, email, hoặc repo URL định danh.
- `Paper_ICDM_2026/main.tex`
  - Giữ làm working draft hiện tại; không xem là file submission cuối nếu chưa chọn track.

## Audit các điểm nhận diện trong manuscript

Kết quả kiểm tra hiện tại:

- Author block trong `main.tex`: `Anonymous Authors`.
- Acknowledgements: chưa thấy section acknowledgement riêng.
- Funding/grant: chưa thấy funding/grant statement riêng.
- GitHub/repository URL: chưa thấy URL repo trực tiếp trong `main.tex`.
- Artifact/reproducibility: manuscript mô tả artifact pack và restricted data ở mức khái niệm, không gắn URL định danh.
- Self-citation wording: không thấy câu kiểu "our previous work" trong phạm vi kiểm tra format.

## Checklist trước khi submit Applied Track

1. Dùng `paper_applied_singleblind.tex`.
2. Thay toàn bộ `TODO_AUTHOR_NAME`, `TODO_AFFILIATION`, `TODO_CITY`, `TODO_COUNTRY`, `TODO_EMAIL`.
3. Build PDF bằng:

   ```powershell
   cd CryptoRegimeShift\Paper_ICDM_2026
   ..\tectonic.exe paper_applied_singleblind.tex
   ```

4. Kiểm tra PDF không vượt 10 trang.
5. Kiểm tra paper không claim profitability, live trading readiness, exact queue priority, hoặc universal market transfer.
6. Nếu thêm artifact/repo URL, chỉ thêm URL public sau khi đã quyết định single-blind Applied Track và repo không chứa raw commercial data, private logs, checkpoints, hoặc thông tin nhạy cảm.

## Checklist nếu portal yêu cầu anonymous

1. Dùng `paper_anonymous_backup.tex`.
2. Không thêm author names, affiliation, email, funding, acknowledgements, hoặc public repo link có thể định danh.
3. Nếu cần artifact link, dùng anonymous artifact service hoặc placeholder review-safe.
4. Build PDF bằng:

   ```powershell
   cd CryptoRegimeShift\Paper_ICDM_2026
   ..\tectonic.exe paper_anonymous_backup.tex
   ```

5. Grep các cụm nhận diện trước khi upload. Lưu ý không grep ký tự `@` đơn lẻ vì LaTeX dùng `@{}` trong table layout.

   ```powershell
   rg -n "TODO_AUTHOR|TODO_EMAIL|TODO_AFFILIATION|github|GitHub|acknowledg|fund|grant|affiliation" paper_anonymous_backup.tex
   rg -n "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" paper_anonymous_backup.tex
   ```

## Boundary vẫn phải giữ

- Không viết paper như trading-profit paper.
- Không claim live trading readiness.
- Không claim exact L3 replay, exact queue priority, hidden liquidity, hoặc passive fills.
- Không claim universal cross-asset generalization; chỉ nói BTC-USDT và ETH-USDT đã được evaluate theo protocol hiện tại.

## Kết luận

File candidate cho ICDM 2026 Applied Track là `paper_applied_singleblind.tex`, nhưng hiện **NOT submission-ready** cho tới khi có h-row purged results và PDF không quá 10 trang. File `paper_anonymous_backup.tex` là bản dự phòng review-safe nếu portal hoặc track yêu cầu anonymization, nhưng cũng **NOT submission-ready** với cùng blocker.
