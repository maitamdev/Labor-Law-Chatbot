from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        getattr(sys.stdout, "reconfigure")(encoding="utf-8")
        getattr(sys.stderr, "reconfigure")(encoding="utf-8")
    except Exception:
        pass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# VietLabor AI
# Official Vietnamese labor-law PDF downloader
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
CORE_DIR = RAW_DIR / "core"
REFERENCE_DIR = RAW_DIR / "references"
AMENDMENT_DIR = RAW_DIR / "amendments"

MANIFEST_PATH = RAW_DIR / "download_manifest.csv"


# ============================================================
# DANH SÁCH VĂN BẢN
#
# include_in_rag:
#   True  = dự kiến đưa vào corpus chính
#   False = chỉ lưu để đối chiếu/lịch sử
# ============================================================

DOCUMENTS = [

    # --------------------------------------------------------
    # CORE - CORPUS CHÍNH
    # --------------------------------------------------------

    {
        "id": "VBHN_18_2026",
        "title": "Văn bản hợp nhất 18/VBHN-VPQH - Bộ luật Lao động",
        "filename": "01_18_VBHN_VPQH_2026_Bo_Luat_Lao_Dong.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=0&docid=217002&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/02/18-vbhn-vpqh.pdf",
    },

    {
        "id": "ND_145_2020",
        "title": "Nghị định 145/2020/NĐ-CP",
        "filename": "02_145_2020_ND_CP.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/default.aspx?docid=201967&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/12/145.signed.pdf",
    },

    {
        "id": "TT_10_2020",
        "title": "Thông tư 10/2020/TT-BLĐTBXH",
        "filename": "03_10_2020_TT_BLDTBXH.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vbpl.vn/TW/Pages/vbpq-van-ban-goc.aspx?ItemID=146696",
        "pdf_url":
            "https://vbpl-bientap-gateway.moj.gov.vn/api/qtdc/public/doc/minio/buckets/"
            "vbpl/146696/VanBanGoc_TT%2010%202020%20BL%C4%90TBXH.pdf/download",
    },

    {
        "id": "ND_293_2025",
        "title": "Nghị định 293/2025/NĐ-CP - Mức lương tối thiểu",
        "filename": "04_293_2025_ND_CP_Luong_Toi_Thieu.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/?docid=215832&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/11/"
            "293-cp.signed.pdf",
    },

    {
        "id": "ND_12_2022",
        "title": "Nghị định 12/2022/NĐ-CP - Xử phạt vi phạm lĩnh vực lao động",
        "filename": "05_12_2022_ND_CP_Xu_Phat_Lao_Dong.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=0&docid=205182&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2022/01/"
            "12-2022-nd.signed.pdf",
    },

    {
        "id": "ND_337_2025",
        "title": "Nghị định 337/2025/NĐ-CP - Hợp đồng lao động điện tử",
        "filename": "06_337_2025_ND_CP_Hop_Dong_Lao_Dong_Dien_Tu.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=0&docid=216284&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/12/"
            "337-cp.signed.pdf",
    },

    {
        "id": "TT_08_2026",
        "title": "Thông tư 08/2026/TT-BNV - Hợp đồng lao động điện tử",
        "filename": "07_08_2026_TT_BNV_Hop_Dong_Lao_Dong_Dien_Tu.pdf",
        "category": "core",
        "include_in_rag": True,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=0&docid=218200&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/5/08-bnv.pdf",
    },


    # --------------------------------------------------------
    # REFERENCE
    # Bản gốc để nghiên cứu/đối chiếu.
    # Không index mặc định vì đã có VBHN 18/2026.
    # --------------------------------------------------------

    {
        "id": "BLLD_45_2019",
        "title": "Bộ luật Lao động 45/2019/QH14 - Bản gốc",
        "filename": "45_2019_QH14_Bo_Luat_Lao_Dong_Ban_Goc.pdf",
        "category": "references",
        "include_in_rag": False,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160&typegroupid=3",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/12/45.signed.pdf",
    },


    # --------------------------------------------------------
    # AMENDMENTS / DOCUMENTS AFFECTING ND 145/2020
    #
    # Lưu để kiểm tra quan hệ sửa đổi.
    # Không đưa cả văn bản vào RAG một cách mù quáng.
    # --------------------------------------------------------

    {
        "id": "ND_35_2022",
        "title": "Nghị định 35/2022/NĐ-CP",
        "filename": "35_2022_ND_CP.pdf",
        "category": "amendments",
        "include_in_rag": False,
        "source_page":
            "https://vanban.chinhphu.vn/?docid=205861&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2022/05/"
            "35-2022-nd.signed.pdf",
    },

    {
        "id": "ND_10_2024",
        "title": "Nghị định 10/2024/NĐ-CP",
        "filename": "10_2024_ND_CP.pdf",
        "category": "amendments",
        "include_in_rag": False,
        "source_page":
            "https://vanban.chinhphu.vn/?docid=209657&pageid=27160",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/02/"
            "10-cp.signed.pdf",
    },

    {
        "id": "ND_129_2025",
        "title": "Nghị định 129/2025/NĐ-CP",
        "filename": "129_2025_ND_CP.pdf",
        "category": "amendments",
        "include_in_rag": False,
        "source_page":
            "https://vanban.chinhphu.vn/?classid=1&docid=213920&pageid=27160&typegroupid=4",
        "pdf_url":
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/6/"
            "129nd.signed.pdf",
    },
]


