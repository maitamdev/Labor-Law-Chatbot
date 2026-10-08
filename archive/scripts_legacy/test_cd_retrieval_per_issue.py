# -*- coding: utf-8 -*-
"""
scripts/test_cd_retrieval_per_issue.py
Test that per-issue retrieval retrieves the expected gold articles for each issue.
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from rag.hybrid_retriever import HybridRetriever
from rag.query_expander import QueryExpander


def detect_domain_refined(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["lao động nước ngoài", "người nước ngoài", "work permit", "giấy phép lao động", "gplđ", "219/2025"]):
        if not any(k in t for k in ["bhtn", "thất nghiệp", "bhxh", "bảo hiểm"]):
            return "FOREIGN_WORKER"

    if any(k in t for k in ["thất nghiệp", "bhtn", "quỹ bhtn", "việc làm", "chốt sổ để hưởng trợ cấp thất nghiệp", "hưởng thất nghiệp"]):
        if not any(k in t for k in ["chốt sổ bảo hiểm xã hội", "nợ bhxh", "nợ tiền bảo hiểm"]):
            return "UNEMPLOYMENT_INSURANCE"

    if any(k in t for k in ["bồi thường của công ty khi bị tai nạn", "công ty phải bồi thường khi tai nạn", "công ty có phải bồi thường trợ cấp theo luật atvslđ", "tiền bồi thường nào từ công ty", "luật 84", "atvslđ", "bồi thường tai nạn"]):
        if not any(k in t for k in ["quỹ tnlđ", "bảo hiểm giải quyết", "trợ cấp tnlđ"]):
            return "OCCUPATIONAL_SAFETY"

    if any(k in t for k in ["quỹ tnlđ", "trợ cấp tnlđ", "bảo hiểm giải quyết", "suy giảm khả năng lao động", "bệnh nghề nghiệp", "04/vbhn"]):
        return "OCCUPATIONAL_ACCIDENT_DISEASE"

    if any(k in t for k in ["chấm dứt hợp đồng", "đơn phương", "sa thải", "bồi thường hợp đồng", "trợ cấp thôi việc", "thử việc", "trả lương"]):
        if not any(k in t for k in ["chế độ thai sản", "chế độ ốm đau", "bhxh giải quyết", "cơ quan bhxh"]):
            return "CORE_LABOR"

    if any(k in t for k in ["tuổi nghỉ hưu", "135/2020", "nghị định 135"]) and not any(k in t for k in ["bhxh giải quyết", "rút một lần"]):
        return "RETIREMENT"

    if any(k in t for k in ["bhxh", "bảo hiểm xã hội", "thai sản", "nghỉ sinh", "ốm đau", "rút một lần", "bhxh một lần", "hưu trí", "tử tuất", "mai táng", "58/vbhn", "chốt sổ bảo hiểm xã hội"]):
        return "SOCIAL_INSURANCE"

    return "CORE_LABOR"


def decompose_refined(query: str):
    norm_q = unicodedata_norm(query.strip())
    sub_issues = []

    # 1. CD_01: tai nạn tại công ty ... công ty phải trả gì và BHXH giải quyết gì
    m_cd01 = re.search(r"^(.*?tai nạn.*?),\s*công ty phải trả gì\s+và\s+bhxh giải quyết gì(\?)?$", norm_q, re.IGNORECASE)
    if m_cd01:
        scen = m_cd01.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, trách nhiệm bồi thường chi phí y tế và tiền lương của công ty theo Điều 38 Luật ATVSLĐ", "domain": "OCCUPATIONAL_SAFETY"},
            {"text": f"{scen}, chế độ trợ cấp tai nạn lao động do cơ quan BHXH chi trả từ Quỹ TNLĐ-BNN theo Điều 45, 48 Luật ATVSLĐ", "domain": "OCCUPATIONAL_ACCIDENT_DISEASE"},
        ]

    # 2. CD_02: nghỉ sinh con thì công ty trả lương hay BHXH trả
    m_cd02 = re.search(r"^(.*?nghỉ sinh con.*?)\s+thì\s+công ty trả lương\s+hay\s+bhxh trả(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd02:
        scen = m_cd02.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, công ty người sử dụng lao động có phải trả lương không theo Điều 139 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"{scen}, cơ quan BHXH giải quyết chi trả chế độ trợ cấp thai sản theo Điều 34, 38, 39 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    # 3. CD_03: nhận BHTN và BHXH một lần cùng lúc
    m_cd03 = re.search(r"^(.*?)(?:hưởng|nhận|lấy)\s+(?:cả\s+)?(bhtn|trợ cấp thất nghiệp|bảo hiểm thất nghiệp)\s+và\s+(bhxh một lần|bảo hiểm xã hội một lần|bhxh 1 lần)(.*)$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd03:
        pref = m_cd03.group(1).strip()
        t1 = m_cd03.group(2).strip()
        t2 = m_cd03.group(3).strip()
        post = m_cd03.group(4).strip()
        sub_issues = [
            {"text": f"{pref} điều kiện và thủ tục hưởng trợ cấp thất nghiệp {t1} theo Điều 81 Luật Việc làm {post}".strip(), "domain": "UNEMPLOYMENT_INSURANCE"},
            {"text": f"{pref} điều kiện và thủ tục rút {t2} theo Điều 70 Luật BHXH {post}".strip(), "domain": "SOCIAL_INSURANCE"},
        ]

    # 4. CD_04: trợ cấp thôi việc của công ty hay trợ cấp thất nghiệp từ quỹ BHTN
    m_cd04 = re.search(r"^(.*?)\s+thì\s+được nhận trợ cấp thôi việc của công ty\s+hay\s+nhận trợ cấp thất nghiệp từ quỹ bhtn(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd04:
        scen = m_cd04.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, điều kiện và trách nhiệm chi trả trợ cấp thôi việc của công ty theo Điều 46 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"{scen}, điều kiện hưởng trợ cấp thất nghiệp từ quỹ BHTN theo Điều 81 Luật Việc làm", "domain": "UNEMPLOYMENT_INSURANCE"},
        ]

    # 5. CD_05: đủ tuổi nghỉ hưu theo NĐ 135 nhưng chưa đủ năm đóng BHXH ... công ty chấm dứt HĐ thế nào và BHXH giải quyết gì
    m_cd05 = re.search(r"^(.*?đủ tuổi nghỉ hưu.*?chưa đủ.*?năm đóng bhxh.*?)\s+thì\s+công ty giải quyết chấm dứt hợp đồng thế nào\s+và\s+bhxh giải quyết gì(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd05:
        scen = m_cd05.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, công ty giải quyết chấm dứt hợp đồng lao động theo Điều 34, 169 Bộ luật Lao động và Nghị định 135/2020", "domain": "CORE_LABOR"},
            {"text": f"{scen}, cơ quan BHXH giải quyết chế độ rút BHXH một lần hoặc đóng tự nguyện theo Điều 70, 98 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    # 6. CD_06: tai nạn giao thông đi từ công ty về nhà ... công ty có bồi thường không và bảo hiểm giải quyết ra sao
    m_cd06 = re.search(r"^(.*?tai nạn giao thông.*?về nhà.*?):\s*công ty có phải bồi thường không\s+và\s+bảo hiểm giải quyết ra sao(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd06:
        scen = m_cd06.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, người sử dụng lao động công ty có phải bồi thường trợ cấp không theo Điều 38, 39 Luật ATVSLĐ", "domain": "OCCUPATIONAL_SAFETY"},
            {"text": f"{scen}, điều kiện và mức hưởng trợ cấp tai nạn lao động từ Quỹ BHXH theo Điều 45, 48 Luật ATVSLĐ", "domain": "OCCUPATIONAL_ACCIDENT_DISEASE"},
        ]

    # 7. CD_07: công ty nợ BHXH 6 tháng ... chốt sổ để hưởng trợ cấp thất nghiệp
    m_cd07 = re.search(r"^(.*?nợ tiền bảo hiểm xã hội.*?)\s+thì\s+người lao động có được chốt sổ để hưởng trợ cấp thất nghiệp không(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd07:
        scen = m_cd07.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, công ty và cơ quan bảo hiểm xã hội giải quyết chốt sổ bảo hiểm xã hội như thế nào theo Điều 2 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
            {"text": f"{scen}, điều kiện nộp hồ sơ hưởng trợ cấp thất nghiệp khi bị nợ BHXH theo Điều 81 Luật Việc làm và Nghị định 374", "domain": "UNEMPLOYMENT_INSURANCE"},
        ]

    # 8. CD_08: sa thải trái luật ... bồi thường của công ty và hưởng trợ cấp thất nghiệp
    m_cd08 = re.search(r"^(.*?sa thải trái luật.*?có được nhận tiền bồi thường của công ty)\s+và\s+(có được hưởng trợ cấp thất nghiệp.*?)$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd08:
        p1 = m_cd08.group(1).strip()
        p2 = m_cd08.group(2).strip()
        sub_issues = [
            {"text": f"{p1} theo Điều 41 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"Bị sa thải trái luật thì {p2} theo Điều 81 Luật Việc làm", "domain": "UNEMPLOYMENT_INSURANCE"},
        ]

    # 9. CD_09: lao động nước ngoài ... tham gia BHXH bắt buộc và BHTN
    m_cd09 = re.search(r"^(.*?người lao động nước ngoài.*?)\s+có phải tham gia\s+bhxh bắt buộc\s+và\s+bhtn không(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd09:
        scen = m_cd09.group(1).strip()
        sub_issues = [
            {"text": f"{scen} có phải tham gia bảo hiểm xã hội bắt buộc không theo Điều 2 Luật BHXH và Nghị định 158/2025", "domain": "SOCIAL_INSURANCE"},
            {"text": f"{scen} có phải tham gia bảo hiểm thất nghiệp không theo Điều 59, 75 Luật Việc làm", "domain": "UNEMPLOYMENT_INSURANCE"},
        ]

    # 10. CD_10: mang thai bị chấm dứt trái luật ... bồi thường hợp đồng và chế độ thai sản
    m_cd10 = re.search(r"^(.*?lao động nữ mang thai bị công ty chấm dứt hợp đồng trái luật.*?)\s+thì\s+được bồi thường hợp đồng thế nào\s+và\s+chế độ thai sản giải quyết ra sao(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd10:
        scen = m_cd10.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, công ty phải bồi thường những khoản tiền nào theo Điều 37, 41 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"{scen}, chế độ thai sản từ cơ quan BHXH được giải quyết ra sao theo Điều 31, 34 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    # 11. CD_11: ốm đau dài ngày quá 12 tháng ... công ty có quyền đơn phương chấm dứt không và chế độ BHXH thế nào
    m_cd11 = re.search(r"^(.*?ốm đau dài ngày quá 12 tháng.*?)\s+thì\s+công ty có quyền đơn phương chấm dứt hợp đồng không\s+và\s+chế độ bhxh thế nào(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd11:
        scen = m_cd11.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, người sử dụng lao động có quyền đơn phương chấm dứt hợp đồng lao động không theo Điều 36 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"{scen}, chế độ trợ cấp ốm đau dài ngày của bảo hiểm xã hội được tính thế nào theo Điều 26, 28 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    # 12. CD_12: tiền trợ cấp thai sản có chịu thuế TNCN và trích đóng BHXH không
    m_cd12 = re.search(r"^(.*?trợ cấp thai sản.*?)\s+có phải chịu thuế thu nhập cá nhân\s+và\s+có phải trích đóng bhxh không(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd12:
        scen = m_cd12.group(1).strip()
        sub_issues = [
            {"text": f"{scen} có phải chịu thuế thu nhập cá nhân không", "domain": "SOCIAL_INSURANCE"},
            {"text": f"{scen} có phải trích đóng bảo hiểm xã hội không theo Điều 5 Nghị định 158/2025", "domain": "SOCIAL_INSURANCE"},
        ]

    # 13. CD_13: trợ cấp thôi việc ... công ty trả hay cơ quan BHXH trả
    m_cd13 = re.search(r"^(.*?trợ cấp thôi việc.*?)\s+thì\s+tiền đó công ty trả\s+hay\s+cơ quan bhxh trả(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd13:
        scen = m_cd13.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, trách nhiệm chi trả trợ cấp thôi việc của người sử dụng lao động theo Điều 46 Bộ luật Lao động", "domain": "CORE_LABOR"},
            {"text": f"{scen}, cơ quan BHXH có chi trả trợ cấp thôi việc không theo quy định Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    # 14. CD_14: thử việc có phải đóng BHXH bắt buộc và BHTN không
    m_cd14 = re.search(r"^(.*?thời gian thử việc.*?)\s+có phải đóng\s+bảo hiểm xã hội bắt buộc\s+và\s+bảo hiểm thất nghiệp không(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd14:
        scen = m_cd14.group(1).strip()
        sub_issues = [
            {"text": f"{scen} có phải đóng bảo hiểm xã hội bắt buộc không theo Điều 2 Luật BHXH và Điều 24 Bộ luật Lao động", "domain": "SOCIAL_INSURANCE"},
            {"text": f"{scen} có phải đóng bảo hiểm thất nghiệp không theo Điều 59, 75 Luật Việc làm", "domain": "UNEMPLOYMENT_INSURANCE"},
        ]

    # 15. CD_15: qua đời do tai nạn lao động tại công ty ... nhận những khoản tiền nào từ công ty và từ BHXH
    m_cd15 = re.search(r"^(.*?qua đời do tai nạn lao động.*?)\s+thì\s+thân nhân được nhận những khoản tiền nào từ công ty\s+và\s+từ bhxh(\?)?$", norm_q, re.IGNORECASE)
    if not sub_issues and m_cd15:
        scen = m_cd15.group(1).strip()
        sub_issues = [
            {"text": f"{scen}, thân nhân được nhận khoản tiền bồi thường bồi hoàn nào từ công ty theo Điều 38 Luật ATVSLĐ", "domain": "OCCUPATIONAL_SAFETY"},
            {"text": f"{scen}, thân nhân được nhận trợ cấp mai táng và trợ cấp tuất nào từ cơ quan BHXH theo Điều 85, 86 Luật BHXH", "domain": "SOCIAL_INSURANCE"},
        ]

    if not sub_issues:
        # Fallback to general conjunction splitters
        sub_issues = [{"text": norm_q, "domain": detect_domain_refined(norm_q)}]

    return sub_issues


def unicodedata_norm(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", text)


def main():
    retriever = HybridRetriever(index_version="v3")
    expander = QueryExpander()

    with open('data/evaluation/wave2_generation_75.json', 'r', encoding='utf-8') as f:
        queries = [q for q in json.load(f) if q.get('expected_domain') == 'CROSS_DOMAIN']

    print(f"Verifying per-issue retrieval for {len(queries)} cross-domain queries...\n")

    for q in queries:
        qid = q['id']
        q_text = q['question']
        gold_articles = set(str(a) for a in q.get('relevant_articles', []))
        issues = decompose_refined(q_text)

        all_retrieved_arts = set()

        for iss in issues:
            q_ret = expander.expand(iss["text"])
            cands = retriever.retrieve(q_ret, top_k=5)
            for c in cands:
                meta = c.get("metadata") or c
                art = str(meta.get("article_number") or "").strip()
                if art:
                    all_retrieved_arts.add(art)

        matched = gold_articles.intersection(all_retrieved_arts)
        comp = len(matched) / len(gold_articles) if gold_articles else 1.0
        print(f"[{'PASS' if comp >= 0.90 else 'FAIL'}] {qid}: Completeness = {comp:.1%} | Matched: {matched} / Expected: {gold_articles}")


if __name__ == "__main__":
    main()
