# -*- coding: utf-8 -*-
"""
VietLabor AI - Legal Crawler CLI
Command-line runner to crawl labor documents from vbpl.vn.
Usage:
    python -m law_crawler.main --id 140456
    python -m law_crawler.main --keyword "thử việc" --max 3
    python -m law_crawler.main --batch
"""
from __future__ import annotations

import argparse
import logging
import sys

from law_crawler.config import DEFAULT_LABOR_KEYWORDS, DOWNLOAD_FOLDER
from law_crawler.vbpl_crawler import VBPLCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("law_crawler.cli")


def main() -> int:
    parser = argparse.ArgumentParser(description="VietLabor AI - vbpl.vn Document Crawler")
    parser.add_argument("--id", type=str, help="Specific VBPL ItemID to crawl (e.g., 140456)")
    parser.add_argument("--name", type=str, default="", help="Optional document name label")
    parser.add_argument("--keyword", type=str, help="Keyword to search and crawl on vbpl.vn")
    parser.add_argument("--max", type=int, default=3, help="Max documents to crawl per keyword")
    parser.add_argument("--batch", action="store_true", help="Crawl all default labor law topics")
    parser.add_argument("--output", type=str, default=str(DOWNLOAD_FOLDER), help="Download target folder")

    args = parser.parse_args()
    crawler = VBPLCrawler(output_folder=args.output)

    if args.id:
        logger.info(f"Crawling specific ItemID: {args.id}")
        res = crawler.crawl_document_by_id(args.id, doc_name=args.name, skip_if_exists=False)
        if res:
            logger.info(f"Success! Extracted {res['char_count']} chars. Saved in {args.output}")
            return 0
        else:
            logger.error("Failed to crawl document.")
            return 1

    elif args.keyword:
        logger.info(f"Searching and crawling keyword: '{args.keyword}' (limit: {args.max})")
        docs = crawler.batch_crawl([args.keyword], max_per_keyword=args.max)
        logger.info(f"Batch crawl finished. Retrieved {len(docs)} documents.")
        return 0

    elif args.batch:
        logger.info(f"Starting batch crawl across {len(DEFAULT_LABOR_KEYWORDS)} labor topics...")
        docs = crawler.batch_crawl(DEFAULT_LABOR_KEYWORDS, max_per_keyword=args.max)
        logger.info(f"Batch crawl completed. Successfully saved {len(docs)} documents.")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
