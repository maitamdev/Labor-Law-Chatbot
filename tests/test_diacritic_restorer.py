# -*- coding: utf-8 -*-
"""
VietLabor AI - Diacritic Restorer Unit Tests
Validates legal accuracy, preservation of numbers, currency, acronyms, and terminology.
"""

import pytest
from ingestion.diacritic_restorer import LegalDiacriticRestorer


@pytest.fixture(scope="module")
def restorer():
    return LegalDiacriticRestorer()


def test_disciplinary_actions_restoration(restorer):
    raw = "1. Khien trach. 2. Keo dai thoi han nang luong khong qua 06 thang. 3. Cach chuc. 4. Sa thai."
    expected = "1. Khiển trách. 2. Kéo dài thời hạn nâng lương không quá 06 tháng. 3. Cách chức. 4. Sa thải."
    res = restorer.restore_text(raw)
    assert res == expected


def test_currency_and_numbers_preservation(restorer):
    raw = "Vung I: 5.310.000 dong/thang, 25.500 dong/gio."
    res = restorer.restore_text(raw)
    assert "5.310.000 đồng/tháng" in res
    assert "25.500 đồng/giờ" in res
    assert "Vùng I" in res


def test_administrative_fine_formula(restorer):
    raw = "Phat tien tu 10.000.000 dong den 20.000.000 dong doi voi nguoi su dung lao dong"
    res = restorer.restore_text(raw)
    assert "Phạt tiền từ 10.000.000 đồng đến 20.000.000 đồng" in res
    assert "người sử dụng lao động" in res


def test_account_vs_clause_citation_distinction(restorer):
    # 'tài khoản' in account context
    account_raw = "Tai khoan dinh danh dien tu cua chu tai khoan bi khoa."
    account_res = restorer.restore_text(account_raw)
    assert "Tài khoản định danh điện tử" in account_res
    assert "chủ tài khoản" in account_res
    assert "bị khóa" in account_res

    # 'tại khoản' in legal clause citation context
    citation_raw = "quy dinh tai khoan 1 Dieu nay"
    citation_res = restorer.restore_text(citation_raw)
    assert "quy định tại khoản 1 Điều này" in citation_res


def test_econtract_acronym_and_contract_restoration(restorer):
    raw = "giao ket hop dong lao dong dien tu tren Nen tang eContract"
    res = restorer.restore_text(raw)
    assert "giao kết hợp đồng lao động điện tử" in res
    assert "eContract" in res


def test_tt_10_2020_preservation(restorer):
    # Chunks from TT_10_2020 must be preserved 100% untouched
    chunk = {
        'doc_id': 'TT_10_2020',
        'chunk_id': 'TT_10_2020#d1-k1',
        'article_title': 'Phạm vi điều chỉnh',
        'content': 'Thông tư này hướng dẫn thi hành một số điều của Bộ luật Lao động.'
    }
    restored = restorer.restore_chunk(chunk)
    assert restored == chunk


def test_labor_law_titles_and_management(restorer):
    raw = "quản lý nhà nước về lao dong. Bộ luật Lao dong số 45/2019/QH14 theo các điều, khoan sau đây của Bộ luật Lao dong:"
    res = restorer.restore_text(raw)
    assert "quản lý nhà nước về lao động." in res
    assert "Bộ luật Lao động số 45/2019/QH14" in res
    assert "theo các điều, khoản sau đây của Bộ luật Lao động:" in res


def test_vietnam_national_formula_and_citations(restorer):
    raw = "CONG HOA XA HQI CHU NGHIA VIET NAM Doclap-Tydo-Hanhphuc Cần cir Luật T0 chức Chính phi ngày 19 tháng 6 năm 2015; sira đổi, bổ sung b0i Luật s0 71/2025/QH15 c6 hiệu lực kể tiur ngày 01 tháng 01 năm 2026."
    res = restorer.restore_text(raw)
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in res
    assert "Độc lập - Tự do - Hạnh phúc" in res
    assert "Căn cứ Luật Tổ chức Chính phủ" in res
    assert "sửa đổi, bổ sung bởi Luật số 71/2025/QH15" in res
    assert "có hiệu lực kể từ ngày 01 tháng 01 năm 2026." in res


def test_administrative_penalties_terminology(restorer):
    raw = "quy định về hành yi vi phẩm, hình thức xử phạt, mức xu phạt trong lĩnh vrc lao dong, bảo hiểm xã hội, người lao động Việt Nam đi làm việc ? nước ngoài theo hợp đồng"
    res = restorer.restore_text(raw)
    assert "quy định về hành vi vi phạm, hình thức xử phạt, mức xử phạt" in res
    assert "trong lĩnh vực lao động, bảo hiểm xã hội" in res
    assert "người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng" in res


def test_econtract_and_data_terminology(restorer):
    raw = "cấp, khoa, mo khoa tài khoản truy cấp Nền tảng hợp đồng lao động điện tử; dir liêu và cập nhật, khai thác, lưu trữ, chia sẻ dự liệu; khi xây ra sy co; tập huan và huan luyen an toàn"
    res = restorer.restore_text(raw)
    assert "khóa, mở khóa tài khoản truy cập Nền tảng hợp đồng lao động điện tử" in res
    assert "dữ liệu và cập nhật, khai thác, lưu trữ, chia sẻ dữ liệu" in res
    assert "khi xảy ra sự cố" in res
    assert "tập huấn và huấn luyện an toàn" in res
