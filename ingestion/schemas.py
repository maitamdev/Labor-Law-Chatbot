from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class PageText(BaseModel):
    """Schema representing raw extracted text from a single PDF page."""
    model_config = ConfigDict(frozen=True)

    doc_id: str = Field(..., description="Unique document ID from manifest (e.g. TT_10_2020)")
    filename: str = Field(..., description="PDF file name")
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    text: str = Field(..., description="Raw text extracted from this page")


class LegalChunk(BaseModel):
    """Schema representing a structured legal chunk (Article, Clause, or Point)."""
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(..., description="Deterministic unique ID: e.g. VBHN_18_2026#d25-k1-a")

    # Document-level metadata
    doc_id: str = Field(..., description="Document identifier matching manifest")
    doc_title: str = Field(..., description="Official title of the legal document")
    document_no: Optional[str] = Field(None, description="Document number e.g. 10/2020/TT-BLĐTBXH")
    document_type: Optional[str] = Field(None, description="Type of document e.g. Thông tư, Nghị định, Luật")
    issuer: Optional[str] = Field(None, description="Issuing agency or authority")

    # Structural legal hierarchy
    part: Optional[str] = Field(None, description="Part / Phần (e.g. PHẦN THỨ NHẤT)")
    chapter: Optional[str] = Field(None, description="Chapter / Chương (e.g. Chương II)")
    section: Optional[str] = Field(None, description="Section / Mục (e.g. Mục 1)")

    # Legal unit markers
    article_number: Optional[str] = Field(None, description="Article number e.g. 25 or 25a")
    article_title: Optional[str] = Field(None, description="Title of the article e.g. Thời gian thử việc")
    clause_number: Optional[str] = Field(None, description="Clause / Khoản number e.g. 1, 2")
    point: Optional[str] = Field(None, description="Point / Điểm letter e.g. a, b, c")

    # Body content
    content: str = Field(..., min_length=1, description="Normalized substantive text content of the chunk")
    table_data: Optional[Any] = Field(None, description="Structured table data if chunk contains a table")

    # Provenance & Source Metadata
    source_file: str = Field(..., description="Source filename")
    source_page_start: int = Field(..., ge=1, description="Starting page in source document (1-indexed)")
    source_page_end: int = Field(..., ge=1, description="Ending page in source document (1-indexed)")
    extraction_method: str = Field(
        default="pdf_text",
        description="Method used to extract text: official_text, pdf_text, local_ocr"
    )
    ocr_engine: Optional[str] = Field(None, description="OCR engine name e.g. paddleocr+vietocr")
    ocr_model: Optional[str] = Field(None, description="OCR model name e.g. vgg_seq2seq")
    text_source_url: Optional[str] = Field(None, description="Direct URL of the source page or text portal")
    extraction_timestamp: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of extraction")

    # Validity & Source metadata (from verified manifest / metadata only, otherwise None)
    signer: Optional[str] = Field(None, description="Signer / Người ký xác thực")
    effective_from: Optional[str] = Field(None, description="Effective date (YYYY-MM-DD) if verified")
    effective_to: Optional[str] = Field(None, description="Expiry date (YYYY-MM-DD) if verified")
    status: Optional[str] = Field("CURRENT", description="Validity status: CURRENT, PARTIALLY_EFFECTIVE, REPEALED, HISTORICAL")
    official_source: Optional[str] = Field(None, description="Official portal URL or verified source")

    # Phase 5G - Extended Scope & Domain Metadata
    scope_tier: Optional[str] = Field("core", description="Scope tier: core or extended")
    domain: Optional[str] = Field("CORE_LABOR", description="Legal domain: CORE_LABOR, RETIREMENT, UNEMPLOYMENT_INSURANCE, FOREIGN_WORKER, UNKNOWN")
    amends: Optional[str] = Field(None, description="Document amended by this doc")
    amended_by: Optional[str] = Field(None, description="Document amending this doc")
    replaces: Optional[str] = Field(None, description="Document replaced by this doc")
    replaced_by: Optional[str] = Field(None, description="Document replacing this doc")
