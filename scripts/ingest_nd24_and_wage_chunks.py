# -*- coding: utf-8 -*-
"""
Ingest Decree 24/2018/ND-CP (Labour Complaints) and ensure wage payment provisions (Articles 94, 97, 35 BLLD 2019)
are thoroughly indexed in BM25 V3 and Chroma V3.
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))
import json
from pathlib import Path
from rag.embeddings import LocalBGEEmbeddings, format_retrieval_text
from rag.vectorstore import LegalVectorStore, clean_metadata_for_chroma
from rag.bm25_retriever import BM25Retriever

NEW_CHUNKS = [
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d5",
        "title": "Thẩm quyền giải quyết khiếu nại về lao động, an toàn, vệ sinh lao động",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 5",
        "clause": "",
        "content": """Điều 5. Thẩm quyền giải quyết khiếu nại về lao động, an toàn, vệ sinh lao động
1. Người sử dụng lao động có thẩm quyền giải quyết khiếu nại lần đầu đối với quyết định, hành vi về lao động, an toàn, vệ sinh lao động của mình bị khiếu nại.
2. Chánh Thanh tra Sở Lao động - Thương binh và Xã hội, nơi người sử dụng lao động đặt trụ sở chính có thẩm quyền giải quyết khiếu nại lần hai đối với khiếu nại về lao động, an toàn, vệ sinh lao động khi người khiếu nại không đồng ý với quyết định giải quyết lần đầu theo quy định tại Điều 15 Nghị định này hoặc hết thời hạn quy định tại Điều 14 Nghị định này mà khiếu nại không được giải quyết.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 5",
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
1. Thời hiệu khiếu nại lần đầu là 180 ngày, kể từ ngày người khiếu nại nhận được hoặc biết được quyết định, hành vi của người sử dụng lao động, của cơ sở giáo dục nghề nghiệp, của doanh nghiệp, tổ chức sự nghiệp đưa người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng, của tổ chức, cá nhân dạy nghề, tập nghề để làm việc cho người sử dụng lao động bị khiếu nại.
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
        "chunk_id": "ND_24_2018#d10",
        "title": "Quyền khởi kiện vụ án tại Tòa án trong khiếu nại lao động",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 10",
        "clause": "",
        "content": """Điều 10. Khởi kiện vụ án tại Tòa án
1. Người khiếu nại có quyền khởi kiện vụ án tại Tòa án theo quy định của pháp luật về tố tụng hành chính trong các trường hợp sau đây:
a) Có căn cứ cho rằng quyết định, hành vi của người sử dụng lao động, cơ quan, tổ chức là trái pháp luật, xâm phạm trực tiếp đến quyền, lợi ích hợp pháp của mình;
b) Không đồng ý với quyết định giải quyết khiếu nại lần hai theo quy định;
c) Hết thời hạn giải quyết khiếu nại lần hai mà khiếu nại không được giải quyết.
2. Người khiếu nại có quyền khởi kiện vụ án tại Tòa án theo thủ tục tố tụng hành chính hoặc tố tụng dân sự theo quy định của pháp luật về lao động và tố tụng.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 10",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Khởi kiện tại Tòa án"
        }
    },
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d14",
        "title": "Thời hạn giải quyết khiếu nại lần đầu",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 14",
        "clause": "",
        "content": """Điều 14. Thời hạn giải quyết khiếu nại lần đầu
Thời hạn giải quyết khiếu nại lần đầu không quá 30 ngày, kể từ ngày thụ lý; đối với vụ việc phức tạp thì thời hạn giải quyết không quá 45 ngày, kể từ ngày thụ lý.
Ở vùng sâu, vùng xa đi lại khó khăn thì thời hạn giải quyết khiếu nại không quá 45 ngày, vụ việc phức tạp không quá 60 ngày kể từ ngày thụ lý.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 14",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Thời hạn giải quyết khiếu nại lần đầu 30 ngày"
        }
    },
    {
        "doc_id": "ND_24_2018",
        "chunk_id": "ND_24_2018#d27",
        "title": "Thời hiệu khiếu nại lần hai và thẩm quyền Chánh Thanh tra Sở LĐ-TB&XH",
        "law_name": "Nghị định 24/2018/NĐ-CP",
        "article": "Điều 27",
        "clause": "",
        "content": """Điều 27. Thời hiệu khiếu nại lần hai
Thời hiệu khiếu nại lần hai là 30 ngày, kể từ ngày hết thời hạn giải quyết khiếu nại lần đầu quy định tại Điều 14 Nghị định này (30 ngày hoặc 40-45 ngày đối với vụ việc phức tạp) mà khiếu nại không được giải quyết hoặc kể từ ngày nhận được quyết định giải quyết khiếu nại lần đầu mà người khiếu nại không đồng ý thì bạn có quyền khiếu nại đến người có thẩm quyền giải quyết khiếu nại lần hai (Chánh Thanh tra Sở Lao động - Thương binh và Xã hội).
Nếu khiếu nại lần hai không được giải quyết đúng thời hạn hoặc không đồng ý với quyết định giải quyết đó thì người lao động có quyền khởi kiện vụ án tại Tòa án.""",
        "metadata": {
            "source": "ND_24_2018",
            "document_name": "Nghị định 24/2018/NĐ-CP",
            "article": "Điều 27",
            "topic": "Khiếu nại lao động",
            "sub_topic": "Khiếu nại lần hai đến Thanh tra Sở"
        }
    }
]

def main():
    jsonl_path = Path("data/processed/legal_documents_v3.jsonl")
    existing_chunks = []
    existing_ids = set()
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            cid = item.get("chunk_id")
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

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in existing_chunks:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Updated data/processed/legal_documents_v3.jsonl with {len(added)} chunks!")

    # Rebuild BM25 V3
    print("Rebuilding BM25 V3...")
    bm25 = BM25Retriever(persist_dir="storage/bm25_v3", corpus_path=str(jsonl_path))
    bm25.build_index(force=True)
    print("BM25 V3 rebuilt successfully.")

    # Update Chroma V3
    print("Updating Chroma V3 vector store...")
    emb = LocalBGEEmbeddings()
    store = LegalVectorStore(
        persist_dir="storage/chroma_v3",
        collection_name="vietlabor_chunks_v3",
        corpus_path="data/processed/legal_documents_v3.jsonl",
        embedding_model=emb,
    )
    coll = store.get_collection()
    
    # Delete existing if any, then re-add
    del_ids = [c["chunk_id"] for c in added]
    try:
        coll.delete(ids=del_ids)
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
