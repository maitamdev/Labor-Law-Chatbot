# -*- coding: utf-8 -*-
"""
VietLabor AI - VBPL Crawler Engine
Crawls legal documents from the Vietnamese National Legal Information Portal (vbpl.vn)
with robust session management, rate-limiting, retry logic, and HTML cleaning.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from law_crawler.config import (
    BASE_URL,
    DOWNLOAD_FOLDER,
    LABOR_WHITELIST_KEYWORDS,
    MAX_WORKERS,
    REQUEST_TIMEOUT,
    SEARCH_URL,
    STRICT_EXCLUDE_KEYWORDS,
    TOANVAN_URL_TEMPLATE,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


def build_resilient_session(max_workers: int = MAX_WORKERS) -> requests.Session:
    """Builds requests Session with connection pool and automatic backoff retry."""
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(
        pool_connections=max_workers * 2,
        pool_maxsize=max_workers * 2,
        max_retries=retry_strategy,
    )
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    return session


class VBPLCrawler:
    """Crawler for National Legal Information Portal (vbpl.vn)."""

    def __init__(
        self,
        output_folder: Path = DOWNLOAD_FOLDER,
        max_workers: int = MAX_WORKERS,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = build_resilient_session(max_workers=max_workers)

    @staticmethod
    def validate_labor_scope(title: str, content: str = "") -> tuple[bool, str]:
        """Strictly validates whether a document belongs to Vietnamese labor law regime."""
        title_lower = title.lower()
        body_lower = (title + " " + content[:2500]).lower()

        # 1. Check strict non-labor exclusions
        for exc in STRICT_EXCLUDE_KEYWORDS:
            if exc in title_lower:
                return False, f"Bị loại trừ do thuộc lĩnh vực '{exc}'"

        # 2. Check presence of labor law keywords
        has_labor = any(kw in body_lower for kw in LABOR_WHITELIST_KEYWORDS)
        if not has_labor:
            return False, "Không chứa các thuật ngữ chuyên môn của Luật Lao động"

        return True, "Hợp lệ (Thuộc hệ sinh thái Luật Lao động)"

    def crawl_document_by_id(
        self,
        item_id: str,
        doc_name: str = "",
        skip_if_exists: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Crawls full text of a legal document by its ItemID.
        
        Args:
            item_id: Unique document ID on vbpl.vn (e.g., '140456' for BLLĐ 2019).
            doc_name: Optional human-readable title or alias for filename.
            skip_if_exists: If True, avoids re-downloading existing files.
            
        Returns:
            Dictionary containing document metadata and extracted plain-text content.
        """
        clean_id = str(item_id).strip()
        safe_name = re.sub(r"[^\w\-_]", "_", doc_name.strip())[:50]
        filename = f"{clean_id}_{safe_name}.json" if safe_name else f"{clean_id}.json"
        filepath = self.output_folder / filename

        if skip_if_exists and filepath.exists():
            logger.info(f"Document {filename} already exists locally. Loading cached...")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        url = TOANVAN_URL_TEMPLATE.format(item_id=clean_id)
        logger.info(f"Crawling document from {url}...")

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(f"Failed to fetch document {clean_id} from {url}: {exc}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Locate full text container
        content_div = soup.find("div", class_="toanvancontent")
        if not content_div:
            content_div = soup.find("div", class_="content")
        if not content_div:
            content_div = soup.find("div", id="divContentDoc")

        if not content_div:
            logger.warning(f"No full-text container found at {url}")
            return None

        # 2. Extract title
        title_tag = soup.find("h1", class_="title") or soup.find("div", class_="title") or soup.find("h1")
        doc_title = title_tag.get_text(strip=True) if title_tag else (doc_name or f"Văn bản pháp luật {clean_id}")

        # 3. Clean and concatenate text paragraphs
        paragraphs = content_div.find_all(["p", "div"])
        text_lines = []
        for p in paragraphs:
            t = p.get_text(strip=True)
            if t and t not in text_lines[-1:]:  # Deduplicate consecutive identical lines
                text_lines.append(t)

        full_content = "\n\n".join(text_lines)
        if not full_content:
            full_content = content_div.get_text(separator="\n", strip=True)

        if not full_content:
            logger.warning(f"Extracted content is empty for {url}")
            return None

        # 4. Enforce strict Labor Law domain scope
        is_labor, reason = self.validate_labor_scope(doc_title, full_content)
        if not is_labor:
            logger.warning(f"Skipping document {clean_id} ('{doc_title}'): {reason}")
            return None

        # 5. Extract metadata fields if present
        doc_payload: Dict[str, Any] = {
            "source_portal": "vbpl.vn",
            "item_id": clean_id,
            "url": url,
            "title": doc_title,
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": full_content,
            "char_count": len(full_content),
            "domain": "LABOR_LAW",
        }

        # Save to disk
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(doc_payload, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved document {filename} ({len(full_content)} chars) to {filepath}")
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")

        return doc_payload

    def search_vbpl(
        self,
        keyword: str,
        max_results: int = 5,
    ) -> List[Dict[str, str]]:
        """Searches vbpl.vn for documents matching keyword and returns found ItemIDs.
        
        Args:
            keyword: Search phrase (e.g. 'bộ luật lao động', 'nghị định 145').
            max_results: Max number of document records to retrieve.
            
        Returns:
            List of dicts: [{"item_id": "...", "title": "...", "url": "..."}]
        """
        search_query_url = f"{SEARCH_URL}?Keyword={quote(keyword)}"
        logger.info(f"Searching vbpl.vn for keyword: '{keyword}'...")

        try:
            response = self.session.get(search_query_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to query search page on vbpl.vn: {e}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        results: List[Dict[str, str]] = []

        # Parse search results
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "ItemID=" in href:
                match = re.search(r"ItemID=(\d+)", href, re.IGNORECASE)
                if match:
                    item_id = match.group(1)
                    title = a_tag.get_text(strip=True)
                    if title and not any(r["item_id"] == item_id for r in results):
                        full_url = urljoin(BASE_URL, href)
                        results.append({
                            "item_id": item_id,
                            "title": title,
                            "url": full_url,
                        })
                        if len(results) >= max_results:
                            break

        logger.info(f"Found {len(results)} search results for '{keyword}'.")
        return results

    def batch_crawl(
        self,
        item_ids_or_search_keywords: List[str],
        max_per_keyword: int = 3,
    ) -> List[Dict[str, Any]]:
        """Executes concurrent batch crawling across multiple IDs or keywords."""
        to_crawl: List[tuple[str, str]] = []

        for item in item_ids_or_search_keywords:
            if item.isdigit():
                to_crawl.append((item, f"Doc_{item}"))
            else:
                search_res = self.search_vbpl(item, max_results=max_per_keyword)
                for r in search_res:
                    to_crawl.append((r["item_id"], r["title"]))

        # Deduplicate
        unique_targets = {}
        for i_id, title in to_crawl:
            unique_targets[i_id] = title

        crawled_docs = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(self.crawl_document_by_id, i_id, title): i_id
                for i_id, title in unique_targets.items()
            }
            for future in as_completed(future_to_id):
                res = future.result()
                if res:
                    crawled_docs.append(res)

        return crawled_docs
