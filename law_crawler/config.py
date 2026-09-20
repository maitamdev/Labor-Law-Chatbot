# -*- coding: utf-8 -*-
"""
VietLabor AI - Legal Crawler Configuration (vbpl.vn)
Defines endpoints, download directories, user-agents, and labor law query topics
for automated ingestion from the Vietnamese National Legal Portal (vbpl.vn).
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOWNLOAD_FOLDER = PROJECT_ROOT / "data" / "raw" / "crawler"

BASE_URL = "https://vbpl.vn"
SEARCH_URL = "https://vbpl.vn/TW/Pages/vbpq-timkiem.aspx"
TOANVAN_URL_TEMPLATE = "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID={item_id}"

# Default query keywords for labor law ecosystem
DEFAULT_LABOR_KEYWORDS = [
    "bộ luật lao động",
    "hợp đồng lao động",
    "tiền lương",
    "bảo hiểm xã hội",
    "bảo hiểm thất nghiệp",
    "an toàn vệ sinh lao động",
    "tai nạn lao động",
    "kỷ luật lao động",
    "người lao động nước ngoài",
]

# Request parameters
MAX_WORKERS = int(os.environ.get("CRAWLER_MAX_WORKERS", "4"))
REQUEST_TIMEOUT = float(os.environ.get("CRAWLER_REQUEST_TIMEOUT", "25"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (VietLabor-AI-Crawler/1.0)"

# Strict Labor Domain Whitelist
LABOR_WHITELIST_KEYWORDS = [
    "lao động",
    "tiền lương",
    "bảo hiểm xã hội",
    "bảo hiểm thất nghiệp",
    "việc làm",
    "an toàn vệ sinh lao động",
    "tai nạn lao động",
    "kỷ luật lao động",
    "thử việc",
    "hợp đồng lao động",
    "thỏa ước lao động",
    "nghỉ thai sản",
    "trợ cấp thôi việc",
    "trợ cấp mất việc",
    "công đoàn",
    "tiền lương làm thêm",
    "người sử dụng lao động",
    "người lao động",
]

# Strict Exclusions (to protect vector space from non-labor pollution)
STRICT_EXCLUDE_KEYWORDS = [
    "hình sự",
    "tố tụng hình sự",
    "đất đai",
    "hôn nhân và gia đình",
    "giao thông đường bộ",
    "sở hữu trí tuệ",
    "thuế thu nhập doanh nghiệp",
    "chứng khoán",
    "hải quan",
]

