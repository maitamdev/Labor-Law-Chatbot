# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.abspath("."))
import json
from pathlib import Path
from rag.embeddings import LocalBGEEmbeddings, format_retrieval_text
from rag.vectorstore import LegalVectorStore, clean_metadata_for_chroma
from rag.bm25_retriever import BM25Retriever

NEW_D5_K1_CONTENT = """1. Người lao động có các quyền sau đây:
a) Làm việc; tự do lựa chọn việc làm, nơi làm việc, nghề nghiệp, học nghề, nâng cao trình độ nghề nghiệp; không bị phân biệt đối xử, cưỡng bức lao động, quấy rối tình dục tại nơi làm việc;
b) Hưởng lương phù hợp với trình độ, kỹ năng nghề trên cơ sở thỏa thuận với người sử dụng lao động; được bảo hộ lao động, làm việc trong điều kiện bảo đảm về an toàn, vệ sinh lao động; nghỉ theo chế độ, nghỉ hằng năm có hưởng lương và được hưởng quyền lợi phúc lợi tập thể;
c) Thành lập, gia nhập, hoạt động trong tổ chức đại diện người lao động, tổ chức nghề nghiệp và tổ chức khác theo quy định của pháp luật; yêu cầu và tham gia đối thoại, thực hiện quy chế dân chủ, thương lượng tập thể với người sử dụng lao động và được tham vấn tại nơi làm việc để bảo vệ quyền và lợi ích hợp pháp, chính đáng của mình; tham gia quản lý theo nội quy của người sử dụng lao động;
d) Từ chối làm việc nếu có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe trong quá trình thực hiện công việc;
đ) Đơn phương chấm dứt hợp đồng lao động;
e) Đình công;
g) Các quyền khác theo quy định của pháp luật."""

def main():
    jsonl_path = Path("data/processed/legal_documents_v3.jsonl")
    lines = []
    updated_chunk = None
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line.strip())
            if item.get("chunk_id") == "VBHN_18_2026#d5-k1":
                item["content"] = NEW_D5_K1_CONTENT
                updated_chunk = item
            lines.append(item)
    
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("Updated data/processed/legal_documents_v3.jsonl successfully!")

    # Rebuild BM25 V3
    print("Rebuilding BM25 V3 index...")
    bm25 = BM25Retriever(persist_dir="storage/bm25_v3", corpus_path=str(jsonl_path))
    bm25.build_index(force=True)
    print("BM25 V3 rebuilt.")

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
    try:
        coll.delete(ids=["VBHN_18_2026#d5-k1"])
    except Exception as e:
        print("Delete old d5-k1 warning:", e)
    
    doc_text = format_retrieval_text(updated_chunk)
    vec = emb.embed_documents([doc_text])[0]
    meta = clean_metadata_for_chroma(updated_chunk)
    coll.add(
        ids=["VBHN_18_2026#d5-k1"],
        embeddings=[vec],
        documents=[doc_text],
        metadatas=[meta],
    )
    print("Chroma V3 updated with enriched VBHN_18_2026#d5-k1!")

if __name__ == "__main__":
    main()
