# -*- coding: utf-8 -*-
"""
VietLabor AI - Retrieval routing tables.

DOMAIN_PRIMARY_DOCS: primary statutes per legal domain (used to re-order
candidates and for relevance grading).
EVIDENCE_ROLE_RETRIEVAL_HINTS: targeted retrieval phrases per required evidence
role, appended when an issue's mandatory provision was not retrieved.

Moved out of rag/chain.py unchanged; chain.py re-exports both names.
"""
from __future__ import annotations

from typing import Dict, Set

DOMAIN_PRIMARY_DOCS: Dict[str, Set[str]] = {
    "SOCIAL_INSURANCE": {"VBHN_58_2025", "ND_158_2025", "ND_159_2025", "TT_12_2025", "ND_176_2025"},
    "OCCUPATIONAL_SAFETY": {"L_84_2015", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026", "ND_39_2016", "ND_44_2016", "TT_24_2022", "ND_129_2025"},
    "OCCUPATIONAL_ACCIDENT_DISEASE": {"L_84_2015", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026", "ND_39_2016", "ND_129_2025"},
    "UNEMPLOYMENT_INSURANCE": {"LVL_74_2025", "LUAT_74_2025", "ND_374_2025"},
    "FOREIGN_WORKER": {"ND_219_2025", "VBHN_18_2026"},
    "RETIREMENT": {"ND_135_2020", "VBHN_18_2026", "VBHN_58_2025"},
    "CORE_LABOR": {"VBHN_18_2026", "ND_145_2020", "LUAT_113_2025", "ND_168_2026"},
    "MATERNITY": {"VBHN_18_2026", "LUAT_113_2025", "ND_168_2026", "VBHN_58_2025"},
    "COLLECTIVE_LABOR": {"VBHN_18_2026", "VBHN_90_2025", "ND_145_2020", "ND_129_2025"},
    "EMPLOYMENT_SERVICE": {"LVL_74_2025", "ND_318_2025", "ND_352_2025"},
    "CROSS_DOMAIN": {"VBHN_58_2025", "L_84_2015", "LVL_74_2025", "LUAT_74_2025", "VBHN_18_2026", "ND_158_2025", "VBHN_06_BNV_2026", "ND_135_2020", "ND_374_2025"},
}

EVIDENCE_ROLE_RETRIEVAL_HINTS: Dict[str, str] = {
    "OVERTIME_CONSENT": "Điều 107 Khoản 2 Điểm a sự đồng ý của người lao động làm thêm giờ",
    "OVERTIME_LIMIT": "Điều 107 Khoản 2 Điểm b giới hạn số giờ làm thêm trong ngày tháng năm",
    "BONUS_RULE": "Điều 104 Bộ luật Lao động quy chế thưởng căn cứ kết quả sản xuất kinh doanh mức độ hoàn thành công việc",
    "PROHIBITED_MONETARY_DISCIPLINE": "Điều 127 Khoản 2 cấm phạt tiền cắt lương thay xử lý kỷ luật",
    "WAGE_PAYMENT_RULE": "Điều 94 Điều 97 nguyên tắc kỳ hạn trả lương",
    "DELAYED_WAGE_REMEDY": "Điều 97 Khoản 4 trả lương chậm từ 15 ngày tiền lãi",
    "EMPLOYEE_NOTICE_REQUIREMENT": "Điều 35 Khoản 1 thời hạn báo trước của người lao động",
    "EMPLOYEE_NO_NOTICE_EXCEPTION": "Điều 35 Khoản 2 người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước",
    "EMPLOYEE_NO_NOTICE_FOR_MISASSIGNED_WORK": "Điều 35 Khoản 2 Điểm a người lao động không được bố trí theo đúng công việc địa điểm làm việc được nghỉ không cần báo trước Điều 29",
    "WORK_REASSIGNMENT_LIMITS": "Điều 29 Bộ luật Lao động chuyển người lao động làm công việc khác so với hợp đồng lao động",
    "EMPLOYEE_UNLAWFUL_TERMINATION_LIABILITY": "Điều 40 nghĩa vụ người lao động đơn phương chấm dứt trái pháp luật",
    "INDIVIDUAL_LABOUR_DISPUTE_PROCEDURE": "Điều 188 và Điều 190 Bộ luật Lao động thủ tục hòa giải quyền yêu cầu Tòa án và thời hiệu tranh chấp lao động cá nhân",
    "EMPLOYER_MISTREATMENT_PROHIBITION": "Điều 8 Khoản 2 Bộ luật Lao động cấm ngược đãi người lao động",
    "EMPLOYEE_NO_NOTICE_FOR_MISTREATMENT": "Điều 35 Khoản 2 Điểm c người lao động bị người sử dụng lao động đánh đập được nghỉ không cần báo trước",
    "EMPLOYER_MISTREATMENT_SANCTION": "Điều 17 Khoản 4 Điểm a Nghị định 283/2026 xử phạt người sử dụng lao động ngược đãi người lao động",
    "PRE_WORK_CONTRACT_REQUIREMENT": "Điều 13 Khoản 2 trước khi nhận người lao động vào làm việc phải giao kết hợp đồng lao động",
    "EMPLOYMENT_RELATIONSHIP_DEFINITION": "Điều 13 Khoản 1 việc làm có trả công và chịu quản lý được coi là hợp đồng lao động",
    "WRITTEN_CONTRACT_FORM": "Điều 14 Khoản 1 hợp đồng lao động phải bằng văn bản hoặc thông điệp dữ liệu",
    "ORAL_CONTRACT_EXCEPTION": "Điều 14 Khoản 2 hợp đồng dưới 01 tháng có thể giao kết bằng lời nói trừ trường hợp luật định",
    "FORMATION_EQUALITY_GOOD_FAITH": "Điều 15 Khoản 1 nguyên tắc tự nguyện bình đẳng thiện chí hợp tác và trung thực khi giao kết hợp đồng lao động",
    "FORMATION_FREEDOM_LIMITS": "Điều 15 Khoản 2 tự do giao kết nhưng không trái pháp luật thỏa ước lao động tập thể và đạo đức xã hội",
    "MULTIPLE_CONTRACTS_PERMISSION": "Điều 19 Khoản 1 Bộ luật Lao động người lao động có thể giao kết nhiều hợp đồng lao động với nhiều người sử dụng lao động",
    "TERMINATION_SEVERANCE_ALLOWANCE": "Điều 46 Bộ luật Lao động và Điều 8 Nghị định 145/2020 trợ cấp thôi việc người lao động làm việc thường xuyên từ đủ 12 tháng trở lên",
    "PROHIBITED_ACTS_IDENTIFICATION": "Điều 17 Khoản 1 Khoản 2 Bộ luật Lao động nghiêm cấm giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ yêu cầu đặt cọc Điều 15 Nghị định 283/2026",
    "PROHIBITED_ORIGINAL_DOCUMENT_RETENTION": "Điều 17 Khoản 1 Bộ luật Lao động nghiêm cấm giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ của người lao động Điều 15 Nghị định 283/2026",
    "PROHIBITED_SECURITY_DEPOSIT": "Điều 17 Khoản 2 Bộ luật Lao động nghiêm cấm yêu cầu người lao động thực hiện biện pháp bảo đảm bằng tiền hoặc tài sản khác đặt cọc cho việc thực hiện hợp đồng lao động Điều 15 Nghị định 283/2026",
    "DISCIPLINE_LIMITATION_PERIOD": "Điều 123 Khoản 1 Khoản 2 Khoản 3 Bộ luật Lao động thời hiệu xử lý kỷ luật lao động 06 tháng 12 tháng Điều 122",
    "PREGNANCY_DISMISSAL_PROHIBITION": "Điều 37 Khoản 3 Điều 137 Khoản 3 Bộ luật Lao động người sử dụng lao động không được sa thải hoặc đơn phương chấm dứt hợp đồng lao động đối với lao động nữ mang thai nuôi con dưới 12 tháng tuổi",
    "UNINSURED_ACCIDENT_SUBSTITUTION": "Điều 39 Khoản 4 và Điều 38 Luật An toàn vệ sinh lao động người sử dụng lao động chưa đóng bảo hiểm tai nạn lao động phải bồi thường thanh toán chi phí y tế tiền lương",
    "EMPLOYER_MEDICAL_RESPONSIBILITY": "Điều 38 Khoản 1 Khoản 2 Luật An toàn vệ sinh lao động thanh toán chi phí y tế chi phí đồng chi trả cho người lao động bị tai nạn lao động",
    "EMPLOYER_WAGE_RESPONSIBILITY": "Điều 38 Khoản 3 Luật An toàn vệ sinh lao động trả đủ tiền lương cho người lao động bị tai nạn lao động trong thời gian điều trị",
    "EMPLOYER_ACCIDENT_COMPENSATION": "Điều 38 Khoản 4 Khoản 5 Luật An toàn vệ sinh lao động bồi thường cho người lao động bị tai nạn lao động không do lỗi của người lao động",
    "EMPLOYEE_NO_NOTICE_FOR_UNPAID_WAGE": "Điều 35 Khoản 2 Điểm b Bộ luật Lao động người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước khi không được trả đủ lương hoặc trả lương không đúng thời hạn",
    "TERMINATION_SETTLEMENT_OBLIGATION": "Điều 48 Khoản 1 Khoản 3 Bộ luật Lao động trách nhiệm khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội trả lại sổ bảo hiểm trong thời hạn 14 ngày làm việc",
    "EMPLOYER_TRAINING_OBLIGATION": "Điều 61 Điều 62 Bộ luật Lao động học nghề tập nghề hợp đồng đào tạo nghề không phải hợp đồng lao động",
    "WAGE_DEDUCTION_LIMIT": "Điều 102 Bộ luật Lao động khấu trừ tiền lương người sử dụng lao động chỉ được khấu trừ bồi thường thiệt hại tài sản Điều 129",
    "UNDERPAYMENT_SANCTION": "Điều 17 Nghị định 12/2022 Điều 23 Nghị định 283/2026 xử phạt vi phạm tiền lương trả không đủ tiền lương khấu trừ tiền lương trái quy định buộc trả đủ tiền lương và tiền lãi",
    "DISPUTE_RESOLUTION_PROCEDURE": "Điều 188 Bộ luật Lao động hòa giải viên lao động giải quyết tranh chấp lao động cá nhân về tiền lương khởi kiện Tòa án nhân dân",
}
