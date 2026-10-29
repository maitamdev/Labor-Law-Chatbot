"""Background admin jobs. Versioned indexes; business backups exclude private chats."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from app.accounts import AccountError
from app.admin_service import safe_id, utcnow
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, PRODUCTION_CORPUS_PATH, STORAGE_DIR

EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vietlabor-admin")
_SUBMITTED = set()
_LOCK = threading.Lock()
_HEARTBEAT_INTERVAL = 60
_STALE_AFTER = timedelta(minutes=10)
BACKUP_DIR = STORAGE_DIR / "admin_backups"
INDEX_DIR = STORAGE_DIR / "admin_indexes"
POINTER = INDEX_DIR / "active.json"


def active_index():
    if not POINTER.is_file():
        return None
    try:
        data = json.loads(POINTER.read_text(encoding="utf-8"))
        version = str(uuid.UUID(data["version"]))
        root = INDEX_DIR / version
        if not (root / "complete.json").is_file():
            return None
        return {"version": version, "root": root}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def launch(accounts, job_id, *, admin_checked=False):
    if not admin_checked:
        accounts.require_admin()
    job_id = safe_id(job_id)
    with _LOCK:
        if job_id in _SUBMITTED:
            return
        _SUBMITTED.add(job_id)
    try:
        EXECUTOR.submit(_run, accounts, job_id)
    except RuntimeError as exc:
        with _LOCK:
            _SUBMITTED.discard(job_id)
        raise AccountError("Worker quản trị đã dừng. Khởi động lại ứng dụng để tiếp tục tác vụ.") from exc


def resume_jobs(accounts, profile, jobs):
    """Requeue unfinished administrator work after a restart; SQL claims it once."""
    accounts.require_admin()
    now = datetime.now(timezone.utc)
    for job in sorted(jobs, key=lambda item: str(item.get("created_at", ""))):
        if job.get("status") == "pending":
            launch(accounts, job["id"], admin_checked=True)
            continue
        if job.get("status") != "running":
            continue
        try:
            started = datetime.fromisoformat(str(job.get("started_at", "")).replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        except ValueError:
            started = datetime.min.replace(tzinfo=timezone.utc)
        if now - started > _STALE_AFTER:
            launch(accounts, job["id"], admin_checked=True)


def _keep_job_alive(accounts, job_id, lease_token, stop):
    while not stop.wait(_HEARTBEAT_INTERVAL):
        try:
            accounts.rpc("touch_admin_job", {"job_id": job_id, "requested_lease": lease_token})
        except AccountError:
            continue


def _run(accounts, job_id):
    heartbeat = None
    heartbeat_stop = threading.Event()
    lease_token = None
    try:
        requested_lease = str(uuid.uuid4())
        lease_token = requested_lease
        job = accounts.rpc(
            "claim_admin_job", {"job_id": job_id, "requested_lease": requested_lease}
        )
        lease_token = str(job.get("lease_token") or requested_lease)
        heartbeat = threading.Thread(
            target=_keep_job_alive,
            args=(accounts, job_id, lease_token, heartbeat_stop),
            daemon=True,
            name="vietlabor-job-heartbeat",
        )
        heartbeat.start()
        if job["kind"] == "health":
            result = json.dumps(health(), ensure_ascii=False)
        elif job["kind"] == "backup":
            result = create_backup(accounts)
        elif job["kind"] == "restore":
            result = restore_backup(accounts, job.get("payload", {}).get("backup_id"), job_id, lease_token)
        elif job["kind"] == "index":
            result = publish_index(accounts, job_id, lease_token)
        else:
            raise AccountError("Loại tiến trình không được hỗ trợ.")
        accounts.rpc(
            "finish_admin_job",
            {"job_id": job_id, "requested_lease": lease_token, "succeeded": True, "job_result": str(result)[:4000]},
        )
    except Exception:
        if lease_token:
            try:
                accounts.rpc(
                    "finish_admin_job",
                    {
                        "job_id": job_id,
                        "requested_lease": lease_token,
                        "succeeded": False,
                        "job_result": "Tiến trình chưa hoàn tất. Kiểm tra kết nối, dữ liệu nguồn và cấu hình dịch vụ rồi chạy lại.",
                    },
                )
            except AccountError:
                pass
    finally:
        heartbeat_stop.set()
        if heartbeat:
            heartbeat.join(timeout=2)
        with _LOCK:
            _SUBMITTED.discard(job_id)


def health():
    try:
        response = requests.get(OLLAMA_BASE_URL + "/api/tags", timeout=(2, 4))
        response.raise_for_status()
        names = {m.get("name") for m in response.json().get("models", [])}
        model = "ready" if OLLAMA_MODEL in names else "missing_model"
    except (requests.RequestException, ValueError):
        model = "offline"
    return {
        "ollama": model,
        "model": OLLAMA_MODEL,
        "active_index": (active_index() or {}).get("version", "v3"),
        "checked_at": utcnow(),
    }


def create_backup(accounts):
    accounts.require_admin()
    # Deliberately no profiles, auth.users, conversations or private message text.
    data = {
        "format": "vietlabor-business-v1",
        "created_at": utcnow(),
        "documents": accounts.rows("legal_documents"),
        "settings": accounts.rows("app_settings", order="updated_at.desc"),
    }
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    envelope = {"sha256": hashlib.sha256(raw).hexdigest(), "data": data}
    backup_id = str(uuid.uuid4())
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / (backup_id + ".json")
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return (
        "Đã sao lưu cấu hình và metadata văn bản: "
        + backup_id
        + ". Không chứa tài khoản, mật khẩu hoặc lịch sử chat. Tệp PDF gốc nằm trong Supabase Storage."
    )


def list_backups():
    if not BACKUP_DIR.exists():
        return []
    return [
        {"id": p.stem, "created_at": p.stat().st_mtime, "size": p.stat().st_size}
        for p in sorted(BACKUP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    ]


def restore_backup(accounts, backup_id, job_id, lease_token):
    accounts.require_admin()
    path = BACKUP_DIR / (safe_id(backup_id) + ".json")
    if not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
        raise AccountError("Bản sao lưu không hợp lệ.")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    data = envelope["data"]
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != envelope["sha256"] or data.get("format") != "vietlabor-business-v1":
        raise AccountError("Bản sao lưu không vượt qua kiểm tra toàn vẹn.")
    # One DB transaction, whitelisted metadata only. No role/history restoration.
    accounts.rpc(
        "restore_business_metadata_for_job",
        {"job_id": job_id, "requested_lease": lease_token, "snapshot": data},
    )
    return "Đã khôi phục cấu hình và metadata văn bản. Văn bản chuyển về chờ duyệt; chỉ mục đang phục vụ không bị thay thế."


def publish_index(accounts, job_id, lease_token):
    accounts.require_admin()
    import fitz

    from ingestion.parser import LegalParser
    from ingestion.schemas import PageText
    from rag.bm25_retriever import BM25Retriever
    from rag.vectorstore import LegalVectorStore

    documents = accounts.rows("legal_documents", filters={"status": "in.(approved,indexed)"})
    if not documents:
        raise AccountError("Không có văn bản đã được duyệt.")
    version = str(uuid.uuid4())
    root = INDEX_DIR / version
    root.mkdir(parents=True, exist_ok=False)
    corpus = root / "corpus.jsonl"
    # Original production corpus is read only. Build a complete new generation.
    base = PRODUCTION_CORPUS_PATH.read_text(encoding="utf-8")
    with corpus.open("w", encoding="utf-8") as output:
        output.write(base.rstrip() + "\n")
        for doc in documents:
            raw = accounts.download(doc["storage_path"])
            if hashlib.sha256(raw).hexdigest() != doc["sha256"]:
                raise AccountError("Tệp nguồn đã thay đổi sau kiểm duyệt.")
            doc_id = "ADMIN_" + doc["id"].replace("-", "")
            with fitz.open(stream=raw, filetype="pdf") as pdf:
                pages = [
                    PageText(doc_id=doc_id, filename=doc["file_name"], page_number=i + 1, text=page.get_text())
                    for i, page in enumerate(pdf.pages())
                ]
            chunks = LegalParser(
                {
                    "doc_id": doc_id,
                    "doc_title": doc["title"],
                    "filename": doc["file_name"],
                    "document_no": doc["document_no"],
                    "issuer": doc["issuer"],
                    "official_source": doc["source_url"],
                    "effective_from": doc["effective_from"],
                    "status": doc["validity"],
                }
            ).parse_pages(pages)
            if not chunks:
                raise AccountError("Không trích xuất được cấu trúc pháp luật từ văn bản.")
            for chunk in chunks:
                output.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")
    BM25Retriever(persist_dir=root / "bm25", corpus_path=corpus).build_index(force=True)
    store = LegalVectorStore(persist_dir=root / "chroma", collection_name="vietlabor_chunks_v3", corpus_path=corpus)
    store.build_index(force=True, batch_size=32)
    if not store.is_index_valid(strict=True):
        raise AccountError("Chỉ mục chưa được đồng bộ đầy đủ.")
    # Recheck metadata/reviews immediately before activating. Failed/stale build
    # leaves the old index and source corpus untouched.
    current = accounts.rows("legal_documents", filters={"status": "in.(approved,indexed)"})

    def signature(docs):
        return sorted((d["id"], d["sha256"], d["updated_at"]) for d in docs)

    if signature(current) != signature(documents):
        raise AccountError("Kho văn bản đã thay đổi trong lúc lập chỉ mục. Hãy chạy lại.")
    (root / "complete.json").write_text(
        json.dumps({"version": version, "documents": [d["id"] for d in documents], "created_at": utcnow()}),
        encoding="utf-8",
    )
    temp = INDEX_DIR / (version + ".tmp")
    temp.write_text(json.dumps({"version": version}), encoding="utf-8")
    accounts.rpc("assert_admin_job_lease", {"job_id": job_id, "requested_lease": lease_token})
    os.replace(temp, POINTER)
    for doc in documents:
        accounts.rest(
            "PATCH",
            "legal_documents",
            params={"id": "eq." + doc["id"], "updated_at": "eq." + doc["updated_at"]},
            body={"status": "indexed"},
        )
    return "Đã kích hoạt chỉ mục " + version + ". Phiên chat mới sử dụng phiên bản này."
