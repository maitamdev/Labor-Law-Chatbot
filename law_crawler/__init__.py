# -*- coding: utf-8 -*-
"""VietLabor AI - Legal Crawler Package."""
from law_crawler.config import BASE_URL, DEFAULT_LABOR_KEYWORDS, DOWNLOAD_FOLDER
from law_crawler.vbpl_crawler import VBPLCrawler

__all__ = ["VBPLCrawler", "BASE_URL", "DEFAULT_LABOR_KEYWORDS", "DOWNLOAD_FOLDER"]
