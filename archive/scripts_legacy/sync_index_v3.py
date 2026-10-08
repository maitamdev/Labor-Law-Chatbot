"""Synchronize the production Chroma collection with the canonical v3 corpus.

The fast v3 builder reuses unchanged embeddings from earlier indexes.  This
auditor re-embeds only records whose retrieval text changed and refuses to
declare the index healthy when IDs or stored statutory content diverge.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chromadb

from config.settings import CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH
from rag.embeddings import LocalBGEEmbeddings, compute_corpus_fingerprint, format_retrieval_text
from rag.vectorstore import clean_metadata_for_chroma

COLLECTION_NAME = "vietlabor_chunks_v3"


def _load_corpus(corpus_path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with open(corpus_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            chunk_id = str(row.get("chunk_id") or "")
            if not chunk_id:
                raise ValueError(f"Missing chunk_id at line {line_number}")
            if chunk_id in rows:
                raise ValueError(f"Duplicate chunk_id: {chunk_id}")
            rows[chunk_id] = row
    return rows


def _canonical_retrieval_text(row: dict[str, Any]) -> str:
    """Uses the ingestion-approved text, rebuilding only legacy rows."""
    stored = str(row.get("retrieval_text") or "").strip()
    return stored if stored else format_retrieval_text(row)


def synchronize_index(
    corpus_path: Path = PRODUCTION_CORPUS_PATH,
    chroma_dir: Path = CHROMA_INDEX_DIR,
    collection_name: str = COLLECTION_NAME,
) -> dict[str, Any]:
    rows = _load_corpus(corpus_path)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_collection(collection_name)
    stored = collection.get(include=["documents", "metadatas"])

    stored_ids = [str(value) for value in stored["ids"]]
    corpus_ids = set(rows)
    index_ids = set(stored_ids)
    if corpus_ids != index_ids:
        raise RuntimeError(
            f"Index ID mismatch: missing={len(corpus_ids - index_ids)}, "
            f"extra={len(index_ids - corpus_ids)}"
        )

    documents = stored.get("documents") or []
    metadatas = stored.get("metadatas") or []
    changed_ids: list[str] = []
    changed_texts: list[str] = []
    changed_metas: list[dict[str, Any]] = []

    for chunk_id, stored_document, stored_meta in zip(stored_ids, documents, metadatas):
        row = rows[chunk_id]
        canonical_text = _canonical_retrieval_text(row)
        canonical_meta = clean_metadata_for_chroma(row)
        if (
            str(stored_document or "") != canonical_text
            or str((stored_meta or {}).get("content") or "") != str(row.get("content") or "")
        ):
            changed_ids.append(chunk_id)
            changed_texts.append(canonical_text)
            changed_metas.append(canonical_meta)

    if changed_ids:
        embedder = LocalBGEEmbeddings()
        # BGE-M3 at 1024 tokens is memory-intensive on CPU. Small batches avoid
        # severe paging on common student laptops while preserving embeddings.
        batch_size = 8
        for offset in range(0, len(changed_ids), batch_size):
            ids_batch = changed_ids[offset : offset + batch_size]
            texts_batch = changed_texts[offset : offset + batch_size]
            metas_batch = changed_metas[offset : offset + batch_size]
            embeddings = embedder.embed_documents(texts_batch, batch_size=len(texts_batch))
            collection.update(
                ids=ids_batch,
                documents=texts_batch,
                metadatas=metas_batch,
                embeddings=embeddings,
            )

    verification = collection.get(include=["documents", "metadatas"])
    remaining_mismatches = 0
    digest = hashlib.sha256()
    for chunk_id, document, meta in sorted(
        zip(verification["ids"], verification.get("documents") or [], verification.get("metadatas") or []),
        key=lambda item: item[0],
    ):
        row = rows[str(chunk_id)]
        canonical_text = _canonical_retrieval_text(row)
        if str(document or "") != canonical_text or str((meta or {}).get("content") or "") != str(row.get("content") or ""):
            remaining_mismatches += 1
        digest.update(str(chunk_id).encode("utf-8"))
        digest.update(b"\0")
        digest.update(canonical_text.encode("utf-8"))
        digest.update(b"\0")

    if remaining_mismatches:
        raise RuntimeError(f"Index still contains {remaining_mismatches} mismatched records")

    meta = {
        "fingerprint": compute_corpus_fingerprint(corpus_path),
        "corpus_fingerprint": compute_corpus_fingerprint(corpus_path),
        "document_fingerprint": digest.hexdigest(),
        "corpus_path": str(corpus_path),
        "collection_name": collection_name,
        "model_name": LocalBGEEmbeddings().model_name,
        "embedding_dim": LocalBGEEmbeddings().dimension,
        "total_chunks": len(rows),
        "synchronized_records": len(changed_ids),
        "indexed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(chroma_dir / "index_meta.json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    result = synchronize_index()
    print(json.dumps(result, ensure_ascii=False, indent=2))
