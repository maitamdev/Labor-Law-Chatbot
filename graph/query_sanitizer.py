"""
Cypher Query Sanitizer to guard against injection and ensure read-only execution.
"""
import re

FORBIDDEN_CYPHER_KEYWORDS = [
    r"\bCREATE\b",
    r"\bDELETE\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bMERGE\b",
    r"\bDROP\b",
    r"\bDETACH\b",
    r"\bCALL\s+apoc\b",
]

def sanitize_cypher_param(value: str) -> str:
    """Strip dangerous characters from query string parameters."""
    if not isinstance(value, str):
        return str(value)
    # Remove control characters, quotes and semicolons
    chars_to_remove = set("'\\\";")
    cleaned = "".join(c for c in value if c not in chars_to_remove and ord(c) >= 32)
    return cleaned.strip()

def validate_readonly_cypher(query: str) -> bool:
    """Ensure the Cypher query contains no mutating operations."""
    query_upper = query.upper()
    for kw in FORBIDDEN_CYPHER_KEYWORDS:
        if re.search(kw, query_upper):
            return False
    return True
