"""Retired helper; it must not replace the mixed-domain rows 810-915.

The linked Can Tho source is a BLL question bank and does not substantiate the
existing occupational-safety and other mixed-domain questions in that Sheet
range. Keep this module inert to prevent accidental overwrites.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/evaluation/labor_qa_sheet_snapshot.jsonl"
SOURCE_URL = (
    "https://pbgdpl.cantho.gov.vn/bo-cau-hoi-tinh-huong-va-giai-dap-phap-luat-"
    "ve-bo-luat-lao-dong-nam-2019"
)
BLL_URL = "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm"
BHXH_URL = "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm"

QUESTION_PREFIX = re.compile(r"^Câu hỏi\s*((?:\d\s*)+)\s*[:：.]?", re.I)
ARTICLE_REF = re.compile(
    r"(?:(?:điểm\s+[a-zđ]\s+)?(?:khoản\s+\d+(?:\s*,\s*(?:(?:điểm|khoản)\s+)?\d+)*\s+)?"
    r"(?:các\s+)?điều?\s+\d+(?:\s*(?:,|và)\s*\d+)*)",
    re.I,
)
ARTICLE_FALLBACKS = {
    # The published answer for this case states the rule without an article number.
    86: ["Điều 145", "Điều 146"],
}

CURRENT_OVERRIDES: dict[int, str] = {
    1: "Chị H có quyền từ chối làm việc khi có nguy cơ rõ ràng đe dọa trực tiếp tính mạng, sức khỏe trong lúc làm việc; việc đã ký hợp đồng không làm mất quyền này. Nếu tình huống đồng thời là nguy cơ mất an toàn lao động, chị cần báo ngay người phụ trách và có quyền rời nơi làm việc hoặc từ chối tiếp tục công việc theo luật. Căn cứ: điểm d khoản 1 Điều 5 Bộ luật Lao động; điểm đ khoản 1 Điều 6 Luật An toàn, vệ sinh lao động.",
    2: "Người sử dụng lao động chỉ có quyền đóng cửa tạm thời nơi làm việc theo trường hợp luật định, không được tùy ý đóng cửa. Trong đình công, việc đóng cửa chỉ được thực hiện khi không đủ điều kiện để duy trì hoạt động bình thường hoặc để bảo vệ tài sản; phải niêm yết quyết định và thông báo cho cơ quan, tổ chức có thẩm quyền ít nhất 03 ngày làm việc trước ngày đóng cửa. Căn cứ: điểm d khoản 1 Điều 6, điểm b khoản 3 Điều 203 và Điều 205 Bộ luật Lao động.",
    4: "Không đúng. Theo khoản 1 Điều 13 Bộ luật Lao động, tên gọi của giấy tờ không quyết định bản chất: nếu thỏa thuận có việc làm được trả công và có sự quản lý, điều hành, giám sát của chủ cửa hàng thì có thể được xác định là hợp đồng lao động. Chủ cửa hàng phải trả tiền công đã phát sinh; không được tự ý giữ hoặc trừ lương để thu “phí tìm người thay”. Khấu trừ lương chỉ được thực hiện trong phạm vi luật cho phép, chủ yếu để bồi thường thiệt hại do người lao động làm hư hỏng dụng cụ, thiết bị, tài sản. Hoan có thể yêu cầu giải quyết tranh chấp tiền lương; việc không có văn bản mang tên “hợp đồng lao động” không tự tước quyền yêu cầu của người lao động. Căn cứ: khoản 1 Điều 13, khoản 1 Điều 17, khoản 1 Điều 48, Điều 102 và Điều 129 Bộ luật Lao động.",
    5: "Có. Hợp đồng lao động được giao kết bằng phương tiện điện tử dưới hình thức thông điệp dữ liệu theo pháp luật về giao dịch điện tử có giá trị như hợp đồng bằng văn bản. Căn cứ: khoản 1 Điều 14 Bộ luật Lao động.",
    7: "Không. Người sử dụng lao động không được giữ bản chính giấy tờ tùy thân, văn bằng hoặc chứng chỉ của người lao động; cũng không được yêu cầu người lao động đặt cọc tiền hoặc tài sản để bảo đảm thực hiện hợp đồng. Căn cứ: khoản 1 Điều 17 Bộ luật Lao động.",
    10: "Khi hợp đồng xác định thời hạn hết hạn mà người lao động vẫn làm việc, trong 30 ngày hai bên phải ký hợp đồng mới; trong thời gian chưa ký, quyền và nghĩa vụ tiếp tục theo hợp đồng cũ. Hết 30 ngày mà không ký mới thì hợp đồng cũ trở thành không xác định thời hạn. Căn cứ: khoản 2 Điều 20 Bộ luật Lao động.",
    12: "Thời hạn thử việc 02 tháng là trong giới hạn tối đa 60 ngày đối với công việc cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên. Nhưng trả 70% lương là trái luật: lương thử việc ít nhất phải bằng 85% mức lương của công việc đó. Người lao động có thể yêu cầu trả đủ phần chênh lệch. Căn cứ: khoản 2 Điều 25 và Điều 26 Bộ luật Lao động.",
    22: "Anh D có thể đơn phương chấm dứt hợp đồng không xác định thời hạn mà không cần nêu lý do, nhưng phải báo trước ít nhất 45 ngày, trừ trường hợp luật cho phép nghỉ không cần báo trước. Nếu nghỉ đúng luật thì không phải bồi thường chỉ vì chấm dứt hợp đồng. Nếu nghỉ trái luật, người lao động không được trợ cấp thôi việc, phải bồi thường nửa tháng tiền lương và tiền lương tương ứng những ngày không báo trước; nếu đã được đào tạo thì có thể phải hoàn trả chi phí đào tạo theo thỏa thuận và luật. Căn cứ: khoản 1 Điều 35 và Điều 40 Bộ luật Lao động.",
    29: "Tình huống kết thúc hợp đồng vào tháng 7/2021 nên cần áp dụng quy định có hiệu lực tại thời điểm đó. Anh K có thể được nhận trợ cấp thôi việc theo Điều 46 Bộ luật Lao động 2019 cho thời gian làm việc chưa tham gia bảo hiểm thất nghiệp, nếu đáp ứng điều kiện; đồng thời có thể hưởng trợ cấp thất nghiệp nếu đủ điều kiện về thời gian đóng và nộp hồ sơ đúng hạn theo Điều 49, 50 Luật Việc làm 2013. Không thể tính chính xác số tiền nếu chưa biết lịch sử đóng bảo hiểm thất nghiệp, tiền lương và hồ sơ hưởng.",
    30: "Tình huống xảy ra tháng 7/2021. Khi chuyển nhượng doanh nghiệp/tài sản làm ảnh hưởng việc làm, người sử dụng lao động phải lập phương án sử dụng lao động; nếu chị T bị mất việc theo trường hợp luật định và đã làm thường xuyên từ đủ 12 tháng thì có thể được trợ cấp mất việc làm: mỗi năm làm việc được 01 tháng tiền lương, tối thiểu 02 tháng. Thời gian tính trợ cấp phải trừ thời gian đã tham gia bảo hiểm thất nghiệp và thời gian đã được trả trợ cấp tương ứng. Chị T còn có thể hưởng trợ cấp thất nghiệp nếu đủ điều kiện theo Luật Việc làm 2013. Cần kiểm tra hồ sơ chuyển nhượng, phương án sử dụng lao động, thời gian đóng bảo hiểm và tiền lương để tính mức thực tế.",
    31: "Hợp đồng lao động vô hiệu toàn bộ nếu toàn bộ nội dung trái pháp luật, người ký không đúng thẩm quyền, công việc bị pháp luật cấm hoặc thuộc trường hợp luật định khác; vô hiệu từng phần nếu chỉ một phần vi phạm mà không ảnh hưởng phần còn lại. Tòa án nhân dân có thẩm quyền tuyên bố hợp đồng vô hiệu. Căn cứ: Điều 49 và Điều 50 Bộ luật Lao động.",
    38: "Doanh nghiệp phải tổ chức đối thoại tại nơi làm việc định kỳ ít nhất mỗi năm một lần; khi một hoặc các bên yêu cầu; và khi phát sinh các vụ việc luật định, gồm trường hợp người sử dụng lao động đơn phương chấm dứt hợp đồng theo điểm a khoản 1 Điều 36, thay đổi cơ cấu/công nghệ hoặc lý do kinh tế, xây dựng thang bảng lương, quy chế thưởng, nội quy lao động và tạm đình chỉ công việc. Căn cứ: khoản 2 Điều 63 Bộ luật Lao động.",
    53: "Tiền lương là khoản người sử dụng lao động trả theo thỏa thuận để thực hiện công việc, gồm mức lương theo công việc/chức danh, phụ cấp và khoản bổ sung khác. Từ 01/01/2026, lương tối thiểu tháng/giờ lần lượt là: vùng I 5.310.000đ/25.500đ; vùng II 4.730.000đ/22.700đ; vùng III 4.140.000đ/20.000đ; vùng IV 3.700.000đ/17.800đ. Mức áp dụng phụ thuộc địa bàn làm việc và cách trả lương; cần đối chiếu đúng vùng trong phụ lục Nghị định 293/2025/NĐ-CP. Căn cứ: khoản 1 Điều 90, Điều 91 Bộ luật Lao động; Điều 3 Nghị định 293/2025/NĐ-CP.",
    72: "Không. Không được áp dụng nhiều hình thức kỷ luật cho một hành vi; nếu một người đồng thời có nhiều hành vi vi phạm thì chỉ áp dụng hình thức cao nhất tương ứng với hành vi nặng nhất. Phạt tiền hoặc cắt lương thay kỷ luật là hành vi bị cấm; trách nhiệm bồi thường thiệt hại (nếu đủ căn cứ) là vấn đề riêng, không phải hình thức kỷ luật. Điều chuyển công việc cũng không phải hình thức kỷ luật. Căn cứ: khoản 2, khoản 3 Điều 122; Điều 124, Điều 127 và Điều 129 Bộ luật Lao động.",
    82: "Nếu người lao động trở lại làm việc sau khi đã nghỉ ít nhất 04 tháng, đã báo trước, được người sử dụng lao động đồng ý và có xác nhận y tế rằng đi làm sớm không hại sức khỏe, thì vẫn được hưởng chế độ thai sản theo bảo hiểm xã hội cho thời gian nghỉ luật định, đồng thời nhận lương cho ngày đã làm. Theo quy định hiện hành từ 01/07/2026, lao động nữ sinh con thứ hai được nghỉ thai sản 07 tháng; vì vậy nếu quay lại sau 04 tháng thì không mặc nhiên chỉ còn 02 tháng—thời gian còn lại phụ thuộc trường hợp cụ thể. Căn cứ: khoản 1, khoản 4 Điều 139 Bộ luật Lao động (được sửa đổi bởi Điều 29 Luật Dân số 2025) và pháp luật BHXH.",
    83: "Có thể được hưởng chế độ ốm đau khi phải nghỉ để trực tiếp chăm sóc con dưới 07 tuổi bị ốm, nếu thuộc đối tượng BHXH bắt buộc và đáp ứng điều kiện luật định. Trong một năm, thời gian hưởng tối đa cho mỗi con là 20 ngày làm việc nếu con dưới 03 tuổi, hoặc 15 ngày nếu con từ đủ 03 đến dưới 07 tuổi; mức tiền hưởng còn phụ thuộc tiền lương đóng BHXH và giấy tờ y tế. Căn cứ: Điều 42 và Điều 44 Luật BHXH (VBHN 19/2026).",
    89: "Không. Lao động cao tuổi là người tiếp tục làm việc sau độ tuổi nghỉ hưu theo quy định, không lấy mốc 60 tuổi cố định. Năm 2026, trong điều kiện lao động bình thường, tuổi nghỉ hưu là 61 tuổi 6 tháng đối với nam và 57 tuổi đối với nữ; trường hợp nghề nặng nhọc, vùng đặc biệt hoặc suy giảm khả năng lao động có lộ trình/điều kiện khác. Căn cứ: Điều 148, Điều 169 Bộ luật Lao động và Nghị định 135/2020/NĐ-CP.",
    90: "Không đúng. Người lao động đã hưởng lương hưu nhưng tiếp tục làm việc là người lao động cao tuổi; hai bên có thể thỏa thuận ký nhiều lần hợp đồng xác định thời hạn, không bị giới hạn như quy tắc chung. Người lao động tiếp tục được hưởng lương hưu cùng tiền lương và quyền lợi theo hợp đồng; công việc phải phù hợp sức khỏe, an toàn. Căn cứ: khoản 2 Điều 20, Điều 149 Bộ luật Lao động.",
    91: "Người lao động nước ngoài làm việc tại Việt Nam về nguyên tắc phải từ đủ 18 tuổi, có năng lực hành vi dân sự đầy đủ; có trình độ/chuyên môn và sức khỏe phù hợp; không thuộc tình trạng bị truy cứu hoặc đang chấp hành hình phạt theo luật; và có giấy phép lao động, trừ trường hợp được miễn. Hồ sơ và thủ tục hiện hành thực hiện theo Nghị định 219/2025/NĐ-CP. Căn cứ: Điều 151 Bộ luật Lao động; Nghị định 219/2025/NĐ-CP.",
    92: "Doanh nghiệp chỉ được tuyển người nước ngoài vào các vị trí quản lý, điều hành, chuyên gia hoặc lao động kỹ thuật khi đáp ứng điều kiện luật định; phải giải trình nhu cầu và thực hiện thủ tục xin cấp giấy phép hoặc xác nhận miễn trước khi người lao động bắt đầu làm việc. Nghị định 219/2025/NĐ-CP hiện quy định hồ sơ, thời điểm nộp và thẩm quyền tiếp nhận; một số trường hợp được miễn giấy phép nhưng vẫn phải xin xác nhận hoặc thông báo trước. Căn cứ: Điều 152 Bộ luật Lao động; Điều 7–9, 18, 22 Nghị định 219/2025/NĐ-CP.",
    93: "Người nước ngoài làm việc tại Việt Nam không có giấy phép lao động, nếu không thuộc diện miễn, có thể bị buộc xuất cảnh hoặc trục xuất; người sử dụng lao động cũng có thể bị xử phạt và buộc khắc phục theo quy định hiện hành. Tính đến 24/09/2026, xử phạt thực hiện theo Nghị định 283/2026/NĐ-CP, có hiệu lực từ 10/09/2026. Căn cứ: Điều 153 Bộ luật Lao động; Nghị định 283/2026/NĐ-CP.",
    94: "Có. Không phải mọi người nước ngoài làm việc tại Việt Nam đều cần giấy phép. Miễn áp dụng cho các trường hợp tại khoản 3–8 Điều 154 Bộ luật Lao động và các trường hợp bổ sung tại Điều 7 Nghị định 219/2025/NĐ-CP, như một số nhà đầu tư/thành viên góp vốn từ 03 tỷ đồng, người làm việc ngắn hạn dưới 90 ngày trong năm, di chuyển nội bộ đủ điều kiện, sinh viên/thực tập sinh, tình nguyện viên, thân nhân cơ quan đại diện, người thực hiện thỏa thuận quốc tế và một số lĩnh vực giáo dục, tài chính, khoa học-công nghệ được xác nhận. Tùy diện miễn, có thể vẫn phải xin giấy xác nhận hoặc thông báo trước ít nhất 03 ngày làm việc; cần đối chiếu đúng khoản áp dụng. Căn cứ: Điều 154 Bộ luật Lao động; Điều 7–9 Nghị định 219/2025/NĐ-CP.",
    95: "Người nước ngoài kết hôn với công dân Việt Nam và sinh sống trên lãnh thổ Việt Nam thuộc trường hợp không phải cấp giấy phép lao động. Tuy nhiên, theo Nghị định 219/2025/NĐ-CP, người sử dụng lao động vẫn phải thông báo trước ít nhất 03 ngày làm việc cho cơ quan có thẩm quyền tại nơi dự kiến làm việc; không phải xin giấy phép lao động. Căn cứ: khoản 8 Điều 154 Bộ luật Lao động; khoản 4 Điều 9 Nghị định 219/2025/NĐ-CP.",
    96: "Giấy phép lao động có thể được gia hạn một lần, tối đa 02 năm, nếu đáp ứng điều kiện; hồ sơ phải nộp trước khi giấy phép hết hạn từ 10 đến 45 ngày. Không được mặc nhiên tiếp tục làm việc chỉ vì đã nộp hồ sơ; nếu giấy phép đã hết hạn thì phải chờ có giấy phép hợp lệ/thuộc diện miễn trước khi tiếp tục làm việc. Căn cứ: Điều 28, Điều 29 Nghị định 219/2025/NĐ-CP; Điều 155 Bộ luật Lao động.",
    97: "Không. Giấy phép lao động hết hiệu lực khi hợp đồng lao động chấm dứt, dù trên giấy phép còn thời hạn. Căn cứ: khoản 2 Điều 156 Bộ luật Lao động.",
    98: "Giấy phép lao động hết hiệu lực khi hết hạn; hợp đồng lao động chấm dứt; hợp đồng không đúng nội dung giấy phép; người lao động làm sai nội dung giấy phép; hợp đồng/dự án làm cơ sở cấp phép hết hạn hoặc chấm dứt; phía nước ngoài thông báo thôi cử; đơn vị sử dụng lao động chấm dứt hoạt động; hoặc giấy phép bị thu hồi. Căn cứ: Điều 156 Bộ luật Lao động.",
    103: "Người giúp việc gia đình có quyền tham gia BHXH, BHYT, nhưng không nên hiểu là tự động thuộc diện BHXH bắt buộc như lao động theo hợp đồng thông thường. Bộ luật Lao động yêu cầu người sử dụng lao động trả thêm khoản tiền tương ứng phần đóng BHXH, BHYT để người lao động chủ động tham gia. Luật BHXH hiện hành loại người giúp việc gia đình khỏi diện BHXH bắt buộc; họ có thể tham gia BHXH tự nguyện nếu đủ điều kiện. Căn cứ: khoản 2 Điều 163 Bộ luật Lao động; điểm b khoản 7 Điều 2 Luật BHXH (VBHN 19/2026).",
}

ARTICLE_OVERRIDES = {
    1: ["điểm d khoản 1 Điều 5", "điểm đ khoản 1 Điều 6"],
    2: ["điểm d khoản 1 Điều 6", "điểm b khoản 3 Điều 203", "Điều 205"],
    4: ["khoản 1 Điều 13", "khoản 1 Điều 17", "khoản 1 Điều 48", "Điều 102", "Điều 129"],
    5: ["khoản 1 Điều 14"],
    7: ["khoản 1 Điều 17"],
    10: ["khoản 2 Điều 20"],
    12: ["khoản 2 Điều 25", "Điều 26"],
    22: ["khoản 1 Điều 35", "Điều 40"],
    29: ["khoản 1 Điều 34", "Điều 46"],
    30: ["khoản 11 Điều 34", "Điều 43", "Điều 44", "Điều 47"],
    31: ["Điều 49", "Điều 50"],
    53: ["khoản 1 Điều 90", "Điều 91"],
    72: ["khoản 2, khoản 3 Điều 122", "Điều 124", "Điều 127", "Điều 129"],
    82: ["khoản 1, khoản 4 Điều 139"],
    83: ["Điều 42", "Điều 44"],
    89: ["Điều 148", "Điều 169"],
    90: ["khoản 2 Điều 20", "Điều 149"],
    91: ["Điều 151"],
    92: ["Điều 152"],
    93: ["Điều 153"],
    94: ["Điều 154"],
    95: ["khoản 8 Điều 154"],
    96: ["Điều 155"],
    97: ["Điều 156"],
    98: ["Điều 156"],
    103: ["khoản 2 Điều 163", "điểm b khoản 7 Điều 2"],
}


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def extract_cases() -> list[dict[str, str | int]]:
    raise RuntimeError(
        "Retired: the Can Tho BLL Q&A page is not the source of Sheet rows 810-915. "
        "Preserve those records and use primary-law citations instead."
    )
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "VietLaborQA-source-audit/1.0"},
    )
    html = urllib.request.urlopen(request, timeout=30).read()
    soup = BeautifulSoup(html, "html.parser")
    question_paragraphs: list[tuple[int, object, str, int]] = []

    for paragraph in soup.find_all("p"):
        content = clean_text(paragraph.get_text(" ", strip=True))
        match = QUESTION_PREFIX.match(content)
        if not match:
            continue
        ordinal = int(re.sub(r"\s", "", match.group(1)))
        question = clean_text(content[match.end():])
        question_paragraphs.append((ordinal, paragraph, question, match.end()))

    if len(question_paragraphs) != 106 or [item[0] for item in question_paragraphs] != list(range(1, 107)):
        raise RuntimeError(
            f"Expected the official source's 106 numbered questions in order; got "
            f"{len(question_paragraphs)} records."
        )

    cases: list[dict[str, str | int]] = []
    for index, (ordinal, paragraph, question, _offset) in enumerate(question_paragraphs):
        following = question_paragraphs[index + 1][1] if index + 1 < len(question_paragraphs) else None
        answer_parts: list[str] = []
        for sibling in paragraph.find_next_siblings("p"):
            if following is not None and sibling is following:
                break
            text = clean_text(sibling.get_text(" ", strip=True))
            if not text or re.fullmatch(r"Trả lời\s*[:：;]?", text, re.I):
                continue
            answer_parts.append(text)
        answer = clean_text(" ".join(answer_parts))
        answer = CURRENT_OVERRIDES.get(ordinal, answer)
        if not question or not answer:
            raise RuntimeError(f"Question {ordinal} has an empty question or answer.")

        refs: list[str] = []
        for match in ARTICLE_REF.finditer(answer):
            value = clean_text(match.group())
            if value not in refs:
                refs.append(value)
        if ordinal in ARTICLE_OVERRIDES:
            refs = ARTICLE_OVERRIDES[ordinal]
        if not refs:
            refs = ARTICLE_FALLBACKS.get(ordinal, [])
        if not refs:
            raise RuntimeError(f"Question {ordinal} has no identifiable article citation.")

        extra_laws = {
            1: "điểm đ khoản 1 Điều 6 — Luật An toàn, vệ sinh lao động số 84/2015/QH13",
            29: "Điều 49, Điều 50 — Luật Việc làm số 38/2013/QH13 (áp dụng cho tình huống chấm dứt năm 2021)",
            30: "Điều 49, Điều 50 — Luật Việc làm số 38/2013/QH13 (áp dụng cho tình huống chấm dứt năm 2021)",
            53: "Điều 3 — Nghị định số 293/2025/NĐ-CP về mức lương tối thiểu (hiệu lực từ 01/01/2026)",
            82: "Điều 29 — Luật Dân số số 113/2025/QH15; Luật BHXH hợp nhất số 19/VBHN-VPQH",
            83: "Điều 44 — Luật BHXH hợp nhất số 19/VBHN-VPQH",
            91: "Nghị định số 219/2025/NĐ-CP",
            92: "Nghị định số 219/2025/NĐ-CP",
            93: "Nghị định số 219/2025/NĐ-CP; Nghị định số 283/2026/NĐ-CP (hiệu lực từ 10/09/2026)",
            94: "Nghị định số 219/2025/NĐ-CP",
            95: "Nghị định số 219/2025/NĐ-CP",
            96: "Nghị định số 219/2025/NĐ-CP",
            97: "Nghị định số 219/2025/NĐ-CP",
            98: "Nghị định số 219/2025/NĐ-CP",
            103: "Điểm b khoản 7 Điều 2 — Luật BHXH hợp nhất số 19/VBHN-VPQH",
        }.get(ordinal)

        legal_source = (
            f"{'; '.join(refs)} — Bộ luật Lao động số 45/2019/QH14 "
            f"(Văn bản hợp nhất số 18/VBHN-VPQH)"
        )
        source_urls = [BLL_URL]
        if extra_laws:
            legal_source += f"; {extra_laws}"
            if ordinal == 1:
                source_urls.append("https://vanban.chinhphu.vn/?docid=180606&pageid=27160")
            elif ordinal in {29, 30}:
                source_urls.append("https://congbao.chinhphu.vn/van-ban/luat-so-38-2013-qh13-3071.htm")
            elif ordinal in {82}:
                source_urls.extend([
                    "https://congbao.chinhphu.vn/van-ban/luat-so-113-2025-qh15-468675.htm",
                    "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-168-2026-nd-cp-469560/65154.htm",
                    BHXH_URL,
                ])
            elif ordinal in {83, 103}:
                source_urls.append(BHXH_URL)
            elif 91 <= ordinal <= 98:
                source_urls.append("https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-219-2025-nd-cp-45798.htm")
                if ordinal == 93:
                    source_urls.append("https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm")
            elif ordinal == 53:
                source_urls.append("https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-293-2025-nd-cp-46568/59713.htm")
        legal_source += "\n" + "\n".join(dict.fromkeys(source_urls))

        cases.append({
            "sheet_row": 809 + ordinal,
            "question": question,
            "answer": answer,
            "source": legal_source,
            "question_source": "PBGDPL Cần Thơ",
            "source_question_number": ordinal,
        })

    return cases


def main() -> None:
    print(
        "Disabled: this Can Tho BLL Q&A page cannot be used to rebuild mixed-domain "
        "Sheet rows 810-915. No Sheet or snapshot data was changed."
    )
    return
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="first source question, inclusive")
    parser.add_argument("--stop", type=int, default=107, help="source question upper bound, exclusive")
    parser.add_argument("--write-snapshot", action="store_true")
    args = parser.parse_args()

    cases = extract_cases()
    if args.write_snapshot:
        rows = [json.loads(line) for line in SNAPSHOT.read_text(encoding="utf-8").splitlines()]
        by_row = {row["sheet_row"]: row for row in rows}
        for case in cases:
            row_number = int(case["sheet_row"])
            if row_number not in by_row:
                raise RuntimeError(f"Snapshot is missing physical Sheet row {row_number}.")
            by_row[row_number].update({
                "question": case["question"],
                "answer": case["answer"],
                "source": case["source"],
            })
        SNAPSHOT.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    selected = [case for case in cases if args.start <= int(case["source_question_number"]) < args.stop]
    json.dump(selected, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
