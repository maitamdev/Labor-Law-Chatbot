# -*- coding: utf-8 -*-
"""
VietLabor AI - OutputValidator Unit Tests
Tests:
1. Robust JSON parsing with duplicate root-level keys (e.g., repeated "issue" and "findings").
2. Automated Markdown synthesis from legal findings when "answer" is missing or raw JSON.
3. Ensuring no raw JSON string ever leaks into the final user-facing answer.
4. Standard LegalAnswer parsing without regressions.
"""
from __future__ import annotations

import pytest

from rag.output_validator import OutputValidator, LegalAnswer, LegalFinding


def test_parse_llm_json_duplicate_keys_and_missing_answer():
    validator = OutputValidator()

    # Exact structure reported by the user:
    raw_llm_text = """{
"issue": "Việc anh Dũng từ chối làm việc khi nhận thấy có nguy cơ đe dọa trực tiếp đến tính mạng và sức khỏe của bản thân có phù hợp theo quy định pháp luật lao động",
"findings": [
{ "issue": "Việc anh Dũng từ chối làm việc khi nhận thấy có nguy cơ đe dọa trực tiếp đến tính mạng và sức khỏe của bản thân", "conclusion": "Việc anh Lò Văn Dũng từ chối làm việc khi nhận thấy có nguy cơ đe dọa trực tiếp đến tính mạng và sức khỏe của bản thân là phù hợp theo quy định pháp luật lao động. Theo Điểm d Khoản 1 Điều 5 Bộ luật Lao động 2019, người lao động có quyền từ chối làm việc nếu có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe trong quá trình thực hiện công việc. Trong tình huống này, anh Dũng đã nhận thấy nguy cơ sạt lở có thể đe dọa trực tiếp đến tính mạng và sức khỏe của mình, do đó anh có quyền từ chối tiếp tục làm việc.", "evidence_ids": ["E1"] }
],
"issue": "Pháp luật lao động quy định như thế nào về quyền của người lao động",
"findings": [
{ "issue": "Pháp luật lao động quy định như thế nào về quyền của người lao động", "conclusion": "Pháp luật lao động quy định rằng người lao động có các quyền, trong đó có quyền từ chối làm việc nếu có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe trong quá trình thực hiện công việc. Theo Điểm d Khoản 1 Điều 5 Bộ luật Lao động 2019, người lao động có quyền từ chối làm việc khi có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe. Ngoài ra, người lao động còn có quyền được hưởng các quyền khác theo quy định của pháp luật, như được bảo vệ an toàn và sức khỏe trong lao động, được hưởng các quyền khác theo quy định của pháp luật lao động. Theo Điểm g Khoản 1 Điều 5 Bộ luật Lao động 2019, người lao động có các quyền khác theo quy định của pháp luật.", "evidence_ids": ["E1", "E2"] }
],
"issue": "Việc công ty xử lý kỷ luật và cắt thưởng anh Dũng trong trường hợp này có đúng quy định pháp luật không",
"findings": [
{ "issue": "Việc công ty xử lý kỷ luật và cắt thưởng anh Dũng trong trường hợp này", "conclusion": "Việc công ty xử lý kỷ luật và cắt thưởng anh Lò Văn Dũng trong trường hợp này là không đúng quy định pháp luật. Theo Điểm d Khoản 1 Điều 5 Bộ luật Lao động 2019, người lao động có quyền từ chối làm việc khi nhận thấy có nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng, sức khỏe. Do đó, việc anh Dũng từ chối làm việc là phù hợp và không vi phạm quy định pháp luật. Việc công ty xử lý kỷ luật và cắt thưởng anh Dũng vì anh đã từ chối làm việc là không phù hợp và trái với quy định pháp luật.", "evidence_ids": ["E1"] }
],
"needs_clarification": false, "clarification_question": null, "out_of_scope": false
}"""

    parsed: LegalAnswer = validator.parse_llm_json(raw_llm_text)

    # 1. All 3 findings must be preserved, none dropped by duplicate keys
    assert len(parsed.findings) == 3, f"Expected 3 findings, got {len(parsed.findings)}"
    assert "E1" in parsed.findings[0].evidence_ids
    assert "E2" in parsed.findings[1].evidence_ids
    assert "E1" in parsed.findings[2].evidence_ids

    # 2. Answer must NOT be raw JSON
    assert not parsed.answer.strip().startswith("{"), "Answer should not be a raw JSON string"
    assert not parsed.answer.strip().endswith("}"), "Answer should not be a raw JSON string"

    # 3. Answer must contain synthesized Markdown headings for each issue
    assert "###" in parsed.answer
    assert "từ chối làm việc" in parsed.answer
    assert "quyền của người lao động" in parsed.answer
    assert "xử lý kỷ luật" in parsed.answer

    # 4. Evidence tokens must be collected
    assert "E1" in parsed.evidence_ids
    assert "E2" in parsed.evidence_ids


