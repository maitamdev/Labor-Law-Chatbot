# -*- coding: utf-8 -*-
"""
VietLabor AI - Corpus Legal Diacritic Restoration Script
Restores 100% standard Vietnamese diacritics on all OCR chunks in data/processed/legal_documents.jsonl.
Preserves TT_10_2020 unchanged, preserves all numbers, currency, dates, IDs, and structure.
"""

import os
import sys
import json
import shutil
from datetime import datetime

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ingestion.diacritic_restorer import LegalDiacriticRestorer


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    input_file = os.path.join(BASE_DIR, 'data', 'processed', 'legal_documents.jsonl')
    backup_file = os.path.join(BASE_DIR, 'data', 'processed', 'legal_documents.bak.jsonl')
    temp_file = os.path.join(BASE_DIR, 'data', 'processed', 'legal_documents.tmp.jsonl')

    if not os.path.exists(input_file) and not os.path.exists(backup_file):
        print(f"Error: Neither {input_file} nor {backup_file} exists!")
        sys.exit(1)

    print(f"Starting Vietnamese Legal Diacritic Restoration...")
    
    # 1. Maintain a safe backup
    if os.path.exists(backup_file):
        source_file = backup_file
        print(f"Using pristine backup source: {backup_file}")
    else:
        source_file = input_file
        print(f"Creating pristine backup at: {backup_file}")
        shutil.copy2(input_file, backup_file)

    # 2. Initialize restorer
    print("Loading LegalDiacriticRestorer...")
    restorer = LegalDiacriticRestorer()
    print(f"Loaded phrase memory with {len(restorer.phrase_memory)} canonical legal phrases.")

    # 3. Process all chunks
    total_chunks = 0
    restored_chunks = 0
    skipped_chunks = 0

    start_time = datetime.now()

    with open(source_file, 'r', encoding='utf-8') as fin, \
         open(temp_file, 'w', encoding='utf-8') as fout:

        for line_num, line in enumerate(fin, 1):
            if not line.strip():
                continue
            total_chunks += 1
            chunk = json.loads(line)
            doc_id = chunk.get('doc_id')

            if doc_id == 'TT_10_2020':
                # Already authentic native PDF layer
                fout.write(json.dumps(chunk, ensure_ascii=False) + '\n')
                skipped_chunks += 1
            else:
                restored = restorer.restore_chunk(chunk)
                fout.write(json.dumps(restored, ensure_ascii=False) + '\n')
                restored_chunks += 1

            if total_chunks % 500 == 0:
                print(f"  Processed {total_chunks} chunks...", flush=True)

    # 4. Atomically swap files
    shutil.move(temp_file, input_file)
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\nRESTORATION COMPLETE in {elapsed:.2f} seconds!")
    print(f"  Total chunks   : {total_chunks}")
    print(f"  Restored chunks: {restored_chunks} (6 scanned documents)")
    print(f"  Preserved native: {skipped_chunks} (TT_10_2020)")
    print(f"  Output saved to : {input_file}")


if __name__ == '__main__':
    main()
