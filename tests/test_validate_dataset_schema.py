import tempfile
from pathlib import Path

from scripts.validate_dataset_schema import validate_chatml_file


def test_validate_chatml_file():
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp.write('{"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}\n')
        tmp_path = Path(tmp.name)
    try:
        res = validate_chatml_file(tmp_path)
        assert res["valid_records"] == 1
        assert len(res["errors"]) == 0
    finally:
        tmp_path.unlink()