# ============================================================
# NETWORK SESSION
# ============================================================

def create_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36 "
            "VietLaborAI-AcademicProject/1.0"
        ),
        "Accept": "application/pdf,*/*;q=0.8",
    })

    return session


# ============================================================
# HELPERS
# ============================================================

def get_destination(document: dict) -> Path:
    category = document["category"]

    if category == "core":
        return CORE_DIR / document["filename"]

    if category == "references":
        return REFERENCE_DIR / document["filename"]

    if category == "amendments":
        return AMENDMENT_DIR / document["filename"]

    raise ValueError(f"Unknown category: {category}")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def is_valid_pdf(path: Path) -> bool:
    if not path.exists():
        return False

    if path.stat().st_size < 100:
        return False

    with path.open("rb") as file:
        header = file.read(5)

    return header == b"%PDF-"


# ============================================================
# DOWNLOAD
# ============================================================

def download_pdf(
    session: requests.Session,
    document: dict,
) -> dict:

    destination = get_destination(document)

    print()
    print("=" * 70)
    print(f"Văn bản : {document['title']}")
    print(f"Nguồn   : {document['source_page']}")
    print(f"PDF     : {document['pdf_url']}")
    print(f"Lưu tại : {destination}")
    print("=" * 70)

    # Skip nếu file đã tồn tại và hợp lệ
    if destination.exists() and is_valid_pdf(destination):
        print("[SKIP] File đã tồn tại và là PDF hợp lệ.")

        return {
            **document,
            "local_path": str(destination.relative_to(PROJECT_ROOT)),
            "status": "existing",
            "size_bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "downloaded_at": "",
        }

    temp_path = destination.with_suffix(".pdf.part")

    try:
        with session.get(
            document["pdf_url"],
            stream=True,
            timeout=(15, 180),
            allow_redirects=True,
        ) as response:

            response.raise_for_status()

            content_type = (
                response.headers
                .get("Content-Type", "")
                .lower()
            )

            print(
                f"[INFO] HTTP {response.status_code} "
                f"| Content-Type: {content_type}"
            )

            with temp_path.open("wb") as file:
                downloaded = 0

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded += len(chunk)

                    mb = downloaded / (1024 * 1024)
                    print(
                        f"\r[DOWNLOAD] {mb:.2f} MB",
                        end="",
                        flush=True,
                    )

        print()

        if not is_valid_pdf(temp_path):
            temp_path.unlink(missing_ok=True)

            raise RuntimeError(
                "File tải xuống không có PDF signature %PDF-. "
                "Có thể website đã trả HTML/error page."
            )

        temp_path.replace(destination)

        file_hash = sha256_file(destination)

        print(
            f"[OK] {destination.name} "
            f"({destination.stat().st_size / 1024 / 1024:.2f} MB)"
        )
        print(f"[SHA256] {file_hash}")

        return {
            **document,
            "local_path": str(
                destination.relative_to(PROJECT_ROOT)
            ),
            "status": "downloaded",
            "size_bytes": destination.stat().st_size,
            "sha256": file_hash,
            "downloaded_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except Exception as error:
        temp_path.unlink(missing_ok=True)

        print(f"[ERROR] {document['title']}")
        print(f"        {error}")

        return {
            **document,
            "local_path": str(
                destination.relative_to(PROJECT_ROOT)
            ),
            "status": "error",
            "size_bytes": 0,
            "sha256": "",
            "downloaded_at": "",
            "error": str(error),
        }


# ============================================================
# MANIFEST
# ============================================================

def save_manifest(results: list[dict]) -> None:

    fields = [
        "id",
        "title",
        "category",
        "include_in_rag",
        "filename",
        "source_page",
        "pdf_url",
        "local_path",
        "status",
        "size_bytes",
        "sha256",
        "downloaded_at",
        "error",
    ]

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()

        for result in results:
            writer.writerow(result)

    print()
    print(f"[MANIFEST] {MANIFEST_PATH}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    CORE_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    AMENDMENT_DIR.mkdir(parents=True, exist_ok=True)

    session = create_session()

    results = []

    print()
    print("==============================================")
    print(" VietLabor AI - Official Law PDF Downloader")
    print("==============================================")
    print(f"Documents: {len(DOCUMENTS)}")
    print()

    for document in DOCUMENTS:
        result = download_pdf(session, document)
        results.append(result)

    save_manifest(results)

    downloaded = sum(
        r["status"] == "downloaded"
        for r in results
    )

    existing = sum(
        r["status"] == "existing"
        for r in results
    )

    failed = sum(
        r["status"] == "error"
        for r in results
    )

    print()
    print("==============================================")
    print(" DOWNLOAD SUMMARY")
    print("==============================================")
    print(f"Total      : {len(results)}")
    print(f"Downloaded : {downloaded}")
    print(f"Existing   : {existing}")
    print(f"Failed     : {failed}")
    print("==============================================")

    if failed:
        print()
        print(
            "Một số file không tải được. "
            "Kiểm tra download_manifest.csv."
        )


if __name__ == "__main__":
    main()
