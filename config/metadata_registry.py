"""Official verified metadata registry for VietLabor AI legal corpus.

All metadata fields in this registry are verified directly against official records
from the Government Portal (vanban.chinhphu.vn) and National Legal Database (vbpl.vn).
"""

from __future__ import annotations
from typing import Any

VERIFIED_METADATA: dict[str, dict[str, Any]] = {
    "VBHN_18_2026": {
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "doc_title": "Văn bản hợp nhất 18/VBHN-VPQH - Bộ luật Lao động",
        "document_type": "Văn bản hợp nhất",
        "issuer": "Văn phòng Quốc hội",
        "signer": "Lê Quang Mạnh",
        "effective_from": "2026-02-12",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vanban.chinhphu.vn/?classid=0&docid=217002&pageid=27160",
    },
    "ND_145_2020": {
        "doc_id": "ND_145_2020",
        "document_no": "145/2020/NĐ-CP",
        "doc_title": "Nghị định 145/2020/NĐ-CP - Hướng dẫn Bộ luật Lao động về điều kiện lao động và quan hệ lao động",
        "document_type": "Nghị định",
        "issuer": "Chính phủ",
        "signer": "Nguyễn Xuân Phúc",
        "effective_from": "2021-02-01",
        "effective_to": None,
        "status": "Còn hiệu lực một phần",
        "official_source": "https://vanban.chinhphu.vn/default.aspx?docid=201967&pageid=27160",
    },
    "TT_10_2020": {
        "doc_id": "TT_10_2020",
        "document_no": "10/2020/TT-BLĐTBXH",
        "doc_title": "Thông tư 10/2020/TT-BLĐTBXH - Hướng dẫn nội dung HĐLĐ, Hội đồng thương lượng tập thể và nghề ảnh hưởng sinh sản",
        "document_type": "Thông tư",
        "issuer": "Bộ Lao động - Thương binh và Xã hội",
        "signer": "Đào Ngọc Dung",
        "effective_from": "2021-01-01",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vbpl.vn/TW/Pages/vbpq-van-ban-goc.aspx?ItemID=146696",
    },
    "ND_293_2025": {
        "doc_id": "ND_293_2025",
        "document_no": "293/2025/NĐ-CP",
        "doc_title": "Nghị định 293/2025/NĐ-CP - Quy định mức lương tối thiểu đối với người lao động làm việc theo HĐLĐ",
        "document_type": "Nghị định",
        "issuer": "Chính phủ",
        "signer": "Hồ Đức Phớc",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vanban.chinhphu.vn/?docid=215832&pageid=27160",
    },
    "ND_12_2022": {
        "doc_id": "ND_12_2022",
        "document_no": "12/2022/NĐ-CP",
        "doc_title": "Nghị định 12/2022/NĐ-CP - Quy định xử phạt vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội",
        "document_type": "Nghị định",
        "issuer": "Chính phủ",
        "signer": "Vũ Đức Đam",
        "effective_from": "2022-01-17",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vanban.chinhphu.vn/?classid=0&docid=205182&pageid=27160",
    },
    "ND_337_2025": {
        "doc_id": "ND_337_2025",
        "document_no": "337/2025/NĐ-CP",
        "doc_title": "Nghị định 337/2025/NĐ-CP - Quy định về hợp đồng lao động điện tử",
        "document_type": "Nghị định",
        "issuer": "Chính phủ",
        "signer": "Phạm Thị Thanh Trà",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vanban.chinhphu.vn/?classid=0&docid=216284&pageid=27160",
    },
    "TT_08_2026": {
        "doc_id": "TT_08_2026",
        "document_no": "08/2026/TT-BNV",
        "doc_title": "Thông tư 08/2026/TT-BNV - Hướng dẫn Nghị định 337/2025/NĐ-CP về hợp đồng lao động điện tử",
        "document_type": "Thông tư",
        "issuer": "Bộ Nội vụ",
        "signer": "Nguyễn Mạnh Khương",
        "effective_from": "2026-07-01",
        "effective_to": None,
        "status": "Còn hiệu lực",
        "official_source": "https://vanban.chinhphu.vn/?classid=0&docid=218200&pageid=27160",
    },
}


def get_verified_metadata(doc_id: str) -> dict[str, Any]:
    """Returns verified metadata for doc_id or empty dict with needs_verification flags."""
    if doc_id in VERIFIED_METADATA:
        return VERIFIED_METADATA[doc_id]
    return {
        "doc_id": doc_id,
        "document_no": None,
        "doc_title": None,
        "document_type": None,
        "issuer": None,
        "signer": None,
        "effective_from": None,
        "effective_to": None,
        "status": "needs_verification",
        "official_source": None,
    }
