# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 3E 70-Sample Stratified Legal Fidelity Audit
Extracts 10 precise, verified legal samples per document (70 total)
across 8 legal categories:
1. Article heading
2. Clause
3. Point (including d vs đ)
4. Currency / Fine amount
5. Percentage
6. Time duration / Deadline
7. Table (ND 293 minimum wage)
8. Cross-reference
"""
import json
import re
from pathlib import Path

CORPUS_PATH = Path("data/processed/legal_documents.jsonl")

# 10 verified samples per document based on official gazette text
SAMPLES = [
    # --- VBHN 18/2026 (Bộ luật Lao động) ---
    {
        "doc_id": "VBHN_18_2026",
        "category": "1. Article Heading",
        "query": "Phạm vi điều chỉnh",
        "chunk_id": "VBHN_18_2026#d1",
        "expected": "Điều 1. Phạm vi điều chỉnh",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "1. Article Heading (Missing Scan Restored)",
        "query": "Lấy ý kiến và ký kết thỏa ước lao động tập thể",
        "chunk_id": "VBHN_18_2026#d76-k1",
        "expected": "Lấy ý kiến và ký kết thỏa ước lao động tập thể",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "1. Article Heading (Missing Scan Restored)",
        "query": "Gửi thỏa ước lao động tập thể",
        "chunk_id": "VBHN_18_2026#d77",
        "expected": "Điều 77. Gửi thỏa ước lao động tập thể",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "2. Clause",
        "query": "Thử việc",
        "chunk_id": "VBHN_18_2026#d25-k1",
        "expected": "Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "3. Point",
        "query": "Tết Âm lịch",
        "chunk_id": "VBHN_18_2026#d112-k1-b",
        "expected": "Tết Âm lịch: 05 ngày",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "4. Time duration (03 ngày audit)",
        "query": "03 ngày làm việc",
        "chunk_id": "VBHN_18_2026#d35-k1-c",
        "expected": "Ít nhất 03 ngày làm việc",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "4. Time duration (05 ngày audit)",
        "query": "05 ngày làm việc liên tục",
        "chunk_id": "VBHN_18_2026#d36-k1-e",
        "expected": "05 ngày làm việc liên tục trở lên",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "5. Working hours limit",
        "query": "Thời giờ làm việc bình thường",
        "chunk_id": "VBHN_18_2026#d105-k1",
        "expected": "không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "6. Percentage",
        "query": "Làm thêm giờ",
        "chunk_id": "VBHN_18_2026#d107-k2-b",
        "expected": "không quá 50% số giờ làm việc bình thường trong 01 ngày",
    },
    {
        "doc_id": "VBHN_18_2026",
        "category": "7. Article Title (Restored Scan)",
        "query": "Thực hiện thỏa ước",
        "chunk_id": "VBHN_18_2026#d79-k1",
        "expected": "Thực hiện thỏa ước lao động tập thể tại doanh nghiệp",
    },

    # --- ND 145/2020 (Nghị định 145) ---
    {
        "doc_id": "ND_145_2020",
        "category": "1. Article Heading",
        "query": "Sổ quản lý lao động",
        "chunk_id": "ND_145_2020#d3-k1",
        "expected": "lập sổ quản lý lao động ở nơi đặt trụ sở",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "1. Article Heading (Restored Article 30)",
        "query": "Cho thuê lại lao động",
        "chunk_id": "ND_145_2020#d30",
        "expected": "Danh mục công việc được thực hiện cho thuê lại lao động",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "1. Article Heading (Restored Article 82)",
        "query": "Chi phí gửi trẻ",
        "chunk_id": "ND_145_2020#d82",
        "expected": "Giúp đỡ, hỗ trợ của người sử dụng lao động về chi phí gửi trẻ, mẫu giáo",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "2. Clause & Deadline",
        "query": "Báo cáo sử dụng lao động",
        "chunk_id": "ND_145_2020#d4-k2",
        "expected": "trước ngày 05 tháng 6",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "3. Point (Preservation of d and đ)",
        "query": "Miễn nhiệm hòa giải viên",
        "chunk_id": "ND_145_2020#d94-k1-đ",
        "expected": "Từ chối nhiệm vụ hòa giải từ 02 lần trở lên khi được cử tham gia giải quyết tranh chấp lao động",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "4. Salary calculation",
        "query": "Trợ cấp thôi việc",
        "chunk_id": "ND_145_2020#d8-k5-a",
        "expected": "tiền lương bình quân của 06 tháng liền kề",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "5. Time duration",
        "query": "Thời giờ nghỉ giữa giờ",
        "chunk_id": "ND_145_2020#d64-k1",
        "expected": "ít nhất 45 phút liên tục",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "6. Overtime limit",
        "query": "Số giờ làm thêm tối đa",
        "chunk_id": "ND_145_2020#d61",
        "expected": "từ trên 200 giờ đến 300 giờ trong một năm",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "7. Final Article Heading",
        "query": "Trách nhiệm thi hành",
        "chunk_id": "ND_145_2020#d115",
        "expected": "Điều 115. Trách nhiệm thi hành",
    },
    {
        "doc_id": "ND_145_2020",
        "category": "8. Cross-reference",
        "query": "Chuyển tiếp hòa giải viên",
        "chunk_id": "ND_145_2020#d114-k6",
        "expected": "quy định tại các điểm a, c, d và đ khoản 1 Điều 94 Nghị định này",
    },

    # --- TT 10/2020 (Thông tư 10) ---
    {
        "doc_id": "TT_10_2020",
        "category": "1. Article Heading",
        "query": "Nội dung chủ yếu HĐLĐ",
        "chunk_id": "TT_10_2020#d3-k1",
        "expected": "Thông tin về tên, địa chỉ của người sử dụng lao động",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "1. Article Heading (Restored Article 10)",
        "query": "Danh mục nghề ảnh hưởng sinh sản",
        "chunk_id": "TT_10_2020#d10",
        "expected": "Danh mục nghề, công việc có ảnh hưởng xấu tới chức năng sinh sản và nuôi con",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "2. Clause",
        "query": "Bí mật kinh doanh",
        "chunk_id": "TT_10_2020#d4-k1",
        "expected": "bí mật kinh doanh, bí mật công nghệ",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "3. Point",
        "query": "Hình thức trả lương",
        "chunk_id": "TT_10_2020#d3-k5-đ",
        "expected": "Kỳ hạn trả lương do hai bên xác định theo quy định tại Điều 97 của Bộ luật Lao động",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "4. Wage details",
        "query": "Mức lương theo chức danh",
        "chunk_id": "TT_10_2020#d3-k5-a",
        "expected": "Mức lương theo công việc hoặc chức danh",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "5. Rest periods",
        "query": "Nghỉ hằng tuần",
        "chunk_id": "TT_10_2020#d3-k7",
        "expected": "Thời giờ làm việc, thời giờ nghỉ ngơi",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "6. Social Insurance",
        "query": "Bảo hiểm bắt buộc",
        "chunk_id": "TT_10_2020#d3-k9",
        "expected": "Bảo hiểm xã hội, bảo hiểm y tế và bảo hiểm thất nghiệp",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "7. Final Article",
        "query": "Hiệu lực thi hành",
        "chunk_id": "TT_10_2020#d12-k1",
        "expected": "Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 01 năm 2021",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "8. Cross-reference",
        "query": "Điều 21 Bộ luật Lao động",
        "chunk_id": "TT_10_2020#d3",
        "expected": "khoản 1 Điều 21 của Bộ luật Lao động",
    },
    {
        "doc_id": "TT_10_2020",
        "category": "8. Annulment reference",
        "query": "Bãi bỏ thông tư cũ",
        "chunk_id": "TT_10_2020#d12-k2",
        "expected": "hết hiệu lực thi hành",
    },

    # --- ND 293/2025 (Nghị định 293) ---
    {
        "doc_id": "ND_293_2025",
        "category": "1. Article Heading",
        "query": "Mức lương tối thiểu",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "Mức lương tối thiểu tháng và mức lương tối thiểu giờ",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "4. Table: Region I Monthly Wage",
        "query": "5.310.000",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "5.310.000",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "4. Table: Region II Monthly Wage",
        "query": "4.730.000",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "4.730.000",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "4. Table: Region III Monthly Wage (No IHI)",
        "query": "4.140.000",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "4.140.000",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "4. Table: Region IV Monthly Wage",
        "query": "3.700.000",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "3.700.000",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "4. Table: Region I Hourly Wage",
        "query": "25.500",
        "chunk_id": "ND_293_2025#d3-k1",
        "expected": "25.500",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "3. Point d preservation",
        "query": "Thay đổi tên hoặc chia",
        "chunk_id": "ND_293_2025#d3-k3-d",
        "expected": "hoạt động trên địa bàn có sự thay đổi tên hoặc chia",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "3. Point đ preservation",
        "query": "Thành lập mới",
        "chunk_id": "ND_293_2025#d3-k3-đ",
        "expected": "hoạt động trên địa bàn được thành lập mới",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "6. Effective date",
        "query": "Hiệu lực",
        "chunk_id": "ND_293_2025#d5-k1",
        "expected": "từ ngày 01 tháng 01 năm 2026",
    },
    {
        "doc_id": "ND_293_2025",
        "category": "8. Repeal citation",
        "query": "Bãi bỏ NĐ 74/2024",
        "chunk_id": "ND_293_2025#d5-k2",
        "expected": "Nghị định số 74/2024/NĐ-CP",
    },

    # --- ND 12/2022 (Nghị định 12) ---
    {
        "doc_id": "ND_12_2022",
        "category": "1. Article Heading",
        "query": "Hình thức xử phạt",
        "chunk_id": "ND_12_2022#d3-k1",
        "expected": "Cảnh cáo",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "1. Article Heading (Restored Article 40)",
        "query": "Hồ sơ BHXH",
        "chunk_id": "ND_12_2022#d40",
        "expected": "Vi phạm quy định về lập hồ sơ để hưởng chế độ bảo hiểm xã hội, bảo hiểm thất nghiệp",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "4. Currency / Fine range",
        "query": "Phạt tiền Điều 40",
        "chunk_id": "ND_12_2022#d40-k1",
        "expected": "Phạt tiền từ 1.000.000 đồng đến 2.000.000 đồng",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "4. General fine principle",
        "query": "Nguyên tắc phạt tổ chức",
        "chunk_id": "ND_12_2022#d6-k1",
        "expected": "Mức phạt tiền đối với tổ chức bằng 02 lần mức phạt tiền đối với cá nhân",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "5. Multiplier for organization",
        "query": "Thẩm quyền phạt tổ chức gấp 2 lần",
        "chunk_id": "ND_12_2022#d6-k2",
        "expected": "thẩm quyền xử phạt tổ chức gấp 02 lần thẩm quyền xử phạt cá nhân",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "6. Statute of limitations",
        "query": "Thời hiệu xử phạt",
        "chunk_id": "ND_12_2022#d5-k1",
        "expected": "Thời hiệu xử phạt vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "2. Clause",
        "query": "Biện pháp khắc phục",
        "chunk_id": "ND_12_2022#d4-k1",
        "expected": "Buộc trả lại cho cá nhân, tổ chức sử dụng dịch vụ việc làm khoản tiền đã thu",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "7. Final Article",
        "query": "Trách nhiệm thi hành",
        "chunk_id": "ND_12_2022#d64-k1",
        "expected": "Bộ trưởng Bộ Lao động - Thương binh và Xã hội có trách nhiệm hướng dẫn, kiểm tra",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "8. Cross-reference",
        "query": "Quy định về hành vi vi phạm",
        "chunk_id": "ND_12_2022#d1",
        "expected": "Nghị định này quy định về hành vi vi phạm, hình thức xử phạt, mức xử phạt",
    },
    {
        "doc_id": "ND_12_2022",
        "category": "8. Repeal citation",
        "query": "Bãi bỏ NĐ 28/2020",
        "chunk_id": "ND_12_2022#d62-k2",
        "expected": "Nghị định số 28/2020/NĐ-CP",
    },

    # --- ND 337/2025 (Nghị định 337) ---
    {
        "doc_id": "ND_337_2025",
        "category": "1. Article Heading",
        "query": "Giải thích từ ngữ",
        "chunk_id": "ND_337_2025#d3",
        "expected": "Điều 3. Giải thích từ ngữ",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "2. Legal definition",
        "query": "Hợp đồng LĐ điện tử",
        "chunk_id": "ND_337_2025#d3-k1",
        "expected": "Hợp đồng lao động điện tử là hợp đồng lao động được giao kết, thiết lập dưới dạng thông điệp dữ liệu",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "2. Platform definition",
        "query": "Nền tảng HĐLĐ điện tử",
        "chunk_id": "ND_337_2025#d3-k2",
        "expected": "Nền tảng hợp đồng lao động điện tử là hệ thống thông tin phục vụ giao dịch điện tử quy mô lớn",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "3. Clause & Compliance principle",
        "query": "Nguyên tắc chung",
        "chunk_id": "ND_337_2025#d4-k1",
        "expected": "Việc giao kết và thực hiện hợp đồng lao động điện tử phải tuân thủ quy định của pháp luật về lao động",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "4. Authentication requirement",
        "query": "Định danh điện tử",
        "chunk_id": "ND_337_2025#d6-k1",
        "expected": "Việc giao kết hợp đồng lao động điện tử được thực hiện thông qua eContract",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "5. Transition rule",
        "query": "Hợp đồng đã giao kết",
        "chunk_id": "ND_337_2025#d29-k1",
        "expected": "tiếp tục thực hiện theo quy định của pháp luật lao động và pháp luật giao dịch điện tử",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "6. Effective date",
        "query": "Hiệu lực",
        "chunk_id": "ND_337_2025#d28-k1",
        "expected": "Nghị định này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "7. Final Article",
        "query": "Trách nhiệm thi hành",
        "chunk_id": "ND_337_2025#d30-k1",
        "expected": "Bộ trưởng Bộ Nội vụ hướng dẫn, theo dõi, đôn đốc, kiểm tra",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "8. Scope definition",
        "query": "Phạm vi điều chỉnh",
        "chunk_id": "ND_337_2025#d1",
        "expected": "Nền tảng hợp đồng lao động điện tử",
    },
    {
        "doc_id": "ND_337_2025",
        "category": "8. National DB sync",
        "query": "Đồng bộ CSDL quốc gia",
        "chunk_id": "ND_337_2025#d16-k1",
        "expected": "Trung tâm Dữ liệu quốc gia",
    },

    # --- TT 08/2026 (Thông tư 08) ---
    {
        "doc_id": "TT_08_2026",
        "category": "1. Article Heading",
        "query": "Phạm vi điều chỉnh",
        "chunk_id": "TT_08_2026#d1",
        "expected": "Điều 1. Phạm vi điều chỉnh",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "1. Article Heading (Restored Article 11)",
        "query": "Tạm dừng kết nối",
        "chunk_id": "TT_08_2026#d11-k1",
        "expected": "thông báo trước ít nhất 03 ngày làm việc cho Nhà cung cấp eContract",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "1. Article Heading (Restored Article 18)",
        "query": "Khai thác dữ liệu",
        "chunk_id": "TT_08_2026#d18-k1",
        "expected": "Dữ liệu mở trên Nền tảng hợp đồng lao động điện tử được đồng bộ về Trung tâm Dữ liệu quốc gia",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "1. Article Heading (Restored Article 20)",
        "query": "Xử lý sự cố",
        "chunk_id": "TT_08_2026#d20",
        "expected": "Điều 20. Xử lý sự cố",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "2. Clause",
        "query": "Cấp mã ID",
        "chunk_id": "TT_08_2026#d4-k2",
        "expected": "ID được cấp một lần, không thay đổi",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "3. Clause & Data structure",
        "query": "Ký tự gán cho HĐLĐ",
        "chunk_id": "TT_08_2026#d5-k1",
        "expected": "chữ cái A là ký tự gán cho hợp đồng lao động điện tử được giao kết",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "4. Time duration / Notice",
        "query": "Thông báo tạm dừng 03 ngày",
        "chunk_id": "TT_08_2026#d11-k1",
        "expected": "ít nhất 03 ngày làm việc",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "6. Effective Date",
        "query": "Hiệu lực",
        "chunk_id": "TT_08_2026#d23-k1",
        "expected": "từ ngày 01 tháng 7 năm 2026",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "7. Final Article",
        "query": "Điều khoản chuyển tiếp",
        "chunk_id": "TT_08_2026#d24-k1",
        "expected": "Kể từ ngày 01 tháng 7 năm 2026, hợp đồng lao động điện tử sau khi giao kết phải được gửi về Nền tảng",
    },
    {
        "doc_id": "TT_08_2026",
        "category": "8. Scope definition",
        "query": "Mã định danh ID",
        "chunk_id": "TT_08_2026#d1",
        "expected": "cấp mã định danh hợp đồng",
    },
]

def run_audit():
    chunks_by_id = {}
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            chunks_by_id[c["chunk_id"]] = c

    total = len(SAMPLES)
    passed = 0
    failures = []

    print("=" * 80)
    print("PHASE 3E: 70-SAMPLE STRATIFIED LEGAL FIDELITY AUDIT")
    print("Official Digital Source <---> Extracted Text <---> Production JSONL")
    print("=" * 80)

    for idx, sample in enumerate(SAMPLES, 1):
        doc_id = sample["doc_id"]
        cid = sample["chunk_id"]
        expected = sample["expected"]
        cat = sample["category"]

        chunk = chunks_by_id.get(cid)
        if not chunk:
            # Fallback lookup in same doc and article
            cands = [c for c in chunks_by_id.values() if c["doc_id"] == doc_id and cid.split('#')[-1] in c["chunk_id"]]
            if cands:
                chunk = cands[0]

        if not chunk:
            failures.append(f"[{doc_id}] Chunk {cid} missing")
            print(f"{idx:02d}. [FAIL] {doc_id:15s} | {cat:30s} | Chunk {cid} NOT FOUND")
            continue

        full_content = (chunk.get("article_title") or "") + "\n" + chunk.get("content", "")
        norm_full = re.sub(r"\s+", " ", full_content).lower()
        norm_exp = re.sub(r"\s+", " ", expected).lower()

        if norm_exp in norm_full:
            passed += 1
            print(f"{idx:02d}. [PASS] {doc_id:15s} | {cat:32s} | MATCH: '{expected[:35]}...' in {chunk['chunk_id']}")
        else:
            failures.append(f"[{doc_id}] '{expected}' NOT FOUND in {chunk['chunk_id']}")
            print(f"{idx:02d}. [FAIL] {doc_id:15s} | {cat:32s} | MISMATCH: '{expected}' in {chunk['chunk_id']}")
            print(f"     Content: {repr(chunk['content'][:100])}")

    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} samples passed ({(passed/total)*100:.1f}%)")
    print(f"Defects remaining: {len(failures)}")
    print("=" * 80)
    return len(failures) == 0

if __name__ == "__main__":
    import sys
    success = run_audit()
    sys.exit(0 if success else 1)
