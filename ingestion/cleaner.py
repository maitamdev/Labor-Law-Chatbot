from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from ingestion.schemas import PageText

logger = logging.getLogger(__name__)

# Cong Bao running header pattern
CONG_BAO_HEADER_REGEX = re.compile(
    r"^\s*(?:CÔNG\s+BÁO/Số\s+[^\n]+|VĂN\s+BẢN\s+QUY\s+PHẠM\s+PHÁP\s+LUẬT)\s*$",
    re.IGNORECASE,
)

# Standalone headings that should NEVER have body text merged into them
STRUCTURAL_HEADING_REGEX = re.compile(
    r"^\s*(?:"
    r"PHẦN\s+(?:THỨ\s+)?[IVXLCDM\d]+"
    r"|Chương\s+[IVXLCDM\d]+"
    r"|CHƯƠNG\s+[IVXLCDM\d]+"
    r"|Mục\s+\d+"
    r"|MỤC\s+\d+"
    r"|THÔNG\s+TƯ"
    r"|NGHỊ\s+ĐỊNH"
    r"|LUẬT"
    r"|BỘ\s+LUẬT"
    r"|CỘNG\s+HÒA\s+XÃ\s+HỘI"
    r"|Độc\s+lập\s+–\s+Tự\s+do"
    r"|Số:\s*"
    r"|Hà\s+Nội,"
    r"|Nơi\s+nhận:"
    r")\b",
    re.IGNORECASE,
)

# Markers that indicate the START of a new structural unit on next_line
STRUCTURAL_PREFIX_REGEX = re.compile(
    r"^\s*(?:"
    r"PHẦN\s+(?:THỨ\s+)?[IVXLCDM\d]+"
    r"|(?:CHƯƠNG|Chương|Chuong|CHUONG)\s+[IVXLCDM\d]+(?:\s*$|\.|\s*:)"
    r"|Mục\s+\d+"
    r"|MỤC\s+\d+"
    r"|Muc\s+\d+"
    r"|Điều\s+\d+[a-z]?"
    r"|ĐIỀU\s+\d+[a-z]?"
    r"|Dieu\s+\d+[a-z]?"
    r"|Điu\s+\d+[a-z]?"
    r"|\d+\.\s+"
    r"|[a-zđ]\)\s+"
    r"|[a-zđ]\d+\)\s+"
    r"|THÔNG\s+TƯ"
    r"|NGHỊ\s+ĐỊNH"
    r"|LUẬT"
    r"|BỘ\s+LUẬT"
    r"|CỘNG\s+HÒA\s+XÃ\s+HỘI"
    r"|Độc\s+lập\s+–\s+Tự\s+do"
    r"|Số:\s*"
    r"|Hà\s+Nội,"
    r"|Nơi\s+nhận:"
    r")",
    re.IGNORECASE,
)

# Regex to detect standalone page numbers (e.g. "2", "- 2 -", "Trang 2")
STANDALONE_PAGE_NUM_REGEX = re.compile(r"^\s*(?:-\s*)?(?:Trang\s+)?\d{1,4}(?:\s*-)?\s*$", re.IGNORECASE)

# Decorative line separator
DIVIDER_REGEX = re.compile(r"^[\s_\-–—=]{3,}\s*$")

# Digital signature stamp block from government portals
DIGITAL_SIGNATURE_REGEX = re.compile(
    r"(?:VGP\s+)?(?:Ký\s+bởi|Người\s+ký|Ky\s+boi|Nguoi\s+ky):\s*(?:Cổng\s+Thông\s+tin\s+điện\s+tử\s+Chính\s+phủ|CỔNG\s+THÔNG\s+TIN\s+ĐIỆN\s+TỬ\s+CHÍNH\s+PHỦ|CONG\s+THONG\s+TIN\s+DIEN\s+TU\s+CHINH\s+PHU)[^\n]*?(?:(?:Thời\s+gian\s+ký|Thoi\s+gian\s+ky):[^\n]*|\n(?=[A-ZĐ]))",
    re.DOTALL | re.IGNORECASE,
)



