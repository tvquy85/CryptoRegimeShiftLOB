# AGENTS.md

## 1. Ngữ cảnh

Repo phục vụ xây dựng và chạy thí nghiệm cho bài báo dự kiến nộp **ICDM 2026**.

Tất cả phân tích, kế hoạch, nhận xét kết quả và phản hồi phải viết bằng **tiếng Việt**, bao gồm cả phần plan.

Trước khi lập kế hoạch, chạy thí nghiệm, sửa code, sửa pipeline hoặc đánh giá kết quả, luôn đọc `AGENTS.md` và đối chiếu với kế hoạch tổng quan trong `TongQuan.md`.

## 2. Phạm vi mã nguồn và thư mục làm việc

Tất cả mã nguồn phải được tạo trong thư mục `CryptoRegimeShift` để tránh nhầm với các project khác.

Khi inspect mã nguồn, mặc định tìm trong `CryptoRegimeShift` để tránh hao context và token.

## 3. Dữ liệu và tài liệu tham khảo

Dữ liệu nằm tại:

```text
data\full2024
```

Các paper liên quan nằm trong thư mục:

```text
paper
```

Các source code mô hình nằm trong thư mục:

```text
LOBFrame\models
```

## 4. Lập kế hoạch

Mọi plan phải dựa trên:

- Context trước đó trong trao đổi.
- Phân tích và kết quả đã có ở bước trước.
- Kế hoạch tổng quan trong `TongQuan.md`.
- Quy tắc hiện hành trong `AGENTS.md`.
- Mục tiêu cuối cùng: xây dựng thí nghiệm đủ mạnh cho paper **ICDM 2026**.

Khi đề xuất bước tiếp theo, phải dựa trên phân tích trước đó, không làm rời rạc hoặc cảm tính.

Luôn ưu tiên giải pháp tổng quát, có thể tái sử dụng và mở rộng. Không xử lý theo kiểu ad hoc nếu chưa có lý do kỹ thuật rõ ràng.

## 5. Điều tra và tìm giải pháp

Khi gặp lỗi, kết quả yếu hoặc hiện tượng bất thường, phải xử lý với vai trò **chuyên gia ML hàng đầu**:

- Investigate kỹ nguyên nhân.
- Tìm và đối chiếu với nguồn uy tín.
- Ưu tiên paper, benchmark, tài liệu kỹ thuật chính thống hoặc tài liệu từ nguồn đáng tin cậy.
- Không kết luận vội nếu chưa đủ bằng chứng.
- Không claim quá mức nếu kết quả chưa được kiểm chứng.

Giải pháp đưa ra phải có cơ sở kỹ thuật, có khả năng tổng quát hóa và phù hợp với mục tiêu paper.

## 6. Góc nhìn đánh giá

Luôn đánh giá từ hai vai trò:

- **Principal ML Scientist**: tập trung vào mô hình, dữ liệu, phương pháp, độ tin cậy và khả năng tổng quát.
- **Reviewer ICDM hàng đầu**: đánh giá novelty, technical soundness, empirical rigor, clarity, reproducibility và significance.

Không được claim quá mức khi kết quả chưa đủ chuẩn **ICDM 2026**.

## 7. Chạy thí nghiệm

Tận dụng GPU **RTX 3090**, nhưng phải kiểm soát thời gian và tài nguyên.

Với thí nghiệm mới hoặc có khả năng chạy lâu:

- Bắt đầu từ scale nhỏ.
- Mở rộng dần lên scale trung bình/lớn.
- Mỗi stage có `run_id` riêng.
- Mỗi stage có audit riêng.
- Chỉ sang stage tiếp theo khi pass gate đã định nghĩa.

Stage gợi ý:

```text
stage_0_sanity_check
stage_1_small_scale
stage_2_medium_scale
stage_3_full_scale
```

## 8. Local LLM và cache

Local LLM phải được:

- Download một lần.
- Load từ cache local ở các lần sau.
- Tránh download hoặc load lại không cần thiết.

Trước khi tải model từ internet, luôn kiểm tra cache local/model path.

## 9. Thư viện và môi trường

Khi thiếu thư viện, kiểm tra theo thứ tự:

1. Môi trường hiện tại hoặc thư mục `FinEval`.
2. `d:\LOBProj\LOBExp\`.
3. Internet, chỉ khi hai nguồn trên không có.

Không cài đặt tùy tiện nếu có thể tái sử dụng môi trường, thư viện hoặc cache sẵn có.

## 10. Audit kết quả

Nếu kết quả chưa đạt chuẩn **ICDM 2026**, phải điều tra nghiêm túc:

- Vì sao kết quả yếu?
- Vấn đề nằm ở dữ liệu, mô hình, thiết kế thí nghiệm hay metric?
- Có leakage, bias, overfitting hoặc thiếu baseline mạnh không?
- Kết quả đã đủ thuyết phục reviewer chưa?
- Cần cải tiến gì để nâng chất lượng paper?

Phân tích audit phải được lưu thành **nhiều file riêng**, không gom tất cả vào một file lớn.

Mỗi file audit cần có tên ngắn gọn, dễ hiểu và phản ánh đúng nội dung kiểm tra để tiện truy vết.

Quy tắc đặt tên:

```text
audit_<run_id>_<noi_dung_chinh>.md
```

Ví dụ:

```text
audit_stage_0_sanity_check_data_quality.md
audit_stage_1_small_scale_baseline.md
audit_stage_1_small_scale_error_analysis.md
audit_stage_2_medium_scale_model_comparison.md
audit_stage_2_medium_scale_metric_review.md
audit_stage_3_full_scale_icdm_readiness.md
```

Mỗi file audit cần có:

- `run_id`
- Mục tiêu thí nghiệm
- Cấu hình chính
- Kết quả chính
- Vấn đề phát hiện
- Nguyên nhân khả dĩ
- Mức độ ảnh hưởng đến paper
- Đánh giá theo chuẩn ICDM 2026
- Quyết định: pass / fail / cần chạy lại
- Bước tiếp theo

## 11. Nguyên tắc kết luận

Mọi kết luận phải trung thực với bằng chứng hiện có.

Không được:

- Phóng đại novelty.
- Bỏ qua kết quả âm tính.
- Che giấu lỗi thí nghiệm.
- Diễn giải kết quả vượt quá dữ liệu.
- Tối ưu cục bộ bằng mẹo ad hoc chỉ để làm đẹp số.

Mục tiêu là tạo thí nghiệm có giá trị khoa học, có khả năng tái lập và đủ sức thuyết phục reviewer **ICDM 2026**.