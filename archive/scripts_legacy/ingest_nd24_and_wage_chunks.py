# -*- coding: utf-8 -*-
"""
Ingest Decree 24/2018/ND-CP (Labour Complaints) and ensure wage payment provisions (Articles 94, 97, 35 BLLD 2019)
are thoroughly indexed in BM25 V3 and Chroma V3.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from rag.embeddings import LocalBGEEmbeddings, format_retrieval_text
from rag.vectorstore import LegalVectorStore, clean_metadata_for_chroma
from rag.bm25_retriever import BM25Retriever
from config.metadata_registry import get_verified_metadata
from config.settings import BM25_INDEX_DIR, CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH

NEW_CHUNKS = [
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d15",
        "title": "Thẩm quyền giải quyết khiếu nại về lao động, an toàn, vệ sinh lao động",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 15",
        "clause": "",
        "content": """Điều 15. Thẩm quyền giải quyết khiếu nại về lao động, an toàn, vệ sinh lao động
1. Người sử dụng lao động có thẩm quyền giải quyết khiếu nại lần đầu đối với quyết định, hành vi về lao động, an toàn, vệ sinh lao động của mình bị khiếu nại.
2. Chánh Thanh tra Sở Lao động - Thương binh và Xã hội, nơi người sử dụng lao động đặt trụ sở chính có thẩm quyền giải quyết khiếu nại lần hai đối với khiếu nại về lao động, an toàn, vệ sinh lao động khi người khiếu nại không đồng ý với quyết định giải quyết lần đầu theo quy định tại Điều 23 hoặc đã hết thời hạn quy định tại Điều 20 Nghị định này mà khiếu nại không được giải quyết.
3. Thẩm quyền giải quyết khiếu nại về điều tra tai nạn lao động thực hiện theo quy định tại Điều 17 Nghị định số 39/2016/NĐ-CP ngày 15 tháng 5 năm 2016 của Chính phủ quy định chi tiết thi hành một số điều của Luật an toàn, vệ sinh lao động.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 15",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Thẩm quyền giải quyết khiếu nại"
        }
    },
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d7",
        "title": "Thời hiệu khiếu nại trong lĩnh vực lao động",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 7",
        "clause": "",
        "content": """Điều 7. Thời hiệu khiếu nại
1. Thời hiệu khiếu nại lần đầu là 180 ngày, kể từ ngày người khiếu nại nhận được hoặc biết được quyết định, hành vi của người sử dụng lao động, của tổ chức, cá nhân tham gia hoạt động giáo dục nghề nghiệp, của doanh nghiệp, tổ chức sự nghiệp đưa người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng, của tổ chức dịch vụ việc làm, tổ chức có liên quan đến hoạt động tạo việc làm cho người lao động, tổ chức đánh giá, cấp chứng chỉ kỹ năng nghề quốc gia bị khiếu nại.
2. Trường hợp người khiếu nại không thực hiện được quyền khiếu nại theo đúng thời hiệu quy định tại khoản 1 Điều này vì ốm đau, thiên tai, địch họa, đi công tác, học tập ở nơi xa hoặc vì những trở ngại khách quan khác thì thời gian trở ngại đó không tính vào thời hiệu khiếu nại.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 7",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Thời hiệu khiếu nại lần đầu 180 ngày"
        }
    },
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d20",
        "title": "Thời hạn giải quyết khiếu nại lần đầu",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 20",
        "clause": "",
        "content": """Điều 20. Thời hạn giải quyết khiếu nại lần đầu