class TextCleaner:
    """Cleans extracted legal text while preserving critical legal structural markers."""

    def __init__(self, remove_page_numbers: bool = True):
        self.remove_page_numbers = remove_page_numbers

    def clean_text(self, text: str, page_number: Optional[int] = None) -> str:
        """Executes full normalization pipeline on raw string."""
        if not text:
            return ""

        # 1. Unicode NFC Normalization
        text = unicodedata.normalize("NFC", text)

        # 2. Strip digital signature blocks
        text = DIGITAL_SIGNATURE_REGEX.sub("", text)

        # 3. Normalize non-standard whitespaces (NBSP, zero-width space, etc.)
        text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Strip unprintable control characters (keep \n, \t)
        text = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)

        # 4. Process line by line
        lines = text.split("\n")
        cleaned_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue

            # Remove horizontal decorative dividers
            if DIVIDER_REGEX.match(stripped):
                continue

            # Remove Cong Bao running headers
            if CONG_BAO_HEADER_REGEX.match(stripped):
                continue

            # Remove isolated page number lines
            if self.remove_page_numbers:
                if STANDALONE_PAGE_NUM_REGEX.match(stripped):
                    continue

            # Normalize multiple spaces within the line
            normalized_line = re.sub(r"[ \t]+", " ", stripped)
            cleaned_lines.append(normalized_line)

        # 5. Safe unwrap / join lines broken across line wraps
        unwrapped_text = self._safe_unwrap_lines(cleaned_lines)

        # 6. Normalize multiple consecutive blank lines
        unwrapped_text = re.sub(r"\n{3,}", "\n\n", unwrapped_text)

        return unwrapped_text.strip()

    def clean_page(self, page: PageText) -> PageText:
        """Cleans a single PageText object and returns a cleaned PageText."""
        cleaned_str = self.clean_text(page.text, page_number=page.page_number)
        return PageText(
            doc_id=page.doc_id,
            filename=page.filename,
            page_number=page.page_number,
            text=cleaned_str,
        )

    def _safe_unwrap_lines(self, lines: list[str]) -> str:
        """Joins lines broken by PDF width constraints without breaking legal list structure."""
        if not lines:
            return ""

        output_lines: list[str] = []
        i = 0
        n = len(lines)

        while i < n:
            curr = lines[i]
            if not curr:
                output_lines.append("")
                i += 1
                continue

            # Check if this line should merge with following lines
            while i + 1 < n:
                next_line = lines[i + 1]
                if not next_line:
                    break

                # If next line starts with a legal structure marker, DO NOT merge
                if STRUCTURAL_PREFIX_REGEX.match(next_line):
                    break

                # If current line ends with sentence-ending punctuation or colon, DO NOT merge
                if curr.endswith((".", ":", "!", "?", "...", "”", '"', "—", "–")):
                    break

                # If current line is an article heading (starts with Điều \d+\.):
                # Only merge if the title was wrapped across lines (curr ends with , / ; / - or next_line starts with lowercase).
                # If next_line starts with an uppercase letter or clause number, DO NOT merge.
                if re.match(r"^\s*(?:Điều|ĐIỀU|Dieu|DIEU)\s+\d+[a-đ]?\.", curr, re.IGNORECASE):
                    if not (curr.endswith((",", ";", "-")) or (next_line and next_line[0].islower())):
                        break

                # If current line is itself a structural standalone heading (e.g. "CHƯƠNG II"), DO NOT merge
                if STRUCTURAL_HEADING_REGEX.match(curr):
                    break

                # Safe to merge
                if curr.endswith("-"):
                    # Hyphenated word break (e.g. lao- / động -> lao động)
                    curr = curr[:-1] + next_line
                else:
                    curr = curr + " " + next_line
                i += 1

            output_lines.append(curr)
            i += 1

        return "\n".join(output_lines)
