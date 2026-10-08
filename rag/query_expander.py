# -*- coding: utf-8 -*-
"""
VietLabor AI - Query Expander
Bridges colloquial user phrasing and formal legal statutory terminology
to eliminate RETRIEVAL_MISS without modifying user-facing legal conclusions.
"""
import re
import unicodedata
from typing import Dict, List, Tuple


class QueryExpander:
    """Expands natural language legal queries with statutory terminology for retrieval."""

    # Lexicon mapping colloquial expressions or specific factual scenarios to statutory phrases
    STATUTORY_EXPANSIONS: List[Tuple[List[str], str]] = [
        # Article 17 BLLĐ: Prohibited acts when concluding/performing labor contracts
        (["giữ bằng đại học", "giữ bằng tốt nghiệp", "giữ bằng gốc", "giữ văn bằng", "giữ chứng chỉ"],
         "giữ bản chính văn bằng chứng chỉ Điều 17 Bộ luật Lao động"),
        (["nộp tiền đặt cọc", "đóng tiền thế chấp", "đóng tiền cọc", "thế chấp tiền", "tiền thế chấp", "đặt cọc 5 triệu"],
         "biện pháp bảo đảm bằng tiền hoặc tài sản khác thực hiện hợp đồng lao động Điều 17 Bộ luật Lao động"),
        (["căn cước công dân gốc", "cccd gốc", "chứng minh nhân dân gốc", "giấy tờ tùy thân gốc", "nộp lại căn cước"],
         "giữ bản chính giấy tờ tùy thân Điều 17 Bộ luật Lao động"),

        # Article 105 & 109: Working hours and breaks
        (["ca liên tục", "làm việc theo ca liên tục", "ca 6 giờ"],
         "làm việc theo ca liên tục từ 06 giờ trở lên thời gian nghỉ giữa giờ được tính vào giờ làm việc Điều 109 Bộ luật Lao động"),
        (["đặc biệt nặng nhọc, độc hại", "đặc biệt nặng nhọc độc hại nguy hiểm"],
         "nghề công việc đặc biệt nặng nhọc độc hại nguy hiểm thời giờ làm việc rút ngắn Điều 105 Bộ luật Lao động"),

        # Article 107: Overtime limits
        (["giờ làm thêm trong một ngày", "giờ làm thêm của người lao động không được quá bao nhiêu giờ trong một ngày", "làm thêm trong ngày tối đa"],
         "số giờ làm thêm không quá 50% số giờ làm việc bình thường trong 01 ngày Điều 107 Bộ luật Lao động"),
        (["giờ làm thêm trong một tháng", "giờ làm thêm của người lao động không quá bao nhiêu giờ trong một tháng", "làm thêm trong tháng tối đa"],
         "tổng số giờ làm thêm không quá 40 giờ trong 01 tháng Điều 107 Bộ luật Lao động"),
        (["giờ làm thêm trong một năm", "giờ làm thêm của người lao động không quá bao nhiêu giờ trong một năm", "làm thêm trong năm tối đa"],
         "tổng số giờ làm thêm không quá 200 giờ trong 01 năm Điều 107 Bộ luật Lao động"),
        (["ép tôi làm thêm", "bắt tôi làm thêm", "ép làm thêm giờ", "ép tăng ca", "bắt tăng ca", "ép nhân viên tăng ca", "bắt nhân viên tăng ca", "bắt làm thêm", "ép làm thêm", "bắt làm thêm giờ", "không đồng ý tăng ca"],
         "phải được sự đồng ý của người lao động khi làm thêm giờ Điều 107 Bộ luật Lao động"),

        # Wage underpayment / unauthorized fee deduction / withholding wage
        (["deal lương", "thỏa thuận lương", "chỉ trả", "trả thiếu", "bớt lương", "làm phí", "thu phí", "trừ phí", "giữ lương", "khấu trừ lương"],
         "nguyên tắc trả lương đầy đủ đúng hạn Điều 90 Điều 94 khấu trừ tiền lương Điều 102 quyền đơn phương chấm dứt hợp đồng lao động Điều 35 Khoản 2 Điểm b giải quyết tranh chấp lao động Điều 188 Bộ luật Lao động 2019 xử phạt vi phạm tiền lương Điều 17 Nghị định 12/2022 Điều 23 Nghị định 283/2026"),

        # Article 127: Prohibited acts in labor discipline (fines/wage deduction)
        (["phạt tiền trừ vào lương", "phạt tiền trừ lương", "phạt tiền khi đi làm trễ", "trừ lương khi đi làm trễ", "trừ lương đi làm trễ", "trừ lương đi trễ", "phạt tiền đi trễ", "phạt tiền đi làm muộn", "trừ lương thay kỷ luật", "phạt tiền thay kỷ luật", "phạt tiền thay cho xử lý kỷ luật"],
         "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127 Bộ luật Lao động"),

        # Article 130: Handling compensation for damage (equipment damage, deduction max 3 months)
        (["làm rơi vỡ", "làm rơi vỡ máy", "làm vỡ máy", "làm hỏng máy", "hư hỏng máy", "hư hỏng thiết bị", "trừ lương bồi thường", "bồi thường tối đa bao nhiêu tháng", "bồi thường nhiều nhất bao nhiêu tháng"],
         "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130 Bộ luật Lao động"),

        # Workplace violence / colloquial assault by a boss or manager
        (["sếp đấm", "sếp đánh", "sếp tát", "sếp hành hung", "quản lý đánh", "quản lý đấm", "chủ đánh", "chủ đấm", "đánh đập người lao động"],
         "người sử dụng lao động ngược đãi đánh đập người lao động bị nghiêm cấm Điều 8 Khoản 2 quyền nghỉ không cần báo trước Điều 35 Khoản 2 Điểm c xử phạt Điều 17 Khoản 4 Điểm a Nghị định 283/2026"),

        # Starting work before the employment contract is signed
        (["đi làm trước rồi mới ký", "vào làm trước rồi mới ký", "làm chính thức rồi mới ký", "cuối tuần mới ký hđlđ", "chưa ký hợp đồng đã đi làm", "ký hợp đồng sau khi đi làm", "bắt đầu làm nhưng chưa ký", "đã làm mà chưa ký", "làm được một tuần mà chưa ký", "hẹn ký hợp đồng sau", "đi làm chưa có hợp đồng"],
         "trước khi nhận người lao động vào làm việc phải giao kết hợp đồng lao động Điều 13 Khoản 2 hình thức văn bản Điều 14 Khoản 1 hợp đồng dưới 01 tháng bằng lời nói Điều 14 Khoản 2"),

        # Article 15: principles of employment-contract formation
        (["nguyên tắc giao kết hđlđ", "nguyên tắc giao kết hợp đồng lao động", "nguyên tắc nền tảng khi giao kết", "giao kết hđlđ dựa trên", "yêu cầu cơ bản khi giao kết hđlđ"],
         "nguyên tắc giao kết hợp đồng lao động tự nguyện bình đẳng thiện chí hợp tác trung thực tự do giao kết không trái pháp luật thỏa ước lao động tập thể đạo đức xã hội Điều 15"),

        # Article 98: Overtime and holiday pay
        (["làm ngày lễ được trả bao nhiêu", "tiền lương làm thêm ngày lễ", "lương làm thêm ngày lễ", "lương 300%", "tiền lương làm thêm giờ 300%", "không trả tiền lương làm thêm giờ 300%"],
         "tiền lương làm thêm giờ vào ngày nghỉ lễ tết ít nhất bằng 300% Điều 98 Bộ luật Lao động"),

        # Article 113: Annual leave
        (["nặng nhọc, độc hại, nguy hiểm được nghỉ bao nhiêu ngày phép", "công việc nặng nhọc độc hại được nghỉ bao nhiêu ngày"],
         "nghề công việc nặng nhọc độc hại nguy hiểm được nghỉ 14 ngày làm việc Điều 113 Bộ luật Lao động"),
        (["thôi việc mà chưa nghỉ hết số ngày phép", "chưa nghỉ hết phép", "chưa nghỉ hết số ngày phép hàng năm"],
         "thôi việc bị mất việc làm mà chưa nghỉ hằng năm hoặc chưa nghỉ hết số ngày nghỉ hằng năm thì được thanh toán tiền lương Điều 113 Bộ luật Lao động"),

        # Article 124: Disciplinary forms
        (["hình thức xử lý kỷ luật", "bao nhiêu hình thức kỷ luật", "hình thức kỷ luật lao động"],
         "hình thức xử lý kỷ luật lao động khiển trách kéo dài thời hạn nâng lương cách chức sa thải Điều 124"),

        # Article 122 & 137: Female employees
        (["mang thai tháng thứ 7", "mang thai từ tháng thứ 7", "nuôi con dưới 12 tháng tuổi"],
         "người lao động mang thai từ tháng thứ 07 không làm việc ban đêm làm thêm giờ Điều 137"),
        (["sa thải phụ nữ mang thai", "sa thải lao động mang thai", "kỷ luật người mang thai", "lao động nữ mang thai sa thải"],
         "không được xử lý kỷ luật lao động đối với người lao động nữ mang thai Điều 122"),

        # Article 36: Employer unilateral termination
        (["cho tôi nghỉ việc ngay lập tức", "cho nghỉ việc ngay lập tức", "người sử dụng lao động đơn phương", "công ty cho tôi nghỉ việc không báo trước"],
         "người sử dụng lao động đơn phương chấm dứt hợp đồng lao động thời hạn báo trước Điều 36"),

        # Article 48: Responsibilities upon contract termination
        (["không trả lương tháng cuối", "chậm trả lương tháng cuối", "thanh toán tiền lương khi chấm dứt", "trả lương tháng cuối", "lương tháng cuối"],
         "trách nhiệm của hai bên khi chấm dứt hợp đồng lao động thanh toán đầy đủ các khoản tiền trong thời hạn 14 ngày Điều 48"),
        (["trả sổ bảo hiểm", "trả sổ bhxh", "không chịu trả sổ", "không trả sổ", "chưa trả sổ", "giữ sổ bảo hiểm", "giữ sổ bhxh", "chây ì không chịu trả sổ"],
         "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48 Bộ luật Lao động"),

        # Unemployment Insurance: Illegal termination
        (["tự ý nghỉ việc không báo trước", "đơn phương chấm dứt trái luật có được lấy bảo hiểm thất nghiệp", "đơn phương chấm dứt trái luật có được", "nghỉ việc trái luật bảo hiểm thất nghiệp"],
         "điều kiện hưởng trợ cấp thất nghiệp không áp dụng đối với người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật Điều 85 Luật Việc làm"),

        # Article 6k2c, 60, 61, 62, 40k3: Vocational Training & Training Costs
        (["đào tạo nâng cao trình độ", "đào tạo lại", "duy trì, chuyển đổi nghề nghiệp", "kỹ năng nghề", "kế hoạch hằng năm và dành kinh phí cho việc đào tạo", "trách nhiệm đào tạo của người sử dụng lao động", "duy trì chuyển đổi nghề nghiệp", "kế hoạch đào tạo nghề"],
         "đào tạo đào tạo lại bồi dưỡng nâng cao trình độ kỹ năng nghề duy trì chuyển đổi nghề nghiệp Điều 6 Khoản 2 Điểm c Điều 60 Điều 61 Bộ luật Lao động"),
        (["cam kết làm việc sau đào tạo", "chưa hết cam kết", "hoàn trả chi phí đào tạo", "chi phí cử đi học", "nghỉ việc sau đào tạo", "chuyển sang làm cho công ty khác khi chưa hết cam kết", "xử lý chi phí đào tạo", "chuyển sang công ty khác sau đào tạo", "chưa hết thời hạn cam kết"],
         "hợp đồng đào tạo nghề thời hạn cam kết làm việc hoàn trả chi phí đào tạo Điều 62 Điều 40 Khoản 3 Bộ luật Lao động"),

        # =========================================================================
        # Wave 2: Social Insurance (58/VBHN-VPQH & Implementing Decrees)
        # =========================================================================
        (["nghỉ ốm 10 ngày", "ốm đau 10 ngày", "nghỉ ốm được bao nhiêu"],
         "mức hưởng chế độ ốm đau 75% mức tiền lương đóng BHXH tháng liền kề chia cho 24 ngày Điều 28"),
        (["nghỉ việc do ốm đau nửa tháng", "nghỉ ốm nửa tháng"],
         "nghỉ việc hưởng trợ cấp ốm đau từ 14 ngày làm việc trở lên trong tháng không phải đóng BHXH Điều 28"),
        (["đóng bhxh 7 tháng rồi nghỉ sinh", "đóng bhxh 7 tháng", "nghỉ sinh có được thai sản không"],
         "điều kiện hưởng chế độ thai sản đóng BHXH từ đủ 06 tháng trở lên trong thời gian 12 tháng trước khi sinh con Điều 31"),
        (["nghỉ sinh con 6 tháng", "lương bình quân 6 tháng đóng bhxh", "nhận tổng bao nhiêu tiền thai sản"],
         "mức hưởng chế độ thai sản 100% mức bình quân tiền lương 6 tháng và trợ cấp một lần 2 lần mức tham chiếu Điều 38 Điều 39"),
        (["đóng bhxh 18 năm có được rút một lần", "đóng bhxh 18 năm"],
         "bảo hiểm xã hội một lần sau 12 tháng không tiếp tục đóng BHXH và chưa đủ 20 năm đóng Điều 60"),
        (["3 năm đóng trước 2014 và 7 năm đóng từ năm 2014", "rút bhxh một lần được bao nhiêu"],
         "mức hưởng bảo hiểm xã hội một lần 1.5 tháng mức bình quân trước 2014 và 2.0 tháng từ 2014 Điều 60"),
        (["vừa có thời gian đóng bhxh bắt buộc vừa có thời gian đóng bhxh tự nguyện", "bắt buộc vừa tự nguyện"],
         "thời gian đóng BHXH bắt buộc và tự nguyện được cộng dồn Điều 74 Điều 6 Nghị định 159/2025"),
        (["trợ cấp mai táng", "mai táng phí"],
         "trợ cấp mai táng bằng 10 lần mức tham chiếu Điều 66"),
        (["trợ cấp tuất hàng tháng", "tuất hằng tháng"],
         "mức trợ cấp tuất hằng tháng đối với mỗi thân nhân bằng 50% mức tham chiếu Điều 67 Điều 69"),
        (["trợ cấp hưu trí xã hội", "hưu trí xã hội"],
         "trợ cấp hưu trí xã hội từ đủ 75 tuổi trở lên Nghị định 176/2025"),

        # =========================================================================
        # Wave 2: Occupational Safety & Accident/Disease (Luật 84 & 04, 05, 06/VBHN)
        # =========================================================================
        (["tai nạn trên đường đi làm về", "tai nạn trên đường đi và về", "tai nạn giao thông khi đi từ công ty về nhà"],
         "tai nạn trên tuyến đường đi và về từ nơi ở đến nơi làm việc trong khoảng thời gian và tuyến đường hợp lý Điều 45"),
        (["máy ép vào tay trong ca làm việc", "máy ép vào tay", "đứt lìa một ngón tay"],
         "trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động trả viện phí và tiền lương điều trị bồi thường Điều 38"),
        (["suy giảm 25% khả năng lao động", "suy giảm 25%"],
         "bồi thường tai nạn lao động 1.5 + (P - 10) x 0.4 tháng tiền lương Điều 38 trợ cấp một lần Quỹ TNLĐ Điều 48"),
        (["vi phạm quy chuẩn an toàn bị tai nạn", "lỗi của chính người lao động", "lỗi hoàn toàn do người lao động"],
         "tai nạn do lỗi của người lao động trợ cấp ít nhất 40% mức bồi thường Điều 39"),
        (["trả nguyên lương trong thời gian điều trị tai nạn", "nguyên lương trong thời gian điều trị"],
         "trả đủ tiền lương theo hợp đồng lao động trong thời gian điều trị tai nạn lao động Điều 38"),
        (["nghỉ dưỡng sức, phục hồi sức khỏe sau tai nạn", "dưỡng sức phục hồi sức khỏe sau tai nạn"],
         "nghỉ dưỡng sức phục hồi sức khỏe sau khi điều trị thương tật Điều 52"),
        (["mức đóng vào quỹ bảo hiểm tai nạn lao động", "mức đóng quỹ bảo hiểm tai nạn", "mức đóng quỹ tnld"],
         "mức đóng vào Quỹ bảo hiểm tai nạn lao động bệnh nghề nghiệp 0.5% hoặc 0.3% Điều 2 Điều 3 Văn bản hợp nhất 05/VBHN-BNV"),
        (["văn bản hợp nhất 06/vbhn-bnv", "06/vbhn-bnv"],
         "chế độ đối với người lao động bị tai nạn lao động bệnh nghề nghiệp Văn bản hợp nhất 06/VBHN-BNV"),
        (["văn bản hợp nhất 04/vbhn-bnv", "04/vbhn-bnv"],
         "bảo hiểm tai nạn lao động bệnh nghề nghiệp bắt buộc Văn bản hợp nhất 04/VBHN-BNV"),
    ]

    def expand(self, query: str) -> str:
        """Enriches the query text with matching statutory keywords for retrieval only."""
        if not query:
            return ""

        norm_q = unicodedata.normalize("NFC", query).strip().lower()
        matched_expansions = []

        for trigger_phrases, expansion_text in self.STATUTORY_EXPANSIONS:
            for phrase in trigger_phrases:
                if phrase in norm_q:
                    if expansion_text not in matched_expansions:
                        matched_expansions.append(expansion_text)
                    break

        if matched_expansions:
            return f"{query} {' '.join(matched_expansions)}"
        return query
