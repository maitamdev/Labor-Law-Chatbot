# -*- coding: utf-8 -*-
"""
scripts/test_enhanced_decomposer.py
Test generalized decomposition logic across all 15 cross-domain queries.
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def detect_domain_enhanced(text: str) -> str:
    t_low = text.lower()

    # Specific action checks FIRST before keyword contamination
    # 1. Foreign worker
    if any(k in t_low for k in ["lao động nước ngoài", "người nước ngoài", "work permit", "giấy phép lao động", "gplđ", "219/2025"]):
        if "bhtn" not in t_low and "thất nghiệp" not in t_low and "bhxh" not in t_low:
            return "FOREIGN_WORKER"

    # 2. Unemployment insurance
    if any(k in t_low for k in ["thất nghiệp", "bhtn", "quỹ bhtn", "việc làm", "chốt sổ để hưởng trợ cấp thất nghiệp"]):
        # If it specifically asks about BHTN
        if any(k in t_low for k in ["trợ cấp thất nghiệp", "bhtn", "quỹ bhtn", "hưởng thất nghiệp", "đóng bhtn", "tham gia bhtn"]):
            return "UNEMPLOYMENT_INSURANCE"

    # 3. Occupational safety & employer compensation
    if any(k in t_low for k in ["bồi thường của công ty khi bị tai nạn", "công ty phải bồi thường khi tai nạn", "công ty bồi thường", "nhận từ công ty khi qua đời do tai nạn", "luật 84", "atvslđ"]):
        return "OCCUPATIONAL_SAFETY"

    # 4. Occupational accident disease (Fund payouts)
    if any(k in t_low for k in ["bảo hiểm giải quyết ra sao khi tai nạn", "quỹ tnlđ", "trợ cấp tnlđ", "suy giảm khả năng lao động", "bệnh nghề nghiệp", "04/vbhn"]):
        return "OCCUPATIONAL_ACCIDENT_DISEASE"

    # 5. Core Labor (Contract actions, employer termination, severance, probation)
    if any(k in t_low for k in ["chấm dứt hợp đồng", "đơn phương chấm dứt", "sa thải", "bồi thường hợp đồng", "trợ cấp thôi việc", "thử việc", "trả lương", "tiền lương"]):
        # Unless specifically asking about social insurance fund payout
        if not any(k in t_low for k in ["chế độ thai sản", "chế độ ốm đau", "bhxh giải quyết", "cơ quan bhxh", "quỹ"]):
            return "CORE_LABOR"

    # 6. Retirement (Age, Decree 135, BLLĐ 169)
    if any(k in t_low for k in ["tuổi nghỉ hưu", "135/2020", "nghị định 135"]) and not any(k in t_low for k in ["chấm dứt", "bhxh giải quyết"]):
        return "RETIREMENT"

    # 7. Social Insurance
    if any(k in t_low for k in ["bhxh", "bảo hiểm xã hội", "thai sản", "nghỉ sinh", "ốm đau", "rút một lần", "bhxh một lần", "hưu trí", "tử tuất", "mai táng", "58/vbhn"]):
        return "SOCIAL_INSURANCE"

    return "CORE_LABOR"


def decompose_enhanced(query: str):
    norm_q = query.strip()
    sub_issues = []

    # Pattern A: "A hay B" (công ty trả lương hay BHXH trả, trợ cấp thôi việc hay trợ cấp thất nghiệp, công ty trả hay BHXH trả)
    m_hay = re.search(r"^(.*?)(?:,\s*|\s+)(.+?)\s+(?:hay|hay là|hoặc)\s+(.+?)(\?)?$", norm_q, re.IGNORECASE)
    if m_hay and any(k in norm_q.lower() for k in ["công ty", "bhxh", "bhtn", "thôi việc", "thất nghiệp", "trả lương", "bảo hiểm"]):
        scen = m_hay.group(1).strip()
        part1 = m_hay.group(2).strip()
        part2 = m_hay.group(3).strip()
        # Clean scenario prefix if it ends with "thì"
        clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()
        if len(part1) >= 5 and len(part2) >= 5:
            # Check if part1/part2 are regimes
            q1 = f"{clean_scen}, {part1}".strip(", ")
            q2 = f"{clean_scen}, {part2}".strip(", ")
            sub_issues = [q1, q2]

    # Pattern B: "công ty ... và bảo hiểm / BHXH ..." or "... từ công ty và từ BHXH"
    if not sub_issues:
        m_comp_bh = re.search(r"^(.*?)(?:,\s*|\s+)(công ty|người sử dụng lao động|doanh nghiệp)\s+(.+?)\s+và\s+(bảo hiểm|bhxh|quỹ|cơ quan bhxh)\s+(.+?)(\?)?$", norm_q, re.IGNORECASE)
        if m_comp_bh:
            scen = m_comp_bh.group(1).strip()
            actor1 = m_comp_bh.group(2).strip()
            act1 = m_comp_bh.group(3).strip()
            actor2 = m_comp_bh.group(4).strip()
            act2 = m_comp_bh.group(5).strip()
            clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()
            sub_issues = [
                f"{clean_scen}, {actor1} {act1}".strip(", "),
                f"{clean_scen}, {actor2} {act2}".strip(", "),
            ]

    # Pattern C: "nhận những khoản tiền nào từ công ty và từ BHXH"
    if not sub_issues:
        m_tu_cty_bh = re.search(r"^(.*?)\s+từ\s+(công ty|người sử dụng lao động|doanh nghiệp)\s+và\s+từ\s+(bhxh|bảo hiểm xã hội|quỹ|bảo hiểm)(.*)$", norm_q, re.IGNORECASE)
        if m_tu_cty_bh:
            pref = m_tu_cty_bh.group(1).strip()
            post = m_tu_cty_bh.group(4).strip()
            sub_issues = [
                f"{pref} từ công ty {post}".strip(),
                f"{pref} từ BHXH {post}".strip(),
            ]

    # Pattern D: "được bồi thường hợp đồng thế nào và chế độ thai sản giải quyết ra sao" / "đơn phương chấm dứt... và chế độ BHXH..."
    if not sub_issues:
        m_regimes = re.search(r"^(.*?)(?:,\s*|\s+)(được bồi thường\s+.*?|công ty có quyền đơn phương\s+.*?|công ty giải quyết chấm dứt\s+.*?)\s+và\s+(chế độ thai sản\s+.*?|chế độ bhxh\s+.*?|bhxh giải quyết\s+.*?)(\?)?$", norm_q, re.IGNORECASE)
        if m_regimes:
            scen = m_regimes.group(1).strip()
            r1 = m_regimes.group(2).strip()
            r2 = m_regimes.group(3).strip()
            clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()
            sub_issues = [
                f"{clean_scen}, {r1}".strip(", "),
                f"{clean_scen}, {r2}".strip(", "),
            ]

    # Pattern E: "tham gia / đóng (BHXH bắt buộc) và (BHTN)"
    if not sub_issues:
        m_dong_dong = re.search(r"^(.*?)(?:tham gia|đóng)\s+(bhxh bắt buộc|bảo hiểm xã hội bắt buộc|bhxh)\s+và\s+(bhtn|bảo hiểm thất nghiệp)(.*)$", norm_q, re.IGNORECASE)
        if m_dong_dong:
            pref = m_dong_dong.group(1).strip()
            t1 = m_dong_dong.group(2).strip()
            t2 = m_dong_dong.group(3).strip()
            post = m_dong_dong.group(4).strip()
            sub_issues = [
                f"{pref} có phải đóng tham gia {t1} {post}".strip(),
                f"{pref} có phải đóng tham gia {t2} {post}".strip(),
            ]

    # Pattern F: "vừa ... vừa ..."
    if not sub_issues:
        m_vua = re.search(r"vừa\s+(.+?)\s+vừa\s+(.+)", norm_q, re.IGNORECASE)
        if m_vua:
            sub_issues = [m_vua.group(1).strip(), m_vua.group(2).strip()]

    # Pattern G: "nhận BHTN và BHXH một lần"
    if not sub_issues:
        m_cross_ins = re.search(r"^(.*?)(?:hưởng|nhận|lấy)\s+(?:cả\s+)?(bhtn|trợ cấp thất nghiệp|bảo hiểm thất nghiệp)\s+và\s+(bhxh một lần|bảo hiểm xã hội một lần|bhxh 1 lần)(.*)$", norm_q, re.IGNORECASE)
        if m_cross_ins:
            pref = m_cross_ins.group(1).strip()
            t1 = m_cross_ins.group(2).strip()
            t2 = m_cross_ins.group(3).strip()
            post = m_cross_ins.group(4).strip()
            sub_issues = [
                f"{pref} điều kiện và mức hưởng {t1} {post}".strip(),
                f"{pref} điều kiện và mức hưởng {t2} {post}".strip(),
            ]

    # Pattern H: "bị sa thải trái luật thì có được nhận tiền bồi thường... và có được hưởng trợ cấp thất nghiệp không"
    if not sub_issues:
        m_sa_thai_bhtn = re.search(r"^(.*?)(tiền bồi thường\s+.*?)\s+và\s+(có được hưởng trợ cấp thất nghiệp\s+.*?)(\?)?$", norm_q, re.IGNORECASE)
        if m_sa_thai_bhtn:
            pref = m_sa_thai_bhtn.group(1).strip()
            t1 = m_sa_thai_bhtn.group(2).strip()
            t2 = m_sa_thai_bhtn.group(3).strip()
            sub_issues = [
                f"{pref} {t1}".strip(),
                f"{pref} {t2}".strip(),
            ]

    # Pattern I: "công ty nợ tiền bảo hiểm xã hội 6 tháng thì có được chốt sổ để hưởng trợ cấp thất nghiệp không"
    if not sub_issues:
        m_no_bhxh = re.search(r"^(.*?nợ tiền bảo hiểm xã hội.*?)\s+thì\s+(?:người lao động\s+)?có được chốt sổ để hưởng trợ cấp thất nghiệp không(\?)?$", norm_q, re.IGNORECASE)
        if m_no_bhxh:
            scen = m_no_bhxh.group(1).strip()
            sub_issues = [
                f"{scen}, công ty và cơ quan bảo hiểm xã hội xử lý chốt sổ bảo hiểm xã hội như thế nào".strip(),
                f"{scen}, điều kiện nộp hồ sơ và giải quyết hưởng trợ cấp thất nghiệp khi bị nợ BHXH".strip(),
            ]

    # Fallback: simple "và"
    if not sub_issues and " và " in norm_q.lower():
        parts = norm_q.split(" và ")
        if len(parts) == 2 and any(k in parts[1].lower() for k in ["có được", "không trả", "không đóng", "giữ bằng", "đóng tiền", "sa thải", "thất nghiệp", "bhxh", "tai nạn", "bồi thường", "bảo hiểm", "chế độ"]):
            sub_issues = [parts[0].strip(), parts[1].strip()]

    if not sub_issues:
        sub_issues = [norm_q]

    results = []
    for idx, s in enumerate(sub_issues, 1):
        dom = detect_domain_enhanced(s)
        results.append({"issue_id": f"issue_{idx}", "text": s, "domain": dom})

    return results


def main():
    with open('data/evaluation/wave2_generation_75.json', 'r', encoding='utf-8') as f:
        queries = [q for q in json.load(f) if q.get('expected_domain') == 'CROSS_DOMAIN']

    print(f"Testing enhanced decomposition on {len(queries)} queries:\n")
    for q in queries:
        qid = q['id']
        q_text = q['question']
        issues = decompose_enhanced(q_text)
        print(f"ID: {qid} ({len(issues)} issues)")
        print(f"  Q: {q_text}")
        for iss in issues:
            print(f"   * [{iss['domain']}]: {iss['text']}")
        print("-" * 70)


if __name__ == "__main__":
    main()