def test_parse_llm_json_raw_json_inside_answer_field():
    validator = OutputValidator()

    # LLM accidentally puts JSON inside answer string
    nested_json_answer = """{
"answer": "{\\"issue\\": \\"Thử việc\\", \\"findings\\": [{\\"issue\\": \\"Lương thử việc\\", \\"conclusion\\": \\"Phải trả ít nhất 85% lương.\\", \\"evidence_ids\\": [\\"E1\\"]}]}",
"findings": [
    {"issue": "Lương thử việc", "conclusion": "Phải trả ít nhất 85% lương theo Điều 26.", "evidence_ids": ["E1"]}
]
}"""

    parsed = validator.parse_llm_json(nested_json_answer)
    assert not parsed.answer.startswith("{"), "Raw JSON inside answer should be converted to clean markdown"
    assert "Phải trả ít nhất 85% lương" in parsed.answer


def test_parse_llm_json_standard_happy_path():
    validator = OutputValidator()

    valid_json = """{
"answer": "Người lao động có quyền từ chối làm việc khi có nguy cơ đe dọa tính mạng theo quy định tại [E1].",
"findings": [
    {"issue": "Quyền từ chối", "conclusion": "Hợp pháp theo [E1].", "evidence_ids": ["E1"]}
],
"needs_clarification": false,
"clarification_question": null,
"out_of_scope": false
}"""

    parsed = validator.parse_llm_json(valid_json)
    assert len(parsed.findings) == 1
    assert parsed.answer == "Người lao động có quyền từ chối làm việc khi có nguy cơ đe dọa tính mạng theo quy định tại [E1]."
    assert parsed.evidence_ids == ["E1"]
    assert not parsed.needs_clarification


def test_synthesize_answer_from_findings():
    findings = [
        LegalFinding(issue="Vấn đề 1: Lương thử việc", finding="Công ty trả 70% là vi phạm."),
        LegalFinding(issue="Vấn đề 2: Kéo dài thử việc", finding="Kéo dài thêm 15 ngày là trái luật."),
    ]
    synth = OutputValidator.synthesize_answer_from_findings(findings)
    assert "### Vấn đề 1: Lương thử việc" in synth
    assert "Công ty trả 70% là vi phạm." in synth
    assert "### Vấn đề 2: Kéo dài thử việc" in synth
    assert "Kéo dài thêm 15 ngày là trái luật." in synth


def test_parse_llm_json_unescaped_quotes_and_repair():
    validator = OutputValidator()

    # Raw LLM text containing unescaped straight quotes inside statutory citation
    raw_with_unescaped_quotes = """{
  "answer": "### Vấn đề 1: Đào tạo nghề\\nTheo quy định người sử dụng lao động có nghĩa vụ: "Đào tạo, đào tạo lại, bồi dưỡng nâng cao trình độ" theo [E1].\\n\\n### Vấn đề 2: Hoàn trả chi phí\\nTheo Điều 62 ([E2]), người lao động phải hoàn trả chi phí đào tạo.",
  "findings": [
    {"issue": "Vấn đề 1", "conclusion": "Nghĩa vụ theo Điều 6", "evidence_ids": ["E1"]},
    {"issue": "Vấn đề 2", "conclusion": "Hoàn trả chi phí theo Điều 62", "evidence_ids": ["E2"]}
  ],
  "needs_clarification": false,
  "clarification_question": null,
  "out_of_scope": false
}"""

    parsed = validator.parse_llm_json(raw_with_unescaped_quotes)
    assert not parsed.abstain
    assert "Đào tạo, đào tạo lại, bồi dưỡng" in parsed.answer
    assert "Hoàn trả chi phí" in parsed.answer
    assert len(parsed.findings) == 2
    assert "E1" in parsed.evidence_ids
    assert "E2" in parsed.evidence_ids


def test_parse_llm_json_truncated_output():
    validator = OutputValidator()

    # Generation cut off mid-sentence by token limit
    truncated_llm_text = """{
  "answer": "### Vấn đề 1: Đào tạo nghề theo quy định pháp luật\\n\\nTheo [E1] (Căn cứ Điểm c Khoản 2 Điều 6 Bộ luật Lao động 2019), công ty có trách nhiệm bồi dưỡng tay nghề cho lao động. Còn đối với chị Luyến, theo Điều 62"""

    parsed = validator.parse_llm_json(truncated_llm_text)
    assert not parsed.abstain
    assert "Điểm c Khoản 2 Điều 6" in parsed.answer
    assert "E1" in parsed.evidence_ids
