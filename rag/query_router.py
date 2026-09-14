# -*- coding: utf-8 -*-
"""
VietLabor AI - Deterministic Query Router
Routes user queries to the optimal retrieval strategy based on statutory query patterns:
1. Exact legal reference (Điều, Khoản, Điểm, document numbers like 145/2020/NĐ-CP, 18/VBHN-VPQH)
   -> BM25 lexical search + optional metadata filtering.
2. Natural language & colloquial questions
   -> Hybrid RRF search (BM25 + Dense BGE-M3, k=60).

Strictly deterministic rule-based analysis. Zero LLM agent execution.
Router selects RETRIEVAL STRATEGY, NEVER hard-codes statutory answers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Optional
import unicodedata


@dataclass
class RouteDecision:
    """Encapsulates the deterministic routing decision for a query."""
    strategy: str  # "exact_reference" | "hybrid" | "out_of_scope"
    reason: str
    detected_article: Optional[int] = None
    detected_clause: Optional[int] = None
    detected_doc_no: Optional[str] = None
    metadata_filter: Dict[str, Any] = field(default_factory=dict)
    # Phase 5B statutory semantic flags:
    intent: Optional[str] = None  # "termination_notice" | "probation" | "wage" | "overtime" | "general"
    is_special_occupation: bool = False
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    # Phase 5D actor & intent flags:
    actor: str = "UNKNOWN"  # "EMPLOYEE" | "EMPLOYER" | "BOTH" | "UNKNOWN"
    legal_intent: str = "SUBSTANTIVE_RULE"  # "SUBSTANTIVE_RULE" | "SANCTION" | "BOTH"
    augmented_query: Optional[str] = None
    # Phase 5G Domain & Status-Aware flags:
    domain: str = "CORE_LABOR"  # "CORE_LABOR" | "RETIREMENT" | "UNEMPLOYMENT_INSURANCE" | "FOREIGN_WORKER" | "CROSS_DOMAIN" | "UNKNOWN"
    target_domains: List[str] = field(default_factory=lambda: ["CORE_LABOR"])
    scope_tier: str = "core"  # "core" | "extended"
    target_status: str = "CURRENT"  # "CURRENT" | "PARTIALLY_EFFECTIVE" | "ANY"

    def is_exact_reference(self) -> bool:
        return self.strategy == "exact_reference"

    @property
    def is_out_of_scope(self) -> bool:
        return self.strategy == "out_of_scope"


class QueryRouter:
    """Deterministic statutory query analyzer and retrieval router."""

    # Regex patterns for explicit legal references (case-insensitive)
    ARTICLE_PATTERN = re.compile(r"\bđiều\s+(\d+)\b", re.IGNORECASE)
    CLAUSE_PATTERN = re.compile(r"\bkhoản\s+(\d+)\b", re.IGNORECASE)
    POINT_PATTERN = re.compile(r"\bđiểm\s+([a-zđ])\b", re.IGNORECASE)

    # Official document numbers in Vietnam legal system
    DOC_NO_PATTERN = re.compile(
        r"\b(\d+/(?:20\d\d/)?(?:nđ-cp|vbhn-vpqh|tt-blđtbxh|qđ-ttg|qh\d+|vbhn))\b",
        re.IGNORECASE
    )

    # Document abbreviations
    DOC_ALIAS_PATTERNS = {
        "bộ luật lao động": "18/VBHN-VPQH",
        "bllđ": "18/VBHN-VPQH",
        "nghị định 145": "145/2020/NĐ-CP",
        "nd 145": "145/2020/NĐ-CP",
        "nghị định 293": "293/2025/NĐ-CP",
        "lương tối thiểu 2025": "293/2025/NĐ-CP",
        "nghị định 12": "12/2022/NĐ-CP",
        "xử phạt lao động": "12/2022/NĐ-CP",
        "nghị định 337": "337/2025/NĐ-CP",
        "hợp đồng điện tử": "337/2025/NĐ-CP",
        "thông tư 08": "08/2026/TT-BLĐTBXH",
        # Phase 5G Extended Document Aliases:
        "nghị định 135": "135/2020/NĐ-CP",
        "nd 135": "135/2020/NĐ-CP",
        "tuổi nghỉ hưu": "135/2020/NĐ-CP",
        "luật việc làm": "74/2025/QH15",
        "luật việc làm 2025": "74/2025/QH15",
        "nghị định 374": "374/2025/NĐ-CP",
        "nd 374": "374/2025/NĐ-CP",
        "nghị định 219": "219/2025/NĐ-CP",
        "nd 219": "219/2025/NĐ-CP",
        "lao động nước ngoài": "219/2025/NĐ-CP",
        "giấy phép lao động": "219/2025/NĐ-CP",
    }

    # Phase 5G Domain Signal Groups
    RETIREMENT_SIGNALS = [
        "nghỉ hưu", "tuổi nghỉ hưu", "hưu trí", "tuổi hưu", "bao giờ được nghỉ hưu",
        "khi nào được nghỉ hưu", "bao giờ nghỉ hưu", "khi nào nghỉ hưu", "nghỉ hưu sớm",
        "lộ trình nghỉ hưu", "lộ trình tăng tuổi hưu", "nghề nặng nhọc nghỉ hưu",
        "suy giảm khả năng lao động nghỉ hưu", "thời điểm nghỉ hưu", "thời điểm hưởng lương hưu",
        "135/2020", "nghị định 135", "nd 135",
    ]

    UNEMPLOYMENT_SIGNALS = [
        "thất nghiệp", "trợ cấp thất nghiệp", "bảo hiểm thất nghiệp", "bhtn",
        "hưởng thất nghiệp", "nộp hồ sơ thất nghiệp", "trung tâm dịch vụ việc làm",
        "thời gian hưởng trợ cấp thất nghiệp", "mức hưởng trợ cấp thất nghiệp",
        "điều kiện hưởng trợ cấp thất nghiệp", "chấm dứt hưởng trợ cấp thất nghiệp",
        "bảo lưu thời gian đóng bảo hiểm thất nghiệp", "bảo lưu thời gian đóng bhtn",
        "thông báo tìm kiếm việc làm", "luật việc làm", "nghị định 374", "74/2025", "374/2025",
    ]

    FOREIGN_WORKER_SIGNALS = [
        "người nước ngoài", "lao động nước ngoài", "người lao động nước ngoài",
        "quốc tịch nước ngoài", "work permit", "giấy phép lao động", "gplđ",
        "miễn giấy phép lao động", "không thuộc diện cấp giấy phép lao động",
        "chuyên gia nước ngoài", "lao động kỹ thuật nước ngoài", "giám đốc điều hành nước ngoài",
        "thời hạn giấy phép lao động", "gia hạn giấy phép lao động", "cấp lại giấy phép lao động",
        "thu hồi giấy phép lao động", "người hàn quốc", "người trung quốc", "người nhật", "người mỹ",
        "người nước ngoài làm việc tại việt nam", "nghị định 219", "nd 219", "219/2025",
    ]

    # Semantic keyword groups for labor law intent analysis
    SPECIAL_OCCUPATION_SIGNALS = [
        "tổ lái", "tàu bay", "phi công", "tiếp viên hàng không", "hàng không",
        "bảo dưỡng tàu bay", "sửa chữa tàu bay", "điều độ bay", "thuyền viên",
        "tàu biển", "quản lý doanh nghiệp", "đặc thù",
    ]

    TERMINATION_NOTICE_SIGNALS = [
        "nghỉ việc", "thôi việc", "báo trước", "đơn phương chấm dứt",
        "thời hạn báo trước", "hết hạn hợp đồng",
    ]

    PROBATION_SIGNALS = [
        "thử việc", "thời gian thử việc", "hợp đồng thử việc",
    ]

    JOB_TIER_SIGNALS = [
        "quản lý", "giám đốc", "tổng giám đốc", "hội đồng quản trị",
        "cao đẳng", "đại học", "kỹ sư", "cử nhân", "chuyên môn",
        "trung cấp", "công nhân kỹ thuật", "nhân viên nghiệp vụ",
        "lao động phổ thông", "bảo vệ", "tạp vụ", "phụ kho", "văn phòng",
        "công việc khác",
    ]

    AMBIGUOUS_DURATION_PATTERNS = [
        "thử việc 1 tháng", "thử việc 2 tháng", "thử việc 3 tháng", "thử việc 6 tháng",
        "thử việc 30 ngày", "thử việc 60 ngày", "thử việc 180 ngày",
        "bao lâu", "mấy tháng", "bao nhiêu tháng", "mấy ngày", "bao nhiêu ngày",
        "đúng không", "hợp pháp không", "được không", "đúng chưa", "quy định thế nào",
    ]

    CONTRACT_SPEC_SIGNALS = [
        "không xác định thời hạn", "kxdth", "vô thời hạn",
        "xác định thời hạn", "xdth",
        "dưới 12 tháng", "12 đến 36 tháng", "12-36 tháng", "từ 12",
        "1 năm", "2 năm", "3 năm", "01 năm", "02 năm", "03 năm",
        "dưới 1 năm", "trên 1 năm", "trên 3 năm",
        "tổ lái", "tàu bay", "phi công", "tiếp viên",
        "ngành nghề đặc thù", "công việc đặc thù",
    ]

    OUT_OF_SCOPE_SIGNALS = [
        "ly hôn", "đăng ký kết hôn", "thủ tục kết hôn", "kết hôn với người nước ngoài", "chia tài sản", "hôn nhân gia đình",
        "sổ đỏ", "đất nông nghiệp", "sang tên sổ", "quyền sử dụng đất",
        "mua bán nhà", "nhà đất", "thừa kế", "di chúc",
        "trộm cắp", "phạt tù", "hình sự",
        "thuế thu nhập doanh nghiệp", "trốn thuế", "thuế nhập khẩu", "thuế xuất nhập khẩu", "hải quan",
        "vượt đèn đỏ", "xe máy", "bằng lái xe", "giấy phép lái xe", "nồng độ cồn",
        "khởi kiện tranh chấp hợp đồng mua bán", "tranh chấp hợp đồng mua bán", "mua bán hàng hóa", "kiện đòi nợ", "vay tiền", "giấy viết tay",
        "thành lập công ty", "thành lập doanh nghiệp",
        "sở hữu trí tuệ", "nhãn hiệu độc quyền", "bản quyền",
    ]

    AMBIGUOUS_LABOR_PATTERNS = [
        (["nghỉ ngang", "nghi ngang", "nghỉ việc không báo trước", "nghỉ không báo trước"],
         "Bạn muốn nghỉ việc không báo trước vì lý do gì? (Ví dụ: công ty chậm lương, ngược đãi, hay bạn có lý do cá nhân muốn nghỉ sớm mà không báo trước?)"),
        (["trợ cấp thôi việc", "tiền trợ cấp thôi việc"],
         "Để được hưởng trợ cấp thôi việc theo Điều 46 BLLĐ, bạn cần đáp ứng điều kiện làm việc từ đủ 12 tháng trở lên và lý do chấm dứt hợp đồng hợp pháp. Bạn đã làm việc tại doanh nghiệp được bao lâu và lý do nghỉ việc là gì?"),
        (["làm thêm giờ tháng này có bị quá giờ", "quá giờ quy định không", "vượt quá giờ làm thêm"],
         "Để xác định có vượt quá trần làm thêm giờ hay không (tối đa không quá 40 giờ/tháng theo Điều 107 BLLĐ), bạn vui lòng cho biết cụ thể trong tháng này bạn đã làm thêm tổng cộng bao nhiêu giờ?"),
        (["sa thải tôi như vậy có đúng", "sa thải tôi vậy đúng", "sa thai toi vay dung", "bị sa thải như vậy", "công ty sa thải tôi có đúng"],
         "Công ty đưa ra lý do, hành vi vi phạm gì khi sa thải bạn và đã tổ chức cuộc họp xử lý kỷ luật lao động có sự tham gia của bạn chưa?"),
        (["đi làm ngày chủ nhật", "làm việc ngày chủ nhật", "làm ngày chủ nhật thì được tính lương"],
         "Tiền lương làm vào ngày Chủ nhật phụ thuộc vào việc ngày Chủ nhật có phải là ngày nghỉ hằng tuần theo nội quy/hợp đồng của bạn hay là ngày làm việc bình thường. Trong hợp đồng/nội quy công ty, ngày nghỉ hằng tuần của bạn là ngày nào?"),
        (["chuyển tôi sang làm công việc khác", "chuyển tôi sang làm việc khác", "chuyển sang làm việc khác trong công ty", "điều chuyển công việc khác"],
         "Theo Điều 29 BLLĐ, công ty chỉ được tạm thời chuyển bạn làm việc khác tối đa 60 ngày làm việc cộng dồn trong năm do nhu cầu đột xuất, thiên tai, dịch bệnh. Công ty nêu lý do gì và thời gian điều chuyển dự kiến là bao lâu?"),
        (["làm việc 1 năm thì được bao nhiêu ngày nghỉ phép", "làm việc 1 năm thì được bao nhiêu ngày phép"],
         "Số ngày nghỉ hằng năm khi làm đủ 12 tháng phụ thuộc vào điều kiện làm việc (Điều 113 BLLĐ): 12 ngày (điều kiện bình thường), 14 ngày (nghề nặng nhọc, độc hại hoặc lao động chưa thành niên, khuyết tật), 16 ngày (đặc biệt nặng nhọc, độc hại). Công việc của bạn thuộc điều kiện nào?"),
        (["bắt tôi đóng tiền phạt vì vi phạm nội quy", "phạt tiền vì vi phạm nội quy", "phạt tiền trừ lương", "nộp tiền phạt vì vi phạm nội quy"],
         "Theo Điều 127 BLLĐ, công ty bị nghiêm cấm phạt tiền hoặc trừ lương thay cho xử lý kỷ luật lao động. Tuy nhiên, nếu bạn gây hư hỏng tài sản thì công ty có quyền yêu cầu bồi thường theo Điều 129. Vi phạm của bạn là vi phạm nội quy thông thường hay có gây thiệt hại tài sản cho công ty?"),
        (["trừ 50% tiền lương", "trừ lương như vậy có đúng", "tru luong nhu vay co dung", "khấu trừ 50% lương"],
         "Theo Điều 102 Khoản 3 BLLĐ, mức khấu trừ tiền lương hằng tháng không được quá 30% tiền lương thực lĩnh của người lao động. Công ty trừ lương của bạn vì lý do gì (ví dụ: bồi thường thiệt hại tài sản hay lý do nào khác)?"),
        (["hợp đồng thử việc của tôi hết hạn công ty không nói gì", "hết hạn thử việc công ty không nói gì", "hết thời gian thử việc mà công ty im lặng"],
         "Hai bên ký hợp đồng thử việc riêng hay thỏa thuận nội dung thử việc trong hợp đồng lao động? Sau khi hết hạn thử việc, bạn có tiếp tục đến làm việc bình thường tại công ty không?"),
        (["chậm đóng bảo hiểm xã hội", "nợ bảo hiểm xã hội", "không đóng bảo hiểm xã hội"],
         "Công ty đã chậm đóng bảo hiểm xã hội cho bạn trong bao lâu, và bạn đang muốn khiếu nại đến cơ quan chức năng hay muốn căn cứ vào đó để đơn phương chấm dứt hợp đồng lao động (theo Điều 35 Khoản 2 Điểm đ BLLĐ)?"),
        (["làm ca đêm có được trả thêm tiền phụ cấp", "tôi làm ca đêm được trả thêm bao nhiêu", "phụ cấp ca đêm"],
         "Theo Điều 98 BLLĐ, người lao động làm việc vào ban đêm (từ 22h đến 6h) được trả thêm ít nhất 30% lương. Ca làm việc của bạn là ca bình thường vào ban đêm hay bạn làm thêm giờ vào ban đêm?"),
        (["chuyển ngày nghỉ phép năm của tôi sang năm sau", "chuyển ngày nghỉ phép năm sang năm sau", "gộp ngày nghỉ phép năm sang năm sau"],
         "Theo Điều 113 Khoản 4 BLLĐ, người lao động có thể thỏa thuận với người sử dụng lao động để nghỉ phép năm gộp tối đa 03 năm một lần. Việc chuyển phép năm này là do công ty tự ý quyết định hay hai bên đã có thỏa thuận từ trước?"),
        (["mất việc do dịch bệnh", "mất việc vì dịch bệnh", "nghỉ việc do dịch bệnh"],
         "Công ty cho bạn thôi việc theo diện đơn phương chấm dứt hợp đồng (Điều 36) hay cho thôi việc do thay đổi cơ cấu công nghệ hoặc vì lý do kinh tế (Điều 42, được nhận trợ cấp mất việc làm theo Điều 47 BLLĐ)?"),
        (["tạm hoãn hợp đồng của tôi có đúng", "tạm hoãn hợp đồng có đúng"],
         "Lý do công ty đưa ra để tạm hoãn hợp đồng là gì (ví dụ: thỏa thuận hai bên, nghĩa vụ quân sự, tạm giam, tạm giữ theo Điều 30 BLLĐ)?"),
        (["làm thêm như vậy được bao nhiêu", "lam them nhu vay duoc bao nhieu"],
         "Bạn làm thêm vào thời điểm nào (ngày thường, ngày nghỉ hằng tuần, hay ngày lễ/tết; vào ban ngày hay ban đêm từ 22h-6h)?"),
        (["cho tôi nghỉ có đúng", "cho toi nghi co dung", "đuổi việc tôi có đúng", "đơn phương chấm dứt hợp đồng với tôi vậy đúng"],
         "Công ty đưa ra lý do gì để cho bạn thôi việc và đã thông báo trước cho bạn bao nhiêu ngày?"),
        (["hợp đồng thử việc của tôi có được trả lương"],
         "Mức lương thỏa thuận cho vị trí chính thức của bạn là bao nhiêu? (Theo Điều 26 BLLĐ, lương thử việc ít nhất bằng 85% mức lương của công việc đó)."),
        (["công ty bắt tôi làm thêm giờ có được", "ep lam them gio", "bắt làm thêm giờ"],
         "Trường hợp làm thêm giờ của bạn là đột xuất do thiên tai, hỏa hoạn (Điều 108 BLLĐ) hay công việc sản xuất kinh doanh thông thường mà bạn chưa đồng ý (Điều 107 BLLĐ)?"),
        (["nghỉ ốm đau thì được hưởng chế độ gì"],
         "Bạn đã tham gia bảo hiểm xã hội bắt buộc chưa và đã có giấy chứng nhận nghỉ việc hưởng BHXH của cơ sở y tế chưa?"),
        (["thời gian thử việc của tôi là bao lâu"],
         "Bạn đang làm việc ở vị trí nào hoặc công việc yêu cầu trình độ chuyên môn gì (người quản lý doanh nghiệp, cao đẳng trở lên, trung cấp/kỹ thuật, hay công việc khác)?"),
        (["đơn phương chấm dứt hợp đồng có phải bồi thường"],
         "Bạn chấm dứt hợp đồng có tuân thủ đúng thời hạn báo trước và lý do theo quy định tại Điều 35 BLLĐ không?"),
        (["nghỉ thai sản xong đi làm lại có được bố trí việc cũ"],
         "Công việc cũ của bạn hiện có còn tồn tại không hay doanh nghiệp đã thay đổi cơ cấu sản xuất?"),
        (["làm việc vào ngày nghỉ hằng tuần được tính lương"],
         "Bạn làm thêm vào ban ngày hay ban đêm của ngày nghỉ hằng tuần?"),
        (["bị tai nạn lao động công ty bồi thường bao nhiêu"],
         "Tai nạn xảy ra do lỗi của ai và bạn đã được giám định tỷ lệ suy giảm khả năng lao động là bao nhiêu %?"),
    ]

    def route(self, query: str) -> RouteDecision:
        """Analyzes query text and determines the optimal retrieval route.
        
        Args:
            query: Normalized user query.
            
        Returns:
            RouteDecision indicating strategy ('exact_reference' or 'hybrid' or 'out_of_scope')
            and extracted statutory metadata filters and semantic flags.
        """
        if not query or not isinstance(query, str):
            return RouteDecision(strategy="hybrid", reason="Empty query")

        norm_query = unicodedata.normalize("NFC", query).strip().lower()

        # 0. Out-of-scope check (with exemption for foreign marriage labor rights)
        is_foreign_labor = any(k in norm_query for k in ["giấy phép lao động", "work permit", "làm việc", "lao động", "gplđ"])
        is_oos = any(k in norm_query for k in self.OUT_OF_SCOPE_SIGNALS)
        if is_oos and not (("người nước ngoài" in norm_query or "kết hôn với người nước ngoài" in norm_query) and is_foreign_labor):
            return RouteDecision(
                strategy="out_of_scope",
                reason="Câu hỏi nằm ngoài phạm vi pháp luật lao động Việt Nam",
                needs_clarification=False,
                domain="UNKNOWN",
                target_domains=["UNKNOWN"],
                scope_tier="core",
            )

        # 0B. Domain & Status-Aware Classification (Phase 5G)
        is_retirement = any(k in norm_query for k in self.RETIREMENT_SIGNALS)
        is_unemployment = any(k in norm_query for k in self.UNEMPLOYMENT_SIGNALS)
        is_foreign = any(k in norm_query for k in self.FOREIGN_WORKER_SIGNALS)
        is_core_severance_or_notice = any(k in norm_query for k in ["thôi việc", "trợ cấp thôi việc", "trợ cấp mất việc", "báo trước", "đơn phương"])

        is_cross_domain = is_unemployment and is_core_severance_or_notice

        if is_cross_domain:
            detected_domain = "CROSS_DOMAIN"
            target_domains = ["CORE_LABOR", "UNEMPLOYMENT_INSURANCE"]
            scope_tier = "extended"
            target_status = "CURRENT"
        elif is_retirement:
            detected_domain = "RETIREMENT"
            target_domains = ["RETIREMENT"]
            scope_tier = "extended"
            target_status = "PARTIALLY_EFFECTIVE"
        elif is_unemployment:
            detected_domain = "UNEMPLOYMENT_INSURANCE"
            target_domains = ["UNEMPLOYMENT_INSURANCE"]
            scope_tier = "extended"
            target_status = "CURRENT"
        elif is_foreign:
            detected_domain = "FOREIGN_WORKER"
            target_domains = ["FOREIGN_WORKER"]
            scope_tier = "extended"
            target_status = "CURRENT"
        else:
            detected_domain = "CORE_LABOR"
            target_domains = ["CORE_LABOR"]
            scope_tier = "core"
            target_status = "CURRENT"

        # 1. Detect explicit Article number
        article_match = self.ARTICLE_PATTERN.search(norm_query)
        detected_article: Optional[int] = int(article_match.group(1)) if article_match else None

        # 2. Detect explicit Clause number
        clause_match = self.CLAUSE_PATTERN.search(norm_query)
        detected_clause: Optional[int] = int(clause_match.group(1)) if clause_match else None

        # 3. Detect explicit document number (e.g. 145/2020/NĐ-CP)
        doc_match = self.DOC_NO_PATTERN.search(norm_query)
        detected_doc_no: Optional[str] = doc_match.group(1).upper() if doc_match else None

        # 4. Detect document aliases if exact article is also mentioned
        if not detected_doc_no and detected_article is not None:
            for alias, canonical_no in self.DOC_ALIAS_PATTERNS.items():
                if alias in norm_query:
                    detected_doc_no = canonical_no
                    break

        # 5. Semantic intent analysis
        is_special = any(k in norm_query for k in self.SPECIAL_OCCUPATION_SIGNALS)
        is_probation = any(k in norm_query for k in self.PROBATION_SIGNALS)

        # Exclusions for termination notice: annual leave cashout, salary advance, severance pay
        is_leave_cashout = any(k in norm_query for k in ["phép", "ngày nghỉ", "chưa nghỉ", "nghỉ hàng năm", "nghỉ hằng năm"])
        is_wage_advance = any(k in norm_query for k in ["tạm ứng", "nghĩa vụ công dân"])
        is_severance = any(k in norm_query for k in ["trợ cấp thôi việc", "trợ cấp mất việc"])

        is_termination = (
            any(k in norm_query for k in self.TERMINATION_NOTICE_SIGNALS)
            and not is_leave_cashout
            and not is_wage_advance
            and not is_severance
        )

        intent = None
        if is_termination:
            intent = "termination_notice"
        elif is_probation:
            intent = "probation"

        # 5B. Actor Classification
        is_employer_acting = any(k in norm_query for k in [
            "người sử dụng lao động", "nsdlđ", "công ty cho tôi nghỉ", "công ty cho nghỉ",
            "công ty đơn phương", "công ty đuổi", "công ty sa thải", "công ty bắt tôi",
            "người sử dụng lao động đơn phương", "công ty tuyển dụng", "người sử dụng lao động cho",
            "doanh nghiệp đơn phương", "công ty chấm dứt", "công ty muốn", "công ty cho nhân viên",
            "người sử dụng lao động muốn", "doanh nghiệp muốn"
        ])
        is_employee_acting = any(k in norm_query for k in [
            "người lao động", "nlđ", "tôi muốn nghỉ", "muốn nghỉ việc", "tôi xin thôi việc",
            "nghỉ ngang", "người lao động đơn phương", "tôi muốn", "muốn nghỉ", "xin nghỉ",
            "tôi ký hợp đồng", "tôi làm", "tôi là", "tôi đơn phương", "hợp đồng của tôi",
            "nghỉ việc thì", "muốn xin nghỉ", "nghỉ việc do", "nghỉ việc khi", "nghỉ việc nếu",
        ])

        # Priority: who is initiating the action?
        if any(k in norm_query for k in ["công ty cho tôi nghỉ", "công ty cho nghỉ", "công ty đuổi", "công ty sa thải", "công ty đơn phương chấm dứt", "người sử dụng lao động đơn phương", "công ty muốn", "người sử dụng lao động muốn"]):
            actor = "EMPLOYER"
        elif any(k in norm_query for k in ["tôi muốn nghỉ", "muốn nghỉ", "xin nghỉ", "tôi xin thôi việc", "người lao động đơn phương", "muốn đơn phương nghỉ", "tôi ký hợp đồng", "nghỉ việc do", "nghỉ việc khi", "nghỉ việc nếu"]):
            actor = "EMPLOYEE"
        elif is_employer_acting and not is_employee_acting:
            actor = "EMPLOYER"
        elif is_employee_acting and not is_employer_acting:
            actor = "EMPLOYEE"
        elif is_employer_acting and is_employee_acting:
            actor = "BOTH"
        else:
            actor = "UNKNOWN"

        # 5C. Legal Intent Classification
        is_sanction = any(k in norm_query for k in [
            "bị phạt bao nhiêu", "mức phạt", "phạt bao nhiêu tiền", "xử phạt thế nào",
            "xử phạt hành chính", "nghị định 12", "bị phạt thế nào"
        ])
        is_substantive = any(k in norm_query for k in [
            "có đúng không", "có được không", "đúng luật không", "hợp pháp không",
            "quy định thế nào", "quyền của", "sai những gì", "vi phạm quy định nào"
        ])

        if is_sanction and not is_substantive:
            legal_intent = "SANCTION"
        elif is_substantive and not is_sanction:
            legal_intent = "SUBSTANTIVE_RULE"
        elif is_sanction and is_substantive:
            legal_intent = "BOTH"
        else:
            legal_intent = "SUBSTANTIVE_RULE"

        # 5D. Augmented query formulation
        augmented_query = query
        if intent == "termination_notice":
            if actor == "EMPLOYER":
                augmented_query = f"{query} người sử dụng lao động đơn phương chấm dứt hợp đồng lao động thời hạn báo trước Điều 36 Bộ luật Lao động"
            elif actor == "EMPLOYEE" and not is_special:
                if any(k in norm_query for k in ["không trả đủ lương", "không trả lương", "chậm lương", "nợ lương", "ngược đãi", "đánh đập", "quấy rối"]):
                    augmented_query = f"{query} người lao động đơn phương chấm dứt hợp đồng lao động không cần báo trước Điều 35 Bộ luật Lao động"
                else:
                    augmented_query = f"{query} người lao động đơn phương chấm dứt hợp đồng lao động thời hạn báo trước Điều 35 Bộ luật Lao động"
        elif legal_intent == "SUBSTANTIVE_RULE" and any(k in norm_query for k in ["đặt cọc", "thế chấp", "giữ bằng", "giấy tờ tùy thân", "căn cước"]):
            augmented_query = f"{query} hành vi người sử dụng lao động không được làm Điều 17 Bộ luật Lao động"

        # 6. Check clarification for ambiguous queries
        needs_clarification = False
        clarification_reason = None

        # A. Ambiguous probation query missing job tier
        if is_probation and "áp dụng thử việc" not in norm_query:
            has_duration_query = any(k in norm_query for k in self.AMBIGUOUS_DURATION_PATTERNS)
            has_job_tier = any(k in norm_query for k in self.JOB_TIER_SIGNALS)
            if has_duration_query and not has_job_tier:
                needs_clarification = True
                clarification_reason = (
                    "Bạn đang thử việc ở vị trí/công việc nào? Nếu biết, hãy cho tôi biết vị trí đó "
                    "yêu cầu trình độ chuyên môn ở mức nào (ví dụ: người quản lý doanh nghiệp, trình độ "
                    "cao đẳng trở lên, trung cấp/kỹ thuật, hay công việc khác)?"
                )

        # B. Ambiguous termination notice missing contract type
        if not needs_clarification and is_termination:
            is_asking_notice = any(k in norm_query for k in [
                "báo trước bao lâu", "báo trước bao nhiêu", "thời hạn báo trước",
                "báo trước mấy ngày", "báo trước thế nào", "báo trước quy định thế nào",
            ])
            has_contract_spec = any(k in norm_query for k in self.CONTRACT_SPEC_SIGNALS)
            if is_asking_notice and not has_contract_spec and "không cần báo trước" not in norm_query:
                needs_clarification = True
                clarification_reason = (
                    "Thời hạn báo trước khi chấm dứt hợp đồng lao động phụ thuộc vào loại hợp đồng lao động "
                    "và ngành nghề. Hợp đồng của bạn thuộc loại nào (không xác định thời hạn, xác định thời hạn "
                    "từ 12-36 tháng, dưới 12 tháng, hay ngành nghề đặc thù như tổ lái tàu bay)?"
                )

        # C. Other ambiguous labor queries missing factual premises
        if not needs_clarification:
            for patterns, reason in self.AMBIGUOUS_LABOR_PATTERNS:
                if any(p in norm_query for p in patterns):
                    # If this is social insurance and query specifically concerns probation, do not trigger general delay clarification
                    if any(p in patterns for p in ["không đóng bảo hiểm xã hội", "chậm đóng bảo hiểm xã hội", "nợ bảo hiểm xã hội"]) and "thử việc" in norm_query:
                        continue
                    needs_clarification = True
                    clarification_reason = reason
                    break

        # Decision logic:
        # If query explicitly targets an Article or a legal document number, route to exact_reference (BM25)
        if detected_article is not None or detected_doc_no is not None:
            reasons = []
            metadata_filter: Dict[str, Any] = {}

            if detected_article is not None:
                reasons.append(f"Điều {detected_article}")
                metadata_filter["article_number"] = detected_article

            if detected_clause is not None:
                reasons.append(f"Khoản {detected_clause}")
                metadata_filter["clause_number"] = detected_clause

            if detected_doc_no is not None:
                reasons.append(f"Văn bản {detected_doc_no}")
                metadata_filter["document_no"] = detected_doc_no

            reason_str = f"Explicit legal reference detected ({', '.join(reasons)}) -> BM25 priority"
            return RouteDecision(
                strategy="exact_reference",
                reason=reason_str,
                detected_article=detected_article,
                detected_clause=detected_clause,
                detected_doc_no=detected_doc_no,
                metadata_filter=metadata_filter,
                intent=intent,
                is_special_occupation=is_special,
                needs_clarification=needs_clarification,
                clarification_reason=clarification_reason,
                actor=actor,
                legal_intent=legal_intent,
                augmented_query=augmented_query,
                domain=detected_domain,
                target_domains=target_domains,
                scope_tier=scope_tier,
                target_status=target_status,
            )

        # Otherwise: standard natural language query -> Hybrid RRF
        return RouteDecision(
            strategy="hybrid",
            reason="Natural language question -> Hybrid RRF (BM25 + BGE-M3) priority",
            intent=intent,
            is_special_occupation=is_special,
            needs_clarification=needs_clarification,
            clarification_reason=clarification_reason,
            actor=actor,
            legal_intent=legal_intent,
            augmented_query=augmented_query,
            domain=detected_domain,
            target_domains=target_domains,
            scope_tier=scope_tier,
            target_status=target_status,
        )
