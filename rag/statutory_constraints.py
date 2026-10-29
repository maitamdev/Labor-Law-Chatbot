# -*- coding: utf-8 -*-
"""
VietLabor AI - Generic Statutory Constraint Engine.

Why this module exists
----------------------
Retrieval ranks provisions by surface similarity. A question such as
"con dưới 1 tuổi ... phải báo trước 45 ngày phải không?" matches Article 36
(it literally contains "45 ngày") while the provision that actually decides the
case - the prohibition in Article 37/137 - shares no keywords with it.

Instead of writing one hard-coded answer per question (which hijacks every
similar-looking question and breaks on the next variant), this engine encodes
*legal structure* that holds for every question:

* Protective / prohibiting provisions that override general rules
  (protected employees, prohibited sanctions, statutory caps).
* Pre-conditions that must be checked before a procedural rule applies
  (valid termination ground before notice period, transfer limits...).
* Mutually exclusive regimes (severance vs. redundancy allowance).

For every question the engine:
1. ``plan()``   - decides which checks fire (from user facts and from the
   provisions retrieval already selected) and which verified chunks must be
   placed in the evidence context.
2. ``prompt_block()`` - tells the model which [E#] blocks it must reconcile
   before concluding.
3. ``audit()``  - verifies the generated answer actually addressed each
   fact-triggered check; the chain regenerates or appends verbatim statutory
   text when it did not.

All chunk IDs below exist in data/processed/legal_documents_v3.jsonl.
The instructions only point the model at the injected provisions; the model
must still ground every statement in the evidence text.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

BLLD = "VBHN_18_2026"
ND145 = "ND_145_2020"
ATVSLD = "L_84_2015"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower()
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Reusable fact patterns (Vietnamese, colloquial forms included)
# ---------------------------------------------------------------------------
P_MATERNITY = (
    r"mang thai|có thai|có bầu|đang bầu|bầu \d|thai sản|khám thai|dưỡng thai|sảy thai|"
    r"nuôi con (nhỏ )?dưới (12|mười hai) tháng|nuôi con nhỏ|"
    r"con (nhỏ |đẻ )?(dưới|chưa đủ|chưa tròn|chưa được) ?(1|một|12|mười hai) ?(tuổi|tháng)|"
    r"con mới sinh|con sơ sinh|mới sinh con|vừa sinh|cho con bú"
)
P_TERMINATION = (
    r"chấm dứt|sa thải|đuổi việc|đuổi|cho nghỉ|cho thôi việc|buộc thôi việc|bắt nghỉ|ép nghỉ|"
    r"thôi việc|nghỉ việc|cắt hợp đồng|hủy hợp đồng|đơn phương|kỷ luật|"
    r"không ký (tiếp|lại|hợp đồng)|không gia hạn|hết hạn hợp đồng|báo trước|cắt giảm|"
    r"giảm biên chế|mất việc|không cho (làm|đi làm)"
)
P_EMPLOYER_ACTS = (
    r"(công ty|doanh nghiệp|sếp|giám đốc|chủ|cấp trên|nhà máy|xưởng|cửa hàng|bên sử dụng|người sử dụng lao động|nsdlđ)"
    r".{0,60}(cho (tôi |em |mình |bạn |chị |anh |nhân viên |người lao động )?(nghỉ|thôi việc)|đuổi|chấm dứt|"
    r"cho thôi|bắt nghỉ|ép nghỉ|không cho (làm|đi làm)|cắt hợp đồng|không ký|quyết định (cho )?nghỉ)"
)
P_EMPLOYEE_QUITS = (
    r"(tôi|em|mình|nhân viên|người lao động|nlđ|bạn|chị|anh)\s.{0,25}"
    r"(muốn |xin |tự |định |sẽ )(nghỉ việc|thôi việc|nghỉ làm|bỏ việc|chấm dứt)|xin nghỉ việc|nộp đơn (xin )?nghỉ|"
    r"tự ý nghỉ|nghỉ ngang|đơn phương nghỉ"
)


@dataclass(frozen=True)
class LegalCheck:
    """A statutory reasoning constraint that applies to every matching question."""
    check_id: str
    title: str
    inject_ids: Tuple[str, ...]
    instruction: str
    # Query trigger: every group must match (AND); inside a group any alternative (regex OR).
    query_all: Tuple[str, ...] = ()
    query_none: Tuple[str, ...] = ()
    # Article trigger: fires if retrieval already selected any of these (doc_id, article).
    article_any: Tuple[Tuple[str, str], ...] = ()
    # Article trigger requiring all listed articles to be selected.
    article_all: Tuple[Tuple[str, str], ...] = ()
    # Answer audit (only for fact/query-triggered firing): answer must match this regex.
    audit_pattern: str = ""
    # Answer audit: a conclusion matching this regex contradicts the statute
    # for the facts given (e.g. denying a right the law grants unconditionally).
    contradiction_pattern: str = ""
    # Statute-restating conclusion shown instead of a contradicting answer when
    # the model still contradicts the statute after the correction retry.
    safe_conclusion: str = ""
    priority: int = 5  # lower = more important (survives the context budget first)


CHECKS: Tuple[LegalCheck, ...] = (
    LegalCheck(
        check_id="PROTECTED_MATERNITY",
        title="Bảo vệ lao động nữ mang thai, nghỉ thai sản, nuôi con dưới 12 tháng tuổi",
        inject_ids=(f"{BLLD}#d37-k3", f"{BLLD}#d137-k3", f"{BLLD}#d122-k4-d", f"{BLLD}#d39"),
        instruction=(
            "Người lao động thuộc diện được bảo vệ (mang thai/nghỉ thai sản/nuôi con dưới 12 tháng). "
            "PHẢI kết luận điều này TRƯỚC mọi quy định về căn cứ hay thời hạn báo trước: đối chiếu Khoản 3 Điều 37 "
            "(không được đơn phương chấm dứt), Khoản 3 Điều 137 (không được sa thải/đơn phương chấm dứt vì lý do này, "
            "trường hợp ngoại lệ và quyền ưu tiên giao kết HĐLĐ mới khi hết hạn), Điểm d Khoản 4 Điều 122 (không được xử lý kỷ luật). "
            "Có báo trước theo Điều 36 cũng không làm việc chấm dứt trở nên hợp pháp; vi phạm là trái pháp luật theo Điều 39."
        ),
        query_all=(P_MATERNITY, P_TERMINATION),
        audit_pattern=r"điều 37|điều 137|điều 122",
        contradiction_pattern=(
            r"(công ty|người sử dụng lao động|nsdlđ|doanh nghiệp) (vẫn |hoàn toàn )?(được|có quyền) "
            r"(đơn phương )?(chấm dứt|sa thải|cho (bạn |người lao động )?nghỉ)"
        ),
        safe_conclusion=(
            "Theo Khoản 3 Điều 37 Bộ luật Lao động 2019, người sử dụng lao động không được thực hiện quyền đơn phương chấm dứt "
            "hợp đồng theo Điều 36 đối với lao động nữ mang thai, đang nghỉ thai sản hoặc nuôi con dưới 12 tháng tuổi; "
            "Khoản 3 Điều 137 cấm sa thải hoặc đơn phương chấm dứt vì lý do kết hôn, mang thai, nghỉ thai sản, nuôi con "
            "dưới 12 tháng tuổi (trừ các ngoại lệ nêu tại khoản này, như người sử dụng lao động là cá nhân chết, bị tuyên bố "
            "mất năng lực hành vi dân sự, mất tích hoặc người sử dụng lao động không phải là cá nhân chấm dứt hoạt động). "
            "Chấm dứt trái các quy định này là đơn phương chấm dứt trái pháp luật theo Điều 39."
        ),
        priority=0,
    ),
    LegalCheck(
        check_id="PROTECTED_SICKNESS",
        title="Bảo vệ người lao động đang điều trị ốm đau, tai nạn",
        inject_ids=(f"{BLLD}#d37-k1", f"{BLLD}#d36-k1-b", f"{BLLD}#d122-k4-a"),
        instruction=(
            "Người lao động đang ốm đau/tai nạn/điều trị: đối chiếu Khoản 1 Điều 37 (không được đơn phương chấm dứt khi đang "
            "điều trị theo chỉ định, trừ trường hợp điểm b khoản 1 Điều 36 - đã điều trị đủ thời hạn luật định) và điểm a "
            "Khoản 4 Điều 122 (không được xử lý kỷ luật khi đang nghỉ ốm đau) trước khi kết luận."
        ),
        query_all=(r"ốm|bệnh|nằm viện|nhập viện|điều trị|tai nạn|phẫu thuật|mổ|điều dưỡng", P_TERMINATION),
        audit_pattern=r"điều 37|điều 122|điều 36",
        priority=0,
    ),
    LegalCheck(
        check_id="PROTECTED_ON_LEAVE",
        title="Không được đơn phương chấm dứt khi người lao động đang nghỉ hằng năm, nghỉ việc riêng",
        inject_ids=(f"{BLLD}#d37-k2", f"{BLLD}#d122-k4-a"),
        instruction=(
            "Người lao động đang nghỉ hằng năm/nghỉ việc riêng/nghỉ được đồng ý: đối chiếu Khoản 2 Điều 37 và điểm a Khoản 4 Điều 122."
        ),
        query_all=(r"nghỉ phép|nghỉ hằng năm|nghỉ hàng năm|phép năm|nghỉ việc riêng|nghỉ không lương|nghỉ cưới|nghỉ tang", P_TERMINATION),
        audit_pattern=r"điều 37|điều 122",
        priority=1,
    ),
    LegalCheck(
        check_id="EMPLOYER_TERMINATION_TEST",
        title="Điều kiện để người sử dụng lao động chấm dứt hợp đồng hợp pháp",
        inject_ids=(f"{BLLD}#d39", f"{BLLD}#d41-k1", f"{BLLD}#d37-k1", f"{BLLD}#d37-k2", f"{BLLD}#d37-k3"),
        instruction=(
            "Khi người sử dụng lao động chấm dứt HĐLĐ phải kiểm tra lần lượt: (1) lý do có thuộc đúng một căn cứ luật định "
            "(Khoản 1 Điều 36, Điều 42, 43 hoặc kỷ luật sa thải Điều 125) không; (2) người lao động có thuộc trường hợp cấm "
            "tại Điều 37 không; (3) có báo trước đúng thời hạn không. Thiếu một điều kiện là đơn phương trái pháp luật "
            "(Điều 39) và người sử dụng lao động phải thực hiện nghĩa vụ tại Điều 41."
        ),
        query_all=(P_EMPLOYER_ACTS,),
        query_none=(r"sa thải|kỷ luật",),
        audit_pattern=r"điều 36|điều 37|điều 39|điều 41|điều 42|điều 125",
        priority=2,
    ),
    LegalCheck(
        check_id="NO_WORK_REDUNDANCY",
        title="Hết việc, không còn vị trí, cắt giảm lao động",
        inject_ids=(f"{BLLD}#d42-k3", f"{BLLD}#d42-k6", f"{BLLD}#d47-k1", f"{BLLD}#d36-k1-c", f"{BLLD}#d42-k5"),
        instruction=(
            "\"Hết việc/không còn vị trí\" tự nó không phải căn cứ chấm dứt. Chỉ hợp pháp khi thuộc điểm c Khoản 1 Điều 36 "
            "(thiên tai, hỏa hoạn, dịch bệnh, địch họa, di dời/thu hẹp theo yêu cầu cơ quan nhà nước, đã tìm mọi biện pháp khắc phục) "
            "hoặc thay đổi cơ cấu, công nghệ, lý do kinh tế theo Điều 42 (phương án sử dụng lao động, ưu tiên đào tạo lại, "
            "trao đổi với tổ chức đại diện và thông báo trước 30 ngày theo Khoản 6 Điều 42, trả trợ cấp mất việc làm theo Điều 47)."
        ),
        query_all=(
            r"không (còn )?(có )?việc|hết việc|vị trí.{0,25}(không còn|bị (bỏ|cắt|xóa|giải thể))|cắt giảm (nhân sự|lao động|biên chế|người)|"
            r"giảm biên chế|tái cơ cấu|cơ cấu lại|thay đổi cơ cấu|thu hẹp sản xuất|lý do kinh tế|dư thừa lao động|sáp nhập",
        ),
        audit_pattern=r"điều 42|điều 36|điều 47",
        priority=1,
    ),
    LegalCheck(
        check_id="ALLOWANCE_EXCLUSION",
        title="Trợ cấp thôi việc và trợ cấp mất việc làm không hưởng đồng thời",
        inject_ids=(f"{BLLD}#d46-k1", f"{BLLD}#d47-k1", f"{ND145}#d8-k1", f"{ND145}#d8-k2"),
        instruction=(
            "Trợ cấp thôi việc (Điều 46, Khoản 1 Điều 8 Nghị định 145/2020/NĐ-CP) và trợ cấp mất việc làm (Điều 47, Khoản 2 Điều 8 "
            "Nghị định 145/2020/NĐ-CP) gắn với các căn cứ chấm dứt KHÁC NHAU của Điều 34. Với một lần chấm dứt, người lao động chỉ "
            "thuộc một trong hai chế độ, không hưởng đồng thời cả hai. Phải xác định căn cứ chấm dứt trước rồi mới kết luận khoản trợ cấp."
        ),
        query_all=(r"trợ cấp thôi việc|tiền thôi việc", r"(trợ cấp|tiền) mất việc|thôi việc và (trợ cấp )?mất việc"),
        article_all=((BLLD, "46"), (BLLD, "47")),
        audit_pattern=(
            r"không (được )?(hưởng|nhận|chi trả|trả) (đồng thời|cùng lúc|cả hai)|không đồng thời|không cùng lúc|"
            r"chỉ (được )?(hưởng|nhận) (một|1)|loại trừ|không thể (hưởng|nhận) cả|một trong hai"
        ),
        priority=0,
    ),
    LegalCheck(
        check_id="SEVERANCE_CONDITIONS",
        title="Điều kiện hưởng trợ cấp thôi việc",
        inject_ids=(f"{BLLD}#d46-k1", f"{ND145}#d8-k1", f"{BLLD}#d46-k2"),
        instruction=(
            "Trợ cấp thôi việc chỉ áp dụng khi làm việc thường xuyên từ đủ 12 tháng và HĐLĐ chấm dứt theo các khoản 1, 2, 3, 4, 6, 7, 9, 10 "
            "Điều 34; có các trường hợp loại trừ tại Khoản 1 Điều 8 Nghị định 145/2020/NĐ-CP; thời gian tham gia bảo hiểm thất nghiệp "
            "không được tính (Khoản 2 Điều 46)."
        ),
        query_all=(r"trợ cấp thôi việc",),
        article_any=((BLLD, "46"),),
        priority=3,
    ),
    LegalCheck(
        check_id="REDUNDANCY_CONDITIONS",
        title="Điều kiện hưởng trợ cấp mất việc làm",
        inject_ids=(f"{BLLD}#d47-k1", f"{ND145}#d8-k2", f"{BLLD}#d42-k5"),
        instruction=(
            "Trợ cấp mất việc làm chỉ áp dụng khi chấm dứt theo Khoản 11 Điều 34 (cho thôi việc theo Điều 42, 43) và người lao động "
            "làm việc thường xuyên từ đủ 12 tháng; mức hưởng và mức tối thiểu theo Khoản 1 Điều 47."
        ),
        query_all=(r"mất việc làm|trợ cấp mất việc",),
        article_any=((BLLD, "47"),),
        priority=3,
    ),
    LegalCheck(
        check_id="DISCIPLINE_PROCEDURE",
        title="Điều kiện, trình tự xử lý kỷ luật và sa thải",
        inject_ids=(
            f"{BLLD}#d122-k1-a", f"{BLLD}#d125-k1", f"{BLLD}#d122-k4", f"{BLLD}#d125-k2",
            f"{BLLD}#d122-k1", f"{BLLD}#d125-k3", f"{BLLD}#d122-k1-d", f"{BLLD}#d125-k4",
        ),
        instruction=(
            "Sa thải chỉ được áp dụng khi hành vi thuộc đúng một trường hợp liệt kê tại Điều 125. Mọi hình thức kỷ luật phải tuân thủ "
            "Khoản 1 Điều 122 (chứng minh lỗi, có tổ chức đại diện tham gia, người lao động có mặt và được bào chữa, lập biên bản) và "
            "không được xử lý trong các thời gian tại Khoản 4 Điều 122."
        ),
        query_all=(r"sa thải|kỷ luật|khiển trách|cách chức|kéo dài (thời hạn )?nâng lương",),
        article_any=((BLLD, "125"), (BLLD, "124")),
        audit_pattern=r"điều 125|điều 122|điều 124",
        priority=1,
    ),
    LegalCheck(
        check_id="NO_FINES_WAGE_DEDUCTION",
        title="Cấm phạt tiền, cắt lương; giới hạn khấu trừ lương",
        inject_ids=(f"{BLLD}#d127-k2", f"{BLLD}#d102-k1", f"{BLLD}#d102-k3"),
        instruction=(
            "Đối chiếu Khoản 2 Điều 127 (cấm phạt tiền, cắt lương thay việc xử lý kỷ luật) và Điều 102 (chỉ khấu trừ lương để bồi thường "
            "thiệt hại tài sản theo Điều 129, người lao động được biết lý do, mức khấu trừ tối đa theo Khoản 3)."
        ),
        query_all=(
            r"phạt tiền|bị phạt|phạt \d|phạt.{0,20}(nghìn|ngàn|triệu|đồng|tiền)|trừ.{0,15}lương|cắt lương|khấu trừ|trừ tiền|"
            r"phạt (đi )?(trễ|muộn)|giữ lương|đền tiền|bồi thường.{0,20}(lương|trừ)",
        ),
        audit_pattern=r"điều 127|điều 102",
        priority=1,
    ),
    LegalCheck(
        check_id="WORK_TRANSFER_LIMITS",
        title="Giới hạn chuyển người lao động làm công việc khác",
        inject_ids=(f"{BLLD}#d29-k1", f"{BLLD}#d33-k3", f"{BLLD}#d29-k3", f"{BLLD}#d29-k4"),
        instruction=(
            "Chỉ được tạm thời chuyển người lao động làm công việc khác so với HĐLĐ khi có lý do tại Khoản 1 Điều 29, không quá 60 ngày "
            "làm việc cộng dồn trong 01 năm (trừ khi người lao động đồng ý bằng văn bản); tiền lương theo Khoản 3 Điều 29. Muốn thay đổi "
            "lâu dài phải sửa đổi HĐLĐ; không thỏa thuận được thì tiếp tục thực hiện HĐLĐ đã giao kết (Khoản 3 Điều 33). Việc người lao "
            "động không đồng ý thay đổi lâu dài công việc không phải là căn cứ chấm dứt HĐLĐ."
        ),
        query_all=(
            r"chuyển (sang |qua )?(làm )?(công việc|việc|vị trí|bộ phận|chỗ|phòng) khác|điều chuyển|luân chuyển|"
            r"(sắp xếp|bố trí|giao) (công )?việc khác|làm việc khác|đổi vị trí|chuyển công tác|"
            r"chuyển (tôi|em|mình|nhân viên|người lao động|bạn|chị|anh)?.{0,15}(sang|qua|xuống|về) "
            r"(bộ phận|phòng|kho|vị trí|công việc|xưởng|chi nhánh|tổ|ca|làm)",
        ),
        article_any=((BLLD, "29"),),
        audit_pattern=r"điều 29|điều 33",
        priority=1,
    ),
    LegalCheck(
        check_id="PROBATION_RULES",
        title="Quy định về thử việc",
        inject_ids=(
            f"{BLLD}#d25", f"{BLLD}#d26", f"{BLLD}#d25-k1", f"{BLLD}#d25-k2", f"{BLLD}#d25-k3", f"{BLLD}#d25-k4",
            f"{BLLD}#d27-k2", f"{BLLD}#d24-k3",
        ),
        instruction=(
            "Thử việc: thời gian tối đa theo Điều 25 tùy loại công việc và chỉ được thử việc 01 lần với một công việc; tiền lương ít nhất "
            "85% (Điều 26); trong thời gian thử việc mỗi bên có quyền hủy bỏ không cần báo trước, không phải bồi thường (Khoản 2 Điều 27); "
            "không áp dụng thử việc với HĐLĐ dưới 01 tháng (Khoản 3 Điều 24)."
        ),
        query_all=(r"thử việc",),
        audit_pattern=r"điều 24|điều 25|điều 26|điều 27",
        priority=2,
    ),
    LegalCheck(
        check_id="FIXED_TERM_RENEWAL",
        title="Ký tiếp hợp đồng xác định thời hạn",
        inject_ids=(f"{BLLD}#d20-k2-a", f"{BLLD}#d20-k2-b", f"{BLLD}#d20-k2-c"),
        instruction=(
            "Khi HĐLĐ xác định thời hạn hết hạn mà vẫn làm việc: đối chiếu Khoản 2 Điều 20 (thời hạn 30 ngày ký HĐLĐ mới, hậu quả nếu "
            "không ký, chỉ được ký thêm 01 lần HĐLĐ xác định thời hạn, sau đó phải ký HĐLĐ không xác định thời hạn và các ngoại lệ)."
        ),
        query_all=(
            r"ký (tiếp|lại|thêm|mới)|tái ký|gia hạn hợp đồng|hết hạn hợp đồng|hợp đồng hết hạn|"
            r"hợp đồng (lần|thứ) ?(2|3|hai|ba)|ký (mấy|bao nhiêu) lần",
        ),
        audit_pattern=r"điều 20",
        priority=2,
    ),
    LegalCheck(
        check_id="OVERTIME_RULES",
        title="Điều kiện làm thêm giờ và tiền lương làm thêm giờ",
        inject_ids=(f"{BLLD}#d107-k2-a", f"{BLLD}#d107-k2-b", f"{BLLD}#d107-k2-c", f"{BLLD}#d98-k1-a", f"{BLLD}#d98-k1-b", f"{BLLD}#d98-k1-c"),
        instruction=(
            "Làm thêm giờ phải được người lao động đồng ý và trong giới hạn tại Khoản 2 Điều 107; tiền lương làm thêm giờ tối thiểu theo "
            "Khoản 1 Điều 98. Từ chối làm thêm khi chưa đồng ý không phải là vi phạm."
        ),
        query_all=(r"làm thêm|tăng ca|thêm giờ|\bot\b|overtime|làm ngoài giờ",),
        audit_pattern=r"điều 107|điều 98",
        priority=2,
    ),
    LegalCheck(
        check_id="EMPLOYEE_RESIGNATION",
        title="Người lao động đơn phương chấm dứt hợp đồng",
        inject_ids=(f"{BLLD}#d35-k1-a", f"{BLLD}#d35-k1-b", f"{BLLD}#d35-k1-c", f"{BLLD}#d40-k1", f"{BLLD}#d40-k2"),
        instruction=(
            "Người lao động đơn phương chấm dứt phải báo trước theo Khoản 1 Điều 35, trừ các trường hợp không cần báo trước tại Khoản 2 "
            "Điều 35. Nghỉ không đúng quy định là trái pháp luật (Điều 39) và chịu hậu quả tại Điều 40."
        ),
        query_all=(P_EMPLOYEE_QUITS,),
        query_none=(P_EMPLOYER_ACTS,),
        article_any=((BLLD, "35"),),
        audit_pattern=r"điều 35",
        priority=2,
    ),
    LegalCheck(
        check_id="MISASSIGNED_WORK_TERMINATION",
        title="Đối chiếu ngoại lệ báo trước khi không được bố trí đúng công việc",
        inject_ids=(f"{BLLD}#d35-k2-a", f"{BLLD}#d29-k1", f"{BLLD}#d40-k1", f"{BLLD}#d40-k2"),
        instruction=(
            "Trước quy định báo trước thông thường, phải đối chiếu điểm a Khoản 2 Điều 35: "
            "không được bố trí đúng công việc, địa điểm hoặc điều kiện đã thỏa thuận, trừ trường hợp tại Điều 29. "
            "Kiểm tra căn cứ, thời hạn và sự đồng ý khi chuyển công việc theo Điều 29. "
            "Chỉ áp dụng nghĩa vụ bồi thường theo Điều 40 khi xác định việc đơn phương chấm dứt là trái pháp luật."
        ),
        query_all=(
            r"không (được )?bố trí.{0,30}đúng|không đúng (công việc|hợp đồng|thỏa thuận)|"
            r"làm công việc khác|phải làm công việc của|làm bốc vác|"
            r"bố trí công việc theo đúng hợp đồng|kiến nghị.{0,40}bố trí công việc",
            P_EMPLOYEE_QUITS,
        ),
        query_none=(P_EMPLOYER_ACTS,),
        audit_pattern=r"điểm a.{0,30}(khoản 2|điều 35)|khoản 2.{0,20}điều 35",
        priority=0,
    ),
    LegalCheck(
        check_id="WAGE_PAYMENT_DELAY",
        title="Chậm trả, nợ lương",
        inject_ids=(f"{BLLD}#d94-k1", f"{BLLD}#d97-k4", f"{BLLD}#d35-k2-b"),
        instruction=(
            "Lương phải trả đầy đủ, đúng hạn (Khoản 1 Điều 94). Chỉ được chậm khi bất khả kháng và đã tìm mọi biện pháp khắc phục, "
            "không quá 30 ngày, chậm từ 15 ngày phải đền bù tiền lãi (Khoản 4 Điều 97). Không được trả đủ/đúng hạn thì người lao động "
            "được nghỉ việc không cần báo trước (điểm b Khoản 2 Điều 35)."
        ),
        query_all=(r"chậm (trả )?lương|nợ lương|quỵt lương|không trả lương|trả lương (trễ|muộn|chậm)|treo lương|khất lương",),
        audit_pattern=r"điều 97|điều 94",
        priority=1,
    ),
    LegalCheck(
        check_id="WAGE_DELAY_RESIGNATION",
        title="Quyền nghỉ việc không cần báo trước khi bị nợ/chậm lương",
        inject_ids=(f"{BLLD}#d35-k2-b", f"{BLLD}#d97-k4", f"{BLLD}#d35-k1-a"),
        instruction=(
            "Người lao động không được trả đủ lương hoặc trả lương không đúng thời hạn CÓ QUYỀN đơn phương chấm dứt HĐLĐ "
            "KHÔNG CẦN BÁO TRƯỚC (điểm b Khoản 2 Điều 35). Ngoại lệ duy nhất là Khoản 4 Điều 97 (bất khả kháng, người sử dụng "
            "lao động đã tìm mọi biện pháp khắc phục VÀ chậm không quá 30 ngày). Chỉ nêu ngoại lệ này dưới dạng điều kiện; "
            "KHÔNG được dùng nó để phủ nhận quyền khi câu hỏi không nêu bất khả kháng. Chậm quá 30 ngày thì ngoại lệ không áp dụng."
        ),
        query_all=(
            r"chậm (trả )?lương|nợ lương|quỵt lương|không trả lương|không trả đủ lương|trả lương (trễ|muộn|chậm)|treo lương|khất lương",
            r"nghỉ|thôi việc|bỏ việc|chấm dứt|đơn phương|báo trước",
        ),
        audit_pattern=r"điều 35",
        contradiction_pattern=r"(không được|không thể|không có quyền) (nghỉ|đơn phương|chấm dứt)",
        safe_conclusion=(
            "Theo điểm b Khoản 2 Điều 35 Bộ luật Lao động 2019, người lao động không được trả đủ lương hoặc trả lương "
            "không đúng thời hạn có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước, trừ trường hợp quy định "
            "tại Khoản 4 Điều 97 (vì lý do bất khả kháng, người sử dụng lao động đã tìm mọi biện pháp khắc phục và việc chậm "
            "trả lương không quá 30 ngày)."
        ),
        priority=0,
    ),
    LegalCheck(
        check_id="TERMINATION_SETTLEMENT",
        title="Thời hạn thanh toán, trả sổ khi chấm dứt hợp đồng",
        inject_ids=(f"{BLLD}#d48-k1", f"{BLLD}#d48-k3-a"),
        instruction=(
            "Thời hạn thanh toán các khoản khi chấm dứt HĐLĐ và trách nhiệm xác nhận, trả lại giấy tờ bảo hiểm: đối chiếu Khoản 1 và "
            "điểm a Khoản 3 Điều 48."
        ),
        query_all=(r"chốt sổ|trả sổ|sổ bảo hiểm|thanh toán.{0,30}(nghỉ việc|thôi việc|chấm dứt)|quyết toán|giữ sổ",),
        audit_pattern=r"điều 48",
        priority=2,
    ),
    LegalCheck(
        check_id="DISCIPLINE_STATUTE_OF_LIMITATIONS",
        title="Thời hiệu xử lý kỷ luật lao động",
        inject_ids=(f"{BLLD}#d123-k1", f"{BLLD}#d123-k2", f"{BLLD}#d123-k3"),
        instruction=(
            "Thời hiệu xử lý kỷ luật lao động là 06 tháng kể từ ngày xảy ra hành vi vi phạm (12 tháng nếu liên quan trực tiếp đến "
            "tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh) theo Khoản 1 Điều 123; trường hợp kéo dài thời hiệu khi hết "
            "thời gian tại Khoản 4 Điều 122 không quá 60 ngày (Khoản 2 Điều 123). Quyết định xử lý kỷ luật phải được ban hành trong thời hạn này."
        ),
        query_all=(
            r"sa thải|kỷ luật|khiển trách|cách chức|xử lý vi phạm",
            r"thời hiệu|quá hạn|hết hạn|(sau|cách đây|đã qua)\s*\d+\s*(tháng|năm)|\d+\s*(tháng|năm)\s*trước|từ năm ngoái",
        ),
        article_any=((BLLD, "123"),),
        audit_pattern=r"điều 123",
        priority=1,
    ),
    LegalCheck(
        check_id="PROHIBITED_ID_DEPOSIT_RETENTION",
        title="Hành vi người sử dụng lao động không được làm khi giao kết, thực hiện hợp đồng lao động",
        inject_ids=(f"{BLLD}#d17-k1", f"{BLLD}#d17-k2"),
        instruction=(
            "Đối chiếu Điều 17 Bộ luật Lao động 2019: người sử dụng lao động không được giữ bản chính giấy tờ tùy thân, văn bằng, "
            "chứng chỉ của người lao động (Khoản 1) và không được yêu cầu người lao động thực hiện biện pháp bảo đảm bằng tiền hoặc "
            "tài sản khác (đặt cọc, thế chấp, ký quỹ) cho việc thực hiện HĐLĐ (Khoản 2)."
        ),
        query_all=(
            r"giữ (bản chính|bản gốc|bằng|văn bằng|chứng chỉ|cccd|cmnd|căn cước|giấy tờ tùy thân)|"
            r"(nộp|thu) (bản chính|bản gốc)\s*(bằng|văn bằng|chứng chỉ|cccd|cmnd|căn cước)|"
            r"(đặt cọc|tiền cọc|ký quỹ|thế chấp).{0,30}(đi làm|nhận việc|hợp đồng|công ty|doanh nghiệp|khi vào làm)|"
            r"(yêu cầu|bắt|ép)\s*(đặt cọc|nộp cọc|ký quỹ|thế chấp)",
        ),
        article_any=((BLLD, "17"),),
        audit_pattern=r"điều 17",
        contradiction_pattern=r"(công ty|người sử dụng lao động|doanh nghiệp) (được phép|có quyền) (giữ bản chính|thu tiền cọc|yêu cầu đặt cọc)",
        safe_conclusion=(
            "Theo Khoản 1 và Khoản 2 Điều 17 Bộ luật Lao động 2019, người sử dụng lao động không được giữ bản chính giấy tờ tùy thân, "
            "văn bằng, chứng chỉ của người lao động và không được yêu cầu người lao động thực hiện biện pháp bảo đảm bằng tiền hoặc tài sản "
            "khác cho việc thực hiện hợp đồng lao động."
        ),
        priority=1,
    ),
    LegalCheck(
        check_id="WORKPLACE_ACCIDENT_LIABILITY",
        title="Trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp",
        inject_ids=(
            f"{ATVSLD}#d38-k1", f"{ATVSLD}#d38-k2", f"{ATVSLD}#d38-k3", f"{ATVSLD}#d38-k4", f"{ATVSLD}#d39-k4",
        ),
        instruction=(
            "Đối chiếu Điều 38 và Điều 39 Luật An toàn, vệ sinh lao động 2015: người sử dụng lao động có trách nhiệm kịp thời sơ cứu, cấp cứu, "
            "tạm ứng và thanh toán chi phí y tế (Khoản 1, 2 Điều 38), trả đủ tiền lương trong thời gian điều trị, phục hồi chức năng (Khoản 3 Điều 38), "
            "bồi thường hoặc trợ cấp theo mức suy giảm khả năng lao động và mức độ lỗi (Khoản 4, 5 Điều 38). Nếu người sử dụng lao động không đóng "
            "bảo hiểm tai nạn lao động, bệnh nghề nghiệp cho người lao động thuộc diện bắt buộc thì phải trả thêm khoản tiền tương ứng với chế độ "
            "quỹ bảo hiểm chi trả theo Khoản 4 Điều 39."
        ),
        query_all=(
            r"tai nạn lao động|bệnh nghề nghiệp",
            r"bồi thường|trợ cấp|chi phí (y tế|điều trị|viện phí)|trách nhiệm.{0,25}(công ty|doanh nghiệp|người sử dụng lao động)|không đóng bảo hiểm",
        ),
        article_any=((ATVSLD, "38"), (ATVSLD, "39")),
        audit_pattern=r"điều 38|điều 39",
        priority=1,
    ),
    # Article-structure links: cheap companions whenever retrieval picks the general rule.
    LegalCheck(
        check_id="LINK_D36_TO_D37",
        title="Quyền đơn phương của người sử dụng lao động luôn đi kèm các trường hợp bị cấm",
        inject_ids=(f"{BLLD}#d37-k1", f"{BLLD}#d37-k2", f"{BLLD}#d37-k3"),
        instruction=(
            "Điều 36 chỉ áp dụng khi người lao động không thuộc các trường hợp cấm tại Điều 37; phải đối chiếu cả hai trước khi kết luận."
        ),
        article_any=((BLLD, "36"),),
        priority=4,
    ),
    LegalCheck(
        check_id="LINK_D125_TO_D122",
        title="Sa thải luôn phải đúng nguyên tắc, trình tự kỷ luật",
        inject_ids=(f"{BLLD}#d122-k4",),
        instruction="Điều 125 chỉ áp dụng khi không rơi vào các thời gian cấm xử lý kỷ luật tại Khoản 4 Điều 122.",
        article_any=((BLLD, "125"),),
        priority=4,
    ),
)


@dataclass
class FiredCheck:
    check: LegalCheck
    by_query: bool
    owner_issue_id: Optional[str] = None


@dataclass
class ConstraintPlan:
    fired: List[FiredCheck] = field(default_factory=list)
    # Ordered (chunk_id, owner_issue_id) to place at the front of the evidence context.
    priority_chunk_ids: List[Tuple[str, Optional[str]]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.fired

    def auditable(self) -> List[FiredCheck]:
        return [f for f in self.fired if f.by_query and (f.check.audit_pattern or f.check.contradiction_pattern)]


def _match_all(groups: Sequence[str], text: str) -> bool:
    return bool(groups) and all(re.search(g, text) for g in groups)


def _match_any(groups: Sequence[str], text: str) -> bool:
    return any(re.search(g, text) for g in groups)


def _selected_articles(chunks: Iterable[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    found: Set[Tuple[str, str]] = set()
    for c in chunks or []:
        meta = c.get("metadata") or c
        doc_id = str(meta.get("doc_id") or "")
        art = str(meta.get("article_number") or "").strip()
        if not (doc_id and art):
            cid = str(c.get("chunk_id") or "")
            m = re.match(r"^([A-Z0-9_]+)#d(\d+)", cid)
            if m:
                doc_id, art = m.group(1), m.group(2)
        if doc_id and art:
            found.add((doc_id, art))
    return found


class StatutoryConstraintEngine:
    """Plans, explains and audits generic statutory constraints."""

    def __init__(self, checks: Sequence[LegalCheck] = CHECKS, max_injected_chunks: int = 10, max_instructions: int = 5):
        self.checks = tuple(checks)
        self.max_injected_chunks = max_injected_chunks
        self.max_instructions = max_instructions

    def plan(
        self,
        query: str,
        issues: Optional[Sequence[Any]] = None,
        selected_chunks: Optional[Iterable[Dict[str, Any]]] = None,
        available_ids: Optional[Set[str]] = None,
    ) -> ConstraintPlan:
        text = normalize_text(query)
        articles = _selected_articles(selected_chunks or [])
        issue_texts: List[Tuple[str, str]] = [
            (str(getattr(iss, "issue_id", f"issue_{i}")), normalize_text(str(getattr(iss, "raw_issue_text", "") or "")))
            for i, iss in enumerate(issues or [], 1)
        ]
        multi_issue = len(issue_texts) > 1

        fired: List[FiredCheck] = []
        for check in self.checks:
            by_query = _match_all(check.query_all, text) and not (check.query_none and _match_any(check.query_none, text))
            by_article = bool(
                (check.article_any and any(a in articles for a in check.article_any))
                or (check.article_all and all(a in articles for a in check.article_all))
            )
            if not (by_query or by_article):
                continue
            owner: Optional[str] = None
            if multi_issue:
                owner = issue_texts[0][0]
                # Prefer the issue whose own text carries the decisive trigger
                # (last group = the legal topic, e.g. termination / allowance).
                trigger = check.query_all[-1] if check.query_all else ""
                for issue_id, itext in issue_texts:
                    if trigger and re.search(trigger, itext):
                        owner = issue_id
                        break
            fired.append(FiredCheck(check=check, by_query=by_query, owner_issue_id=owner))

        # Fact-triggered checks outrank structural links.
        fired.sort(key=lambda f: (0 if f.by_query else 1, f.check.priority))

        # Round-robin allocation so every fired check gets its core provisions.
        plan = ConstraintPlan(fired=fired)
        seen: Set[str] = set()
        depth = 0
        max_depth = max((len(f.check.inject_ids) for f in fired), default=0)
        while len(plan.priority_chunk_ids) < self.max_injected_chunks and depth < max_depth:
            for f in fired:
                if depth >= len(f.check.inject_ids):
                    continue
                cid = f.check.inject_ids[depth]
                if cid in seen or (available_ids is not None and cid not in available_ids):
                    continue
                seen.add(cid)
                plan.priority_chunk_ids.append((cid, f.owner_issue_id))
                if len(plan.priority_chunk_ids) >= self.max_injected_chunks:
                    break
            depth += 1
        return plan

    def prompt_block(self, plan: ConstraintPlan, chunk_to_evidence: Dict[str, str]) -> str:
        if plan.is_empty:
            return ""
        lines = [
            "[KIỂM TRA PHÁP LÝ BẮT BUỘC TRƯỚC KHI KẾT LUẬN]",
            "Các ràng buộc dưới đây được xác định từ dữ kiện câu hỏi. Đọc nội dung các khối căn cứ được chỉ định và đối chiếu "
            "trước khi áp dụng quy định chung. Không được bỏ qua ràng buộc nào có liên quan:",
        ]
        for f in plan.fired[: self.max_instructions]:
            evid = [chunk_to_evidence[c] for c in f.check.inject_ids if c in chunk_to_evidence]
            ref = f" (căn cứ: {', '.join(evid)})" if evid else ""
            owner = f" [thuộc {f.owner_issue_id}]" if f.owner_issue_id else ""
            lines.append(f"- {f.check.title}{owner}{ref}: {f.check.instruction}")
        return "\n".join(lines)

    def correction_message(
        self,
        violations: Sequence[FiredCheck],
        chunk_to_evidence: Dict[str, str],
        answer_text: str = "",
    ) -> str:
        lines = [
            "Bản trả lời trên CHƯA đối chiếu đúng các ràng buộc pháp lý bắt buộc sau, nên kết luận có thể sai:",
        ]
        contradicted = {f.check.check_id for f in self.contradicted(violations, answer_text)}
        for f in violations:
            evid = [chunk_to_evidence[c] for c in f.check.inject_ids if c in chunk_to_evidence]
            ref = f" (dùng {', '.join(evid)})" if evid else ""
            flag = " KẾT LUẬN HIỆN TẠI NGƯỢC VỚI QUY ĐỊNH NÀY." if f.check.check_id in contradicted else ""
            lines.append(f"- {f.check.title}{ref}:{flag} {f.check.instruction}")
        lines.append(
            "Hãy viết lại TOÀN BỘ JSON theo đúng schema. Kết luận phải áp dụng các ràng buộc trên trước quy định chung, "
            "nêu rõ Điều/Khoản tương ứng và gắn đúng evidence_ids. Chỉ dùng căn cứ có trong LEGAL_CONTEXT."
        )
        return "\n".join(lines)

    @staticmethod
    def contradicted(violations: Sequence[FiredCheck], answer_text: str) -> List[FiredCheck]:
        """Violations whose conclusion is the opposite of the statute (not just a missing citation)."""
        text = normalize_text(answer_text)
        return [
            f for f in violations
            if f.check.contradiction_pattern and re.search(f.check.contradiction_pattern, text)
        ]

    def audit(self, plan: ConstraintPlan, answer_text: str, chunk_to_evidence: Optional[Dict[str, str]] = None) -> List[FiredCheck]:
        """Returns fact-triggered checks the answer failed to address.

        A check whose provisions never reached the context cannot be demanded
        from the model, so it is skipped (prevents demanding ungrounded text).
        """
        text = normalize_text(answer_text)
        cited_tokens = {t.upper() for t in re.findall(r"\bE\d+\b", answer_text or "", re.IGNORECASE)}
        violations: List[FiredCheck] = []
        for f in plan.auditable():
            if chunk_to_evidence is not None and not any(c in chunk_to_evidence for c in f.check.inject_ids):
                continue
            if f.check.contradiction_pattern and re.search(f.check.contradiction_pattern, text):
                violations.append(f)
                continue
            if not f.check.audit_pattern:
                continue
            cites_by_token = bool(chunk_to_evidence) and any(
                chunk_to_evidence.get(c, "").upper() in cited_tokens for c in f.check.inject_ids
            )
            if not cites_by_token and not re.search(f.check.audit_pattern, text):
                violations.append(f)
        return violations


def citation_label(meta: Dict[str, Any]) -> str:
    parts: List[str] = []
    point = meta.get("point")
    clause = meta.get("clause_number")
    article = meta.get("article_number")
    if point:
        parts.append(f"Điểm {point}")
    if clause not in (None, ""):
        parts.append(f"Khoản {clause}")
    if article not in (None, ""):
        parts.append(f"Điều {article}")
    doc_id = str(meta.get("doc_id") or "")
    if doc_id == BLLD:
        doc = "Bộ luật Lao động 2019"
    elif doc_id == ND145:
        doc = "Nghị định 145/2020/NĐ-CP"
    elif doc_id == ATVSLD:
        doc = "Luật An toàn, vệ sinh lao động 2015"
    else:
        doc = str(meta.get("document_title") or meta.get("document_no") or doc_id)
    return f"{' '.join(parts)} {doc}".strip()


def verbatim_note(
    violations: Sequence[FiredCheck],
    registry: Dict[str, Dict[str, Any]],
    max_quotes_per_check: int = 3,
) -> Tuple[str, List[str]]:
    """Deterministic fallback: quote the exact statutory text the answer omitted."""
    blocks: List[str] = []
    used: List[str] = []
    for f in violations:
        quotes: List[str] = []
        for cid in f.check.inject_ids:
            if len(quotes) >= max_quotes_per_check:
                break
            if cid in used:
                continue
            meta = registry.get(cid)
            if not meta or not str(meta.get("content") or "").strip():
                continue
            content = re.sub(r"\s+", " ", str(meta["content"]).strip())
            quotes.append(f"- {citation_label(meta)}: “{content}”")
            used.append(cid)
        if quotes:
            blocks.append(f"**{f.check.title}** — nguyên văn quy định cần đối chiếu:\n" + "\n".join(quotes))
    if not blocks:
        return "", []
    note = "### Lưu ý đối chiếu bắt buộc\n\n" + "\n\n".join(blocks)
    return note, used