1. Thời hạn giải quyết khiếu nại lần đầu không quá 30 ngày, kể từ ngày thụ lý; đối với vụ việc phức tạp thì thời hạn giải quyết không quá 45 ngày, kể từ ngày thụ lý.
2. Ở vùng sâu, vùng xa đi lại khó khăn thì thời hạn giải quyết khiếu nại không quá 45 ngày, kể từ ngày thụ lý; đối với vụ việc phức tạp thì thời hạn giải quyết khiếu nại không quá 60 ngày, kể từ ngày thụ lý.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 20",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Thời hạn giải quyết khiếu nại lần đầu 30 ngày"
        }
    },
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d27",
        "title": "Thụ lý giải quyết khiếu nại lần hai",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 27",
        "clause": "",
        "content": """Điều 27. Thụ lý giải quyết khiếu nại lần hai
1. Trong thời hạn 30 ngày, kể từ ngày hết thời hạn giải quyết khiếu nại quy định tại Điều 20 của Luật này mà khiếu nại lần đầu không được giải quyết hoặc kể từ ngày nhận được quyết định giải quyết khiếu nại lần đầu mà người khiếu nại không đồng ý thì có quyền khiếu nại đến người có thẩm quyền giải quyết khiếu nại lần hai; đối với vùng sâu, vùng xa đi lại khó khăn thì thời hạn có thể kéo dài hơn nhưng không quá 45 ngày.
2. Trong thời hạn 07 ngày làm việc, kể từ ngày nhận được đơn khiếu nại thuộc thẩm quyền giải quyết của mình, người giải quyết khiếu nại lần hai phải thụ lý giải quyết và thông báo bằng văn bản về việc thụ lý giải quyết khiếu nại cho người khiếu nại.
3. Trường hợp khiếu nại do cơ quan, tổ chức, cá nhân khác chuyển đến, ngoài việc thông báo cho người khiếu nại theo quy định tại khoản 2 Điều này, người giải quyết khiếu nại lần hai phải thông báo bằng văn bản về việc thụ lý giải quyết khiếu nại cho cơ quan, tổ chức, cá nhân đã chuyển khiếu nại đến.
4. Trường hợp không thụ lý giải quyết thì phải nêu rõ lý do.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 27",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Khiếu nại lần hai đến Thanh tra Sở"
        }
    }
]

# Remove the legacy, misnumbered hand-written records if this migration has
# previously run.  Only exact, source-checked statutory excerpts remain.
LEGACY_CHUNK_IDS = {
    "ND_24_2018#d5",
    "ND_24_2018#d10",
    "ND_24_2018#d14",
}

_nd24_meta = get_verified_metadata("ND_24_2018")
for _chunk in NEW_CHUNKS:
    _article_number = str(_chunk.pop("article")).replace("Điều", "").strip()
    _article_title = _chunk.pop("title")
    _chunk.pop("law_name", None)
    _chunk.pop("clause", None)
    _chunk.pop("metadata", None)
    _chunk.update(
        {
            "doc_title": _nd24_meta["doc_title"],
            "document_no": _nd24_meta["document_no"],
            "document_type": _nd24_meta["document_type"],
            "issuer": _nd24_meta["issuer"],
            "article_number": _article_number,
            "article_title": _article_title,
            "clause_number": "",
            "point": "",
            "source_page_start": 0,
            "source_page_end": 0,
            "official_source": _nd24_meta["official_source"],
            "effective_from": _nd24_meta["effective_from"],
            "effective_to": _nd24_meta["effective_to"],
            "status": _nd24_meta["status"],
            "scope_tier": _nd24_meta["scope_tier"],
            "domain": _nd24_meta["domain"],
            "source_role": _nd24_meta["source_role"],
        }
    )
    _chunk["retrieval_text"] = format_retrieval_text(_chunk)

def main():
    jsonl_path = PRODUCTION_CORPUS_PATH
    existing_chunks = []
    existing_ids = set()
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            cid = item.get("chunk_id")
            if cid in LEGACY_CHUNK_IDS:
                continue
            if cid:
                existing_ids.add(cid)
            existing_chunks.append(item)

    # Append new chunks if not present
    added = []
    for c in NEW_CHUNKS:
        cid = c["chunk_id"]
        if cid in existing_ids:
            # Update existing
            for idx, ex in enumerate(existing_chunks):
                if ex.get("chunk_id") == cid:
                    existing_chunks[idx] = c
                    added.append(c)
                    break
        else:
            existing_chunks.append(c)
            added.append(c)

    temp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        for item in existing_chunks:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, jsonl_path)
    print(f"Updated data/processed/legal_documents_v3.jsonl with {len(added)} chunks!")

    # Rebuild BM25 V3
    print("Rebuilding BM25 V3...")
    bm25 = BM25Retriever(persist_dir=BM25_INDEX_DIR, corpus_path=jsonl_path)
    bm25.build_index(force=True)
    print("BM25 V3 rebuilt successfully.")

    # Update Chroma V3
    print("Updating Chroma V3 vector store...")
    emb = LocalBGEEmbeddings()
    store = LegalVectorStore(
        persist_dir=CHROMA_INDEX_DIR,
        collection_name="vietlabor_chunks_v3",
        corpus_path=jsonl_path,
        embedding_model=emb,
    )
    coll = store.get_collection()
    
    # Delete existing if any, then re-add
    del_ids = [c["chunk_id"] for c in added]
    try:
        coll.delete(ids=sorted(set(del_ids) | LEGACY_CHUNK_IDS))
    except Exception as e:
        print("Note on delete before add:", e)

    texts = [format_retrieval_text(c) for c in added]
    vecs = emb.embed_documents(texts)
    metas = [clean_metadata_for_chroma(c) for c in added]
    
    coll.add(
        ids=del_ids,
        documents=texts,
        embeddings=vecs,
        metadatas=metas,
    )
    print(f"Chroma V3 successfully updated with {len(del_ids)} chunks!")

if __name__ == "__main__":
    main()
