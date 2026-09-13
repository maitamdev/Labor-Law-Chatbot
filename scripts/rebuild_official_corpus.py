# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 3E Production Corpus Rebuild
Rebuilds data/processed/legal_documents.jsonl from canonical official digital sources
(congbao.chinhphu.vn and verified official digital PDFs).
Zero OCR fallback used for production corpus.
"""
import os
import json
import datetime
import fitz
from typing import List, Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.metadata_registry import get_verified_metadata
from ingestion.schemas import PageText, LegalChunk
from ingestion.cleaner import TextCleaner
from ingestion.parser import LegalParser

DOCUMENTS = [
    {
        'doc_id': 'VBHN_18_2026',
        'file_paths': ['data/raw/official_digital/01_18_VBHN_VPQH_2026.pdf'],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm'
    },
    {
        'doc_id': 'ND_145_2020',
        'file_paths': [
            'data/raw/official_digital/02_145_2020_ND_CP.pdf',
            'data/raw/official_digital/02_145_2020_ND_CP_part2.pdf'
        ],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm'
    },
    {
        'doc_id': 'TT_10_2020',
        'file_paths': ['data/raw/core/03_10_2020_TT_BLDTBXH.pdf'],
        'extraction_method': 'pdf_text',
        'official_source': 'https://vbpl.vn/TW/Pages/vbpq-van-ban-goc.aspx?ItemID=146696'
    },
    {
        'doc_id': 'ND_293_2025',
        'file_paths': ['data/raw/official_digital/04_293_2025_ND_CP.pdf'],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-293-2025-nd-cp-46568.htm'
    },
    {
        'doc_id': 'ND_12_2022',
        'file_paths': ['data/raw/official_digital/05_12_2022_ND_CP.pdf'],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-12-2022-nd-cp-36716.htm'
    },
    {
        'doc_id': 'ND_337_2025',
        'file_paths': ['data/raw/official_digital/06_337_2025_ND_CP.pdf'],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-337-2025-nd-cp-467931.htm'
    },
    {
        'doc_id': 'TT_08_2026',
        'file_paths': ['data/raw/official_digital/07_08_2026_TT_BNV.pdf'],
        'extraction_method': 'official_gazette_pdf_text',
        'official_source': 'https://congbao.chinhphu.vn/van-ban/thong-tu-so-08-2026-tt-bnv-469695.htm'
    }
]

def main():
    print("=" * 80)
    print("PHASE 3E: REBUILDING LEGAL CORPUS FROM OFFICIAL DIGITAL SOURCES")
    print("=" * 80)

    cleaner = TextCleaner(remove_page_numbers=True)
    all_chunks: List[LegalChunk] = []
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc_stats = {}

    for doc_cfg in DOCUMENTS:
        doc_id = doc_cfg['doc_id']
        file_paths = doc_cfg['file_paths']
        filename = os.path.basename(file_paths[0])
        print(f"\nProcessing {doc_id} from {file_paths}...")

        meta = get_verified_metadata(doc_id)
        doc_metadata = {
            **meta,
            'filename': filename,
            'extraction_method': doc_cfg['extraction_method'],
            'official_source': doc_cfg['official_source'],
            'text_source_url': doc_cfg['official_source'],
            'extraction_timestamp': timestamp,
            'ocr_engine': None,
            'ocr_model': None,
        }

        # 1. Extract native text pages from official PDF(s)
        raw_pages: List[PageText] = []
        page_counter = 1
        for fp in file_paths:
            pdf_doc = fitz.open(fp)
            for pno in range(len(pdf_doc)):
                page_txt = pdf_doc[pno].get_text()
                raw_pages.append(PageText(
                    doc_id=doc_id,
                    filename=filename,
                    page_number=page_counter,
                    text=page_txt
                ))
                page_counter += 1

        print(f"  Extracted {len(raw_pages)} pages. Total chars: {sum(len(p.text) for p in raw_pages):,}")

        # 2. Clean pages
        cleaned_pages = [cleaner.clean_page(p) for p in raw_pages]

        # 3. Parse pages with hardened parser
        parser = LegalParser(doc_metadata=doc_metadata)
        chunks = parser.parse_pages(cleaned_pages)
        print(f"  Parsed into {len(chunks)} chunks.")

        # Collect stats
        articles = {c.article_number for c in chunks if c.article_number}
        clauses = {c.clause_number for c in chunks if c.clause_number}
        points = {c.point for c in chunks if c.point}
        
        doc_stats[doc_id] = {
            'pages': len(raw_pages),
            'chunks': len(chunks),
            'articles': len(articles),
            'clauses': len(clauses),
            'points': len(points),
            'sample_article_numbers': sorted(list(articles), key=lambda x: int(re.sub(r'\D', '', x)) if re.sub(r'\D', '', x) else 0)[:10]
        }
        all_chunks.extend(chunks)

    # Output to legal_documents.jsonl
    output_path = 'data/processed/legal_documents.jsonl'
    with open(output_path, 'w', encoding='utf-8') as f:
        for c in all_chunks:
            f.write(c.model_dump_json() + '\n')

    print("\n" + "=" * 80)
    print(f"REBUILD COMPLETE: Wrote {len(all_chunks)} chunks to {output_path}")
    print("=" * 80)
    for doc_id, st in doc_stats.items():
        print(f"  {doc_id:15s}: {st['chunks']:4d} chunks | {st['articles']:3d} articles | {st['pages']:3d} pages")

if __name__ == '__main__':
    import re
    main()
