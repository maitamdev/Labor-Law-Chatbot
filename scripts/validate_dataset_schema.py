"""
Validator for SFT ChatML and Alpaca JSON/JSONL datasets.
"""
import json
import sys
from pathlib import Path


def validate_chatml_file(file_path: Path) -> dict:
    """Validate a ChatML JSONL file."""
    valid_count = 0
    errors = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception as e:
                errors.append(f"Line {line_num}: Invalid JSON ({e})")
                continue
            if "messages" not in data or not isinstance(data["messages"], list):
                errors.append(f"Line {line_num}: Missing 'messages' list")
                continue
            roles = [m.get("role") for m in data["messages"]]
            if "user" not in roles or "assistant" not in roles:
                errors.append(f"Line {line_num}: Must contain 'user' and 'assistant' roles")
                continue
            valid_count += 1
    return {"valid_records": valid_count, "errors": errors}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        res = validate_chatml_file(p)
        print(f"Validated {p}: {res['valid_records']} valid, {len(res['errors'])} errors")
