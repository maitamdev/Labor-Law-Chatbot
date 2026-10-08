# -*- coding: utf-8 -*-
"""
VietLabor AI - Kho Biểu Mẫu Pháp Lý Lao Động Chuẩn Hóa
Cung cấp toàn văn nội dung 8 mẫu văn bản pháp lý lao động chuẩn nhất theo Bộ luật Lao động 2019.
"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class LegalTemplate(TypedDict):
    id: str
    title: str
    tag: str
    basis: str
    summary: str
    query: str
    content: str


LEGAL_TEMPLATES: List[LegalTemplate] = [
    {
        "id": "hop_dong_lao_dong",
        "title": "Hợp đồng lao động chuẩn 2026",
        "tag": "Hợp đồng",
        "basis": "Điều 21 Bộ luật Lao động 2019 & Thông tư 10/2020/TT-BLĐTBXH",
        "summary": "Mẫu hợp đồng đầy đủ 10 nội dung bắt buộc: công việc, địa điểm, thời hạn, mức lương, thời giờ làm việc, an toàn lao động và bảo hiểm xã hội.",
        "query": "Hướng dẫn chi tiết và soạn thảo hợp đồng lao động chuẩn theo Bộ luật Lao động 2019",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

HỢP ĐỒNG LAO ĐỘNG
Số: ....../HĐLĐ-2026

- Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20 tháng 11 năm 2019;
- Căn cứ Nghị định số 145/2020/NĐ-CP ngày 14 tháng 12 năm 2020 của Chính phủ;
- Căn cứ nhu cầu và sự thỏa thuận tự nguyện của hai bên;

Hôm nay, ngày ..... tháng ..... năm 202..., tại: ................................................................
Chúng tôi gồm:

NGƯỜI SỬ DỤNG LAO ĐỘNG (BÊN A):
- Tên doanh nghiệp: ............................................................................................
- Mã số doanh nghiệp / MST: .............................................................................
- Địa chỉ trụ sở: .................................................................................................
- Đại diện bởi: Ông/Bà ........................................ Chức vụ: ..................................
- Điện thoại: ..................................................... Email: ........................................

NGƯỜI LAO ĐỘNG (BÊN B):
- Họ và tên: .................................................... Giới tính: ...................................
- Ngày, tháng, năm sinh: ................................. Quốc tịch: ..................................
- Số CCCD/Hộ chiếu: ..................................... Ngày cấp: ............. Nơi cấp: ........
- Địa chỉ thường trú: ............................................................................................
- Nơi ở hiện tại: .................................................................................................
- Số điện thoại: ............................................... Email: ........................................

Hai bên cùng thỏa thuận ký kết Hợp đồng lao động với các điều khoản sau:

ĐIỀU 1: VỊ TRÍ, ĐỊA ĐIỂM VÀ THỜI HẠN LÀM VIỆC
1. Loại hợp đồng: Hợp đồng lao động [xác định thời hạn ... tháng / không xác định thời hạn].
2. Thời hạn hợp đồng: Từ ngày ...../...../202... đến ngày ...../...../202...
3. Địa điểm làm việc: ............................................................................................
4. Vị trí công việc / Chức danh: ............................................................................
5. Mô tả công việc: Thực hiện các nhiệm vụ chuyên môn theo Bảng mô tả công việc đính kèm và sự phân công hợp pháp của Bên A.

ĐIỀU 2: THỜI GIỜ LÀM VIỆC VÀ NGHỈ NGƠI
1. Thời giờ làm việc: 08 giờ/ngày, từ thứ Hai đến thứ Sáu (hoặc thứ Bảy), không quá 48 giờ/tuần.
2. Thời giờ nghỉ ngơi: Nghỉ giữa giờ ít nhất 30 phút (ban ngày) hoặc 45 phút (ban đêm).
3. Làm thêm giờ: Chỉ thực hiện khi có sự thỏa thuận đồng ý của Bên B và tuân thủ đúng giới hạn quy định tại Điều 107 Bộ luật Lao động 2019.
4. Nghỉ phép năm: Bên B làm việc đủ 12 tháng được nghỉ 12 ngày phép năm hưởng nguyên lương. Cứ đủ 05 năm làm việc được tăng thêm 01 ngày.

ĐIỀU 3: TIỀN LƯƠNG, PHỤ CẤP VÀ CÁC KHOẢN BỔ SUNG
1. Mức lương chính (lương theo chức danh/công việc): ..................................... VNĐ/tháng.
2. Các khoản phụ cấp lương (trách nhiệm, chuyên cần, xăng xe, ăn trưa...): ....... VNĐ/tháng.
3. Hình thức trả lương: Chuyển khoản qua tài khoản ngân hàng của Bên B (hoặc tiền mặt).
4. Kỳ hạn trả lương: Vào ngày ..... hàng tháng. Trường hợp chậm trả từ 15 ngày trở lên, Bên A phải trả thêm tiền lãi theo quy định tại Điều 97 BLLĐ 2019.
5. Tiền làm thêm giờ: Được trả ít nhất 150% (ngày thường), 200% (ngày nghỉ hàng tuần), 300% (ngày lễ Tết) theo Điều 98 BLLĐ 2019.

ĐIỀU 4: BẢO HIỂM XÃ HỘI, BẢO HIỂM Y TẾ, BẢO HIỂM THẤT NGHIỆP
1. Bên A và Bên B có trách nhiệm tham gia đóng BHXH, BHYT, BHTN bắt buộc theo đúng quy định của Luật Bảo hiểm xã hội và Luật Việc làm.
2. Mức trích đóng được tính trên cơ sở mức lương thỏa thuận và tiền đóng bảo hiểm theo quy định pháp luật.

ĐIỀU 5: AN TOÀN VÀ VỆ SINH LAO ĐỘNG
1. Bên A có trách nhiệm trang bị đầy đủ phương tiện bảo vệ cá nhân, bảo đảm môi trường làm việc đạt tiêu chuẩn an toàn, vệ sinh lao động.
2. Bên B có nghĩa vụ tuân thủ các nội quy an toàn, quy trình làm việc và tham gia khám sức khỏe định kỳ do Bên A tổ chức.

ĐIỀU 6: QUYỀN VÀ NGHĨA VỤ CỦA CÁC BÊN
1. Nghĩa vụ của Bên B: Hoàn thành tốt công việc được giao; chấp hành nội quy lao động hợp pháp; bảo vệ bí mật kinh doanh của Bên A.
2. Quyền của Bên B: Hưởng đầy đủ tiền lương và các chế độ đãi ngộ; từ chối làm việc khi có nguy cơ đe dọa trực tiếp đến tính mạng, sức khỏe.
3. Nghĩa vụ của Bên A: Thanh toán lương đúng hạn; tôn trọng danh dự, nhân phẩm của Bên B; không được giữ bản chính giấy tờ tùy thân, văn bằng của Bên B.
4. Quyền của Bên A: Điều hành công việc; khen thưởng và xử lý kỷ luật lao động theo đúng Nội quy lao động và quy định pháp luật.

ĐIỀU 7: CHẤM DỨT HỢP ĐỒNG LAO ĐỘNG
Hợp đồng chấm dứt trong các trường hợp quy định tại Điều 34 BLLĐ 2019. Khi đơn phương chấm dứt hợp đồng, các bên có trách nhiệm tuân thủ thời hạn báo trước theo Điều 35 và Điều 36 BLLĐ 2019. Bên A có trách nhiệm thanh toán đầy đủ các khoản tiền và chốt trả sổ BHXH trong thời hạn tối đa 14 ngày làm việc.

ĐIỀU 8: ĐIỀU KHOẢN THI HÀNH
Hợp đồng này có hiệu lực kể từ ngày ký. Hợp đồng được lập thành 02 (hai) bản có giá trị pháp lý như nhau, mỗi bên giữ 01 (một) bản.

           ĐẠI DIỆN BÊN A                                   NGƯỜI LAO ĐỘNG (BÊN B)
       (Ký, ghi rõ họ tên, đóng dấu)                          (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "hop_dong_thu_viec",
        "title": "Hợp đồng thử việc",
        "tag": "Thử việc",
        "basis": "Điều 24 - 27 Bộ luật Lao động 2019",
        "summary": "Áp dụng cho thỏa thuận thử việc riêng biệt, quy định rõ thời hạn thử việc, mức lương tối thiểu 85% và quyền đơn phương hủy bỏ không bồi thường.",
        "query": "Mẫu hợp đồng thử việc chuẩn theo quy định Bộ luật Lao động 2019",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

HỢP ĐỒNG THỬ VIỆC
Số: ....../HĐTV-2026

- Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20 tháng 11 năm 2019;
- Căn cứ nhu cầu sử dụng lao động và năng lực của hai bên;

Hôm nay, ngày ..... tháng ..... năm 202..., tại: ................................................................
Chúng tôi gồm:

BÊN SỬ DỤNG LAO ĐỘNG (BÊN A):
- Tên công ty: ....................................................................................................
- Mã số thuế: ....................................................................................................
- Địa chỉ: ............................................................................................................
- Đại diện: Ông/Bà ................................................. Chức vụ: .............................

BÊN THỬ VIỆC (BÊN B):
- Họ và tên: .................................................... Ngày sinh: ....................................
- Số CCCD: ..................................................... Ngày cấp: ............. Nơi cấp: .......
- Địa chỉ: ............................................................................................................
- Điện thoại: .................................................... Email: ........................................

Hai bên thống nhất ký kết Hợp đồng thử việc với các điều khoản sau:

ĐIỀU 1: VỊ TRÍ VÀ THỜI GIAN THỬ VIỆC
1. Vị trí thử việc: ..................................................................................................
2. Địa điểm làm việc: ............................................................................................
3. Thời gian thử việc: ..... tháng (..... ngày), kể từ ngày ...../...../202... đến ngày ...../...../202...
(Ghi chú: Tối đa 60 ngày đối với công việc có trình độ CĐ/ĐH trở lên; 30 ngày đối với trình độ trung cấp, công nhân kỹ thuật; 180 ngày đối với người quản lý theo Điều 25 BLLĐ 2019).

ĐIỀU 2: NHIỆM VỤ VÀ MỤC TIÊU THỬ VIỆC
1. Bên B thực hiện các nhiệm vụ chuyên môn theo Bảng mô tả công việc được giao.
2. Bên A có trách nhiệm hướng dẫn, tạo điều kiện thuận lợi và đánh giá định kỳ kết quả thử việc của Bên B theo tiêu chí đã thống nhất.

ĐIỀU 3: THỜI GIỜ LÀM VIỆC VÀ NGHỈ NGƠI
1. Thời giờ làm việc: 08 giờ/ngày, từ thứ Hai đến thứ Sáu (hoặc thứ Bảy).
2. Nghỉ giữa ca, nghỉ hàng tuần và các ngày lễ Tết theo quy định chung của pháp luật lao động.

ĐIỀU 4: TIỀN LƯƠNG TRONG THỜI GIAN THỬ VIỆC
1. Tiền lương thử việc: ..................................... VNĐ/tháng.
(Bảo đảm ít nhất bằng 85% mức lương chính thức của công việc theo quy định tại Điều 26 BLLĐ 2019).
2. Hình thức và ngày trả lương: Chuyển khoản/tiền mặt vào ngày ..... hàng tháng.

ĐIỀU 5: HỦY BỎ HỢP ĐỒNG THỬ VIỆC
1. Trong thời gian thử việc, mỗi bên có quyền hủy bỏ hợp đồng thử việc mà không cần báo trước và không phải bồi thường nếu việc làm thử không đạt yêu cầu mà hai bên đã thỏa thuận (Điều 27 BLLĐ 2019).
2. Khi hợp đồng thử việc bị hủy bỏ, Bên A có trách nhiệm thanh toán đầy đủ tiền lương cho những ngày Bên B đã làm việc thực tế.

ĐIỀU 6: KẾT THÚC THỜI GIAN THỬ VIỆC
1. Khi kết thúc thời gian thử việc, Bên A phải thông báo kết quả thử việc cho Bên B.
2. Trường hợp thử việc đạt yêu cầu, Bên A có trách nhiệm tiến hành giao kết Hợp đồng lao động chính thức với Bên B ngay sau khi kết thúc thời gian thử việc.

Hợp đồng này được lập thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản.

            ĐẠI DIỆN BÊN A                                   NGƯỜI THỬ VIỆC (BÊN B)
       (Ký, ghi rõ họ tên, đóng dấu)                          (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "don_xin_thoi_viec",
        "title": "Đơn xin thôi việc / Chấm dứt HĐLĐ",
        "tag": "Nghỉ việc",
        "basis": "Điều 35 Bộ luật Lao động 2019",
        "summary": "Chuẩn hóa đơn xin nghỉ việc bảo đảm đúng thời hạn báo trước theo luật định, bảo toàn quyền lợi trợ cấp thôi việc và chốt sổ BHXH.",
        "query": "Mẫu đơn xin thôi việc chuẩn pháp luật bảo đảm thời hạn báo trước",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

ĐƠN XIN CHẤM DỨT HỢP ĐỒNG LAO ĐỘNG
(ĐƠN XIN THÔI VIỆC)

Kính gửi:
- Ban Giám đốc Công ty .....................................................................................
- Phòng Hành chính - Nhân sự;
- Trưởng bộ phận .................................................................................................

Tôi tên là: ........................................................... Giới tính: ...................................
Ngày sinh: ...../...../......... Số CCCD: ........................... Ngày cấp: ..........................
Chức danh / Vị trí công tác: ...................................................................................
Phòng ban / Bộ phận: ...........................................................................................
Hiện đang làm việc theo Hợp đồng lao động số: .................. ngày ký: ...../...../202...
Loại hợp đồng: [Hợp đồng xác định thời hạn ..... tháng / Hợp đồng không xác định thời hạn]

Nay tôi làm đơn này trân trọng kính đề nghị Ban Giám đốc Công ty chấp thuận cho tôi được chấm dứt Hợp đồng lao động kể từ ngày: ..... tháng ..... năm 202...

Lý do xin thôi việc:
...............................................................................................................................
(Ví dụ: Do có định hướng phát triển nghề nghiệp mới / Lý do gia đình cá nhân / Thay đổi nơi cư trú...)

Để đảm bảo quyền và lợi ích hợp pháp của hai bên theo đúng quy định tại Điều 35 Bộ luật Lao động 2019, tôi đã tuân thủ thời hạn báo trước [ít nhất 30 ngày đối với HĐ xác định thời hạn / ít nhất 45 ngày đối với HĐ không xác định thời hạn].

Tôi xin cam kết:
1. Sẵn sàng phối hợp thực hiện việc bàn giao đầy đủ, chi tiết toàn bộ công việc, tài liệu, hồ sơ chuyên môn và trang thiết bị, tài sản của Công ty trước ngày nghỉ việc chính thức.
2. Nghiêm chỉnh bảo mật các thông tin nội bộ và bí mật kinh doanh của Công ty theo quy định.

Đồng thời, tôi kính đề nghị Quý Công ty hỗ trợ:
1. Thanh toán đầy đủ tiền lương của các ngày làm việc thực tế, tiền làm thêm giờ (nếu có) và tiền phép năm chưa nghỉ hết theo quy định tại Điều 48 và Điều 113 BLLĐ 2019.
2. Hoàn tất thủ tục chốt và trả Sổ bảo hiểm xã hội cùng các giấy tờ tùy thân khác cho tôi trong thời hạn 14 ngày làm việc kể từ ngày chấm dứt hợp đồng lao động.

Tôi xin chân thành cảm ơn Ban Giám đốc và các đồng nghiệp đã luôn tạo điều kiện, hỗ trợ tôi trong suốt thời gian làm việc tại Công ty.

Kính chúc Quý Công ty ngày càng phát triển và thành công!

                                          ........., ngày ..... tháng ..... năm 202...
 Ý KIẾN CỦA TRƯỞNG BỘ PHẬN                          NGƯỜI LÀM ĐƠN
     (Ký và ghi rõ họ tên)                      (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "don_doi_luong_tro_cap",
        "title": "Đơn đề nghị thanh toán tiền lương và trợ cấp thôi việc",
        "tag": "Đòi quyền lợi",
        "basis": "Điều 46, Điều 48 & Điều 97 Bộ luật Lao động 2019",
        "summary": "Áp dụng khi người sử dụng lao động chậm trễ thanh toán tiền lương, trợ cấp hoặc chưa chốt trả sổ BHXH sau khi chấm dứt hợp đồng quá thời hạn luật định.",
        "query": "Mẫu đơn yêu cầu công ty thanh toán tiền lương và trợ cấp thôi việc",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

ĐƠN ĐỀ NGHỊ
(V/v: Yêu cầu thanh toán dứt điểm tiền lương, trợ cấp thôi việc và chốt trả sổ BHXH)

Kính gửi:
- Ban Giám đốc Công ty .....................................................................................
- Người đại diện theo pháp luật của Công ty;
- Phòng Kế toán / Phòng Nhân sự;

Tôi tên là: ........................................................... Giới tính: ...................................
Số CCCD: ........................... Ngày cấp: ................... Nơi cấp: ...............................
Địa chỉ liên hệ: ....................................................................................................
Số điện thoại: ...................................................... Email: ........................................

Tôi là nguyên người lao động tại Công ty, vị trí: .....................................................
Làm việc theo Hợp đồng lao động số: ....................... từ ngày ...../...../......... đến ngày ...../...../.........
Vào ngày ...../...../202..., tôi đã chính thức chấm dứt HĐLĐ và hoàn tất đầy đủ mọi nghĩa vụ bàn giao công việc, tài sản cho Công ty theo đúng Biên bản bàn giao đã ký.

Căn cứ quy định pháp luật:
1. Khoản 1 Điều 48 Bộ luật Lao động 2019: "Trong thời hạn 14 ngày làm việc kể từ ngày chấm dứt hợp đồng lao động, hai bên có trách nhiệm thanh toán đầy đủ các khoản tiền có liên quan đến quyền lợi của mỗi bên...".
2. Điều 46 Bộ luật Lao động 2019 về trách nhiệm chi trả trợ cấp thôi việc cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên.
3. Khoản 4 Điều 97 Bộ luật Lao động 2019 về tiền lãi do chậm trả lương.

Tuy nhiên, tính đến nay (ngày ...../...../202...), đã quá thời hạn 14 ngày làm việc nhưng Công ty vẫn chưa thực hiện thanh toán cho tôi các khoản quyền lợi hợp pháp sau:
1. Tiền lương làm việc thực tế từ ngày ...../...../202... đến ngày ...../...../202...: .................... VNĐ.
2. Tiền trợ cấp thôi việc (nếu đủ điều kiện): .................... VNĐ.
3. Tiền thanh toán các ngày nghỉ phép năm chưa nghỉ hết (..... ngày): .................... VNĐ.
4. Tiền lãi chậm trả tính theo lãi suất huy động tiền gửi ngân hàng: .................... VNĐ.
Tổng số tiền Công ty còn nợ tôi: ..................................................................... VNĐ
(Bằng chữ: .........................................................................................................).
Đồng thời, Công ty vẫn chưa hoàn tất thủ tục chốt và trả sổ BHXH cho tôi.

Bằng văn bản này, tôi kính đề nghị Ban Giám đốc Công ty:
1. Thanh toán dứt điểm toàn bộ số tiền nợ nói trên vào tài khoản ngân hàng của tôi (STK: ................................., Ngân hàng: ................................., Chủ TK: .................................) chậm nhất trước ngày ...../...../202...
2. Chốt và bàn giao trả sổ BHXH cùng các chứng từ liên quan cho tôi trước thời hạn nêu trên.

Nếu quá thời hạn nêu trên mà Công ty vẫn không giải quyết thanh toán, tôi sẽ buộc phải gửi đơn khiếu nại tới Thanh tra Sở Lao động - TB&XH và khởi kiện tại Tòa án nhân dân có thẩm quyền để yêu cầu bảo vệ quyền lợi hợp pháp, đồng thời yêu cầu cơ quan có thẩm quyền xử phạt vi phạm hành chính đối với hành vi nợ lương, chậm trả lương theo quy định tại Nghị định 12/2022/NĐ-CP.

Kính mong Ban Giám đốc quan tâm và giải quyết dứt điểm.

                                          ........., ngày ..... tháng ..... năm 202...
                                                        NGƯỜI LÀM ĐƠN
                                                    (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "thoa_thuan_nda",
        "title": "Thỏa thuận bảo mật thông tin & Bí mật kinh doanh (NDA)",
        "tag": "Bảo mật",
        "basis": "Điều 21 khoản 2 Bộ luật Lao động 2019 & Luật Sở hữu trí tuệ",
        "summary": "Quy định phạm vi bí mật kinh doanh, thời hạn bảo mật và chế tài bồi thường thiệt hại hợp pháp, tránh các điều khoản trái luật hoặc hạn chế quyền làm việc.",
        "query": "Mẫu thỏa thuận bảo mật thông tin và bí mật kinh doanh NDA trong lao động",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

THỎA THUẬN BẢO MẬT THÔNG TIN VÀ BÍ MẬT KINH DOANH
(NON-DISCLOSURE AGREEMENT - NDA)

- Căn cứ Bộ luật Dân sự số 91/2015/QH13;
- Căn cứ khoản 2 Điều 21 Bộ luật Lao động số 45/2019/QH14;
- Căn cứ Luật Sở hữu trí tuệ số 50/2005/QH11 (sửa đổi, bổ sung 2022);

Hôm nay, ngày ..... tháng ..... năm 202..., tại: ................................................................
Chúng tôi gồm:

BÊN A (BÊN CHUYỂN GIAO THÔNG TIN / CÔNG TY):
- Tên doanh nghiệp: ............................................................................................
- Đại diện: Ông/Bà ........................................ Chức vụ: ..................................
- Địa chỉ: ............................................................................................................

BÊN B (BÊN TIẾP NHẬN THÔNG TIN / NGƯỜI LAO ĐỘNG):
- Họ và tên: .................................................... Chức vụ: .....................................
- Số CCCD: ..................................................... Ngày cấp: ....................................
- Địa chỉ: ............................................................................................................

Hai bên tự nguyện thỏa thuận và cam kết thực hiện các điều khoản sau:

ĐIỀU 1: ĐỊNH NGHĨA THÔNG TIN BẢO MẬT
Thông tin bảo mật bao gồm toàn bộ các thông tin kỹ thuật, mã nguồn, bí quyết công nghệ, cơ sở dữ liệu khách hàng, chiến lược định giá, kế hoạch tài chính, tài liệu dự án chưa công bố thuộc quyền sở hữu hợp pháp của Bên A mà Bên B được tiếp cận trong quá trình làm việc.

ĐIỀU 2: NGHĨA VỤ CỦA BÊN B
1. Chỉ sử dụng Thông tin bảo mật nhằm phục vụ cho mục đích thực hiện công việc được Bên A phân công.
2. Không sao chép, trích xuất, phát tán hoặc tiết lộ bất kỳ Thông tin bảo mật nào cho bên thứ ba khi chưa có sự đồng ý bằng văn bản của Bên A.
3. Bàn giao lại toàn bộ tài liệu, dữ liệu, thiết bị lưu trữ chứa Thông tin bảo mật ngay khi chấm dứt hợp đồng lao động.

ĐIỀU 3: THỜI HẠN BẢO MẬT
Nghĩa vụ bảo mật có hiệu lực trong suốt thời gian làm việc và tiếp tục kéo dài ..... tháng (tối đa 24 tháng) kể từ ngày chấm dứt Hợp đồng lao động giữa hai bên.

ĐIỀU 4: TRÁCH NHIỆM BỒI THƯỜNG VI PHẠM
1. Trường hợp Bên B cố ý làm lộ hoặc sử dụng trái phép Thông tin bảo mật gây thiệt hại cho Bên A, Bên B phải bồi thường toàn bộ thiệt hại thực tế phát sinh theo quy định pháp luật.
2. Thỏa thuận này bảo đảm không xâm phạm quyền tự do lựa chọn việc làm của Bên B theo quy định của Hiến pháp và pháp luật lao động.

Thỏa thuận được lập thành 02 bản có giá trị như nhau, mỗi bên giữ 01 bản.

            ĐẠI DIỆN BÊN A                                   NGƯỜI LAO ĐỘNG (BÊN B)
       (Ký, ghi rõ họ tên, đóng dấu)                          (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "bien_ban_ban_giao",
        "title": "Biên bản bàn giao công việc và tài sản",
        "tag": "Bàn giao",
        "basis": "Bộ luật Lao động 2019",
        "summary": "Biên bản nghiệm thu bàn giao toàn bộ nhiệm vụ chuyên môn, hồ sơ tài liệu và tài sản, thiết bị trước khi chính thức thôi việc.",
        "query": "Mẫu biên bản bàn giao công việc và tài sản khi nghỉ việc",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

BIÊN BẢN BÀN GIAO CÔNG VIỆC VÀ TÀI SẢN

Hôm nay, ngày ..... tháng ..... năm 202..., tại Văn phòng Công ty ................................
Chúng tôi tiến hành lập Biên bản bàn giao công việc và tài sản gồm các bên:

NGƯỜI BÀN GIAO (BÊN BÀN GIAO):
- Họ và tên: .................................................... Chức vụ: .....................................
- Bộ phận: ...................................................... Số điện thoại: .............................

NGƯỜI NHẬN BÀN GIAO (BÊN NHẬN BÀN GIAO):
- Họ và tên: .................................................... Chức vụ: .....................................
- Bộ phận: ...................................................... Số điện thoại: .............................

NGƯỜI CHỨNG KIẾN (QUẢN LÝ / NHÂN SỰ):
- Họ và tên: .................................................... Chức vụ: .....................................

NỘI DUNG BÀN GIAO:

1. BÀN GIAO HỒ SƠ, TÀI LIỆU VÀ CÔNG VIỆC CHUYÊN MÔN:
- Tên công việc / Dự án: .................................... Tình trạng hiện tại: ......................
- Hồ sơ, tài liệu giấy kèm theo (liệt kê cụ thể): ........................................................
- Các đầu mối đối tác, khách hàng liên hệ: ............................................................
- Danh mục tài khoản số, file lưu trữ đám mây: ......................................................

2. BÀN GIAO TÀI SẢN, TRANG THIẾT BỊ:
- Máy tính xách tay / PC (Model, số Serial, tình trạng): ............................................
- Thẻ nhân viên, thẻ gửi xe, chìa khóa phòng làm việc: .........................................
- Các công cụ dụng cụ lao động khác: ...................................................................
Tình trạng tài sản: Tất cả hoạt động bình thường, nguyên vẹn, không hư hao.

3. QUYẾT TOÁN CÔNG NỢ, TẠM ỨNG:
- Số tiền tạm ứng đã thanh quyết toán: ................................................................. VNĐ.
- Công nợ còn lại giữa hai bên: Không còn công nợ tồn đọng.

KẾT LUẬN:
Các bên xác nhận Người bàn giao đã hoàn tất toàn bộ nghĩa vụ bàn giao hồ sơ, tài sản và công việc theo đúng quy định. Kể từ thời điểm này, Người nhận bàn giao chịu trách nhiệm tiếp quản và xử lý các công việc được bàn giao.

Biên bản được lập thành 03 bản, mỗi bên giữ 01 bản và lưu hồ sơ Nhân sự 01 bản.

     NGƯỜI BÀN GIAO              NGƯỜI NHẬN BÀN GIAO         ĐẠI DIỆN PHÒNG NHÂN SỰ
  (Ký và ghi rõ họ tên)         (Ký và ghi rõ họ tên)         (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "don_khieu_nai_lao_dong",
        "title": "Đơn khiếu nại hành vi vi phạm pháp luật lao động",
        "tag": "Khiếu nại",
        "basis": "Nghị định 24/2018/NĐ-CP & Nghị định 12/2022/NĐ-CP",
        "summary": "Gửi Chánh Thanh tra Sở Lao động - TB&XH khi quyền và lợi ích hợp pháp của người lao động bị xâm phạm nghiêm trọng.",
        "query": "Mẫu đơn khiếu nại hành vi vi phạm pháp luật lao động của người sử dụng lao động",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

ĐƠN KHIẾU NẠI
(V/v: Hành vi vi phạm pháp luật lao động của Người sử dụng lao động)

Kính gửi:
- Chánh Thanh tra Sở Lao động - Thương binh và Xã hội tỉnh/thành phố: .................
- (hoặc) Phòng Lao động - Thương binh và Xã hội quận/huyện: ...............................

NGƯỜI KHIẾU NẠI:
- Họ và tên: .................................................... Sinh ngày: ...../...../.........
- Số CCCD: ........................... Ngày cấp: ............. Nơi cấp: ...............................
- Nơi đăng ký thường trú: .................................................................................
- Nơi ở hiện nay: ............................................................................................
- Số điện thoại: ............................................... Email: ........................................

ĐỐI TƯỢNG BỊ KHIẾU NẠI:
- Tên công ty / doanh nghiệp: .............................................................................
- Người đại diện theo pháp luật: Ông/Bà ............................. Chức vụ: ...................
- Địa chỉ trụ sở: ................................................................................................
- Mã số thuế: ................................................... Điện thoại: ................................

NỘI DUNG VỤ VIỆC KHIẾU NẠI:
Tôi là người lao động làm việc tại Công ty từ ngày ...../...../......... theo HĐLĐ số: .....................
Thời gian qua, Người sử dụng lao động đã có các hành vi vi phạm nghiêm trọng pháp luật lao động đối với tôi, cụ thể như sau:
...............................................................................................................................
...............................................................................................................................
(Nêu rõ các hành vi vi phạm: Nợ lương quá hạn / Giữ bản chính bằng cấp / Bắt làm thêm giờ trái phép / Sa thải đơn phương không có lý do đúng luật / Trốn đóng BHXH...).

CĂN CỨ PHÁP LÝ VI PHẠM:
- Vi phạm quy định tại Điều ..... Bộ luật Lao động số 45/2019/QH14;
- Hành vi thuộc diện bị xử phạt vi phạm hành chính theo Điều ..... Nghị định số 12/2022/NĐ-CP ngày 17/01/2022 của Chính phủ.

YÊU CẦU GIẢI QUYẾT KHIẾU NẠI:
Kính đề nghị Quý Cơ quan tiến hành các biện pháp theo thẩm quyền:
1. Xác minh, thanh tra và kết luận về hành vi vi phạm pháp luật lao động của Công ty nêu trên.
2. Xử phạt vi phạm hành chính đối với hành vi vi phạm theo đúng quy định tại Nghị định 12/2022/NĐ-CP.
3. Buộc Công ty phải khắc phục hậu quả: Thanh toán toàn bộ các khoản tiền quyền lợi còn nợ, chốt trả sổ BHXH (hoặc trả lại bằng cấp/giấy tờ) cho tôi.

TÀI LIỆU, CHỨNG CỨ KÈM THEO:
1. Bản sao Hợp đồng lao động số: ....................................................................
2. Bản sao CCCD của Người khiếu nại;
3. Bảng thanh toán lương / Sao kê tài khoản ngân hàng thể hiện nợ lương;
4. Các văn bản, thông báo, tin nhắn, email trao đổi liên quan.

Tôi xin cam đoan toàn bộ nội dung trình bày trên là đúng sự thật và hoàn toàn chịu trách nhiệm trước pháp luật.

                                          ........., ngày ..... tháng ..... năm 202...
                                                      NGƯỜI KHIẾU NẠI
                                                    (Ký và ghi rõ họ tên)
"""
    },
    {
        "id": "giay_uy_quyen",
        "title": "Giấy ủy quyền giải quyết tranh chấp lao động",
        "tag": "Ủy quyền",
        "basis": "Bộ luật Dân sự 2015 & Bộ luật Lao động 2019",
        "summary": "Ủy quyền hợp pháp cho người đại diện tham gia quá trình hòa giải hoặc tố tụng tranh chấp lao động.",
        "query": "Mẫu giấy ủy quyền tham gia giải quyết tranh chấp lao động",
        "content": """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
-----------------

GIẤY ỦY QUYỀN
(V/v: Tham gia giải quyết tranh chấp lao động)

- Căn cứ Bộ luật Dân sự số 91/2015/QH13 ngày 24 tháng 11 năm 2015;
- Căn cứ Bộ luật Lao động số 45/2019/QH14 ngày 20 tháng 11 năm 2019;

Hôm nay, ngày ..... tháng ..... năm 202..., tại: ................................................................
Chúng tôi gồm có:

BÊN ỦY QUYỀN (BÊN A):
- Họ và tên: .................................................... Sinh ngày: ...../...../.........
- Số CCCD: ........................... Ngày cấp: ............. Nơi cấp: ...............................
- Nơi đăng ký thường trú: .................................................................................
- Nơi ở hiện nay: ............................................................................................
- Số điện thoại: ............................................... Email: ........................................

BÊN ĐƯỢC ỦY QUYỀN (BÊN B):
- Họ và tên: .................................................... Sinh ngày: ...../...../.........
- Số CCCD: ........................... Ngày cấp: ............. Nơi cấp: ...............................
- Nơi đăng ký thường trú: .................................................................................
- Nơi ở hiện nay: ............................................................................................
- Số điện thoại: ............................................... Quan hệ với Bên A: ....................

NỘI DUNG ỦY QUYỀN:
Bên A đồng ý ủy quyền cho Bên B thay mặt và nhân danh Bên A thực hiện các công việc sau:
1. Đại diện Bên A liên hệ, làm việc với Công ty ................................................... để giải quyết các vấn đề liên quan đến quan hệ lao động và tranh chấp lao động phát sinh.
2. Tham gia các buổi làm việc, đối thoại, phiên hòa giải tranh chấp lao động tại Hòa giải viên lao động, Hội đồng Trọng tài lao động, hoặc Sở/Phòng Lao động - TB&XH.
3. Cung cấp chứng cứ, tài liệu, trình bày ý kiến, ký kết các biên bản làm việc và văn bản thỏa thuận trong phạm vi ủy quyền hợp pháp.

PHẠM VI VÀ THỜI HẠN ỦY QUYỀN:
1. Bên B không được ủy quyền lại cho bất kỳ bên thứ ba nào khác nếu không có sự đồng ý bằng văn bản của Bên A.
2. Giấy ủy quyền này có hiệu lực kể từ ngày ký cho đến khi vụ việc tranh chấp lao động được giải quyết xong, hoặc khi Bên A có văn bản chấm dứt việc ủy quyền.

Hai bên cam kết hoàn toàn tự nguyện thực hiện đúng các nội dung ủy quyền và chịu trách nhiệm trước pháp luật.

          BÊN ĐƯỢC ỦY QUYỀN (BÊN B)                          BÊN ỦY QUYỀN (BÊN A)
            (Ký và ghi rõ họ tên)                            (Ký và ghi rõ họ tên)
"""
    }
]


def get_template_by_id(tpl_id: str) -> LegalTemplate | None:
    for t in LEGAL_TEMPLATES:
        if t["id"] == tpl_id:
            return t
    return None
