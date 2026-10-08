"""Targeted, source-verified citation repairs for the QA bank."""

OFFICIAL_BLL_URL = "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm"
OFFICIAL_BHXH_URL = "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm"

_BLL_ROWS = frozenset({
    652, 653, 654, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666,
    667, 669, 670, 671, 672, 675, 676, 680, 681, 684, 689, 690, 692, 693,
})


def normalize_source(sheet_row: int, source: str) -> str:
    """Attach the exact instrument numbers and current official Gazette links."""
    if sheet_row == 422:
        return (
            "Điểm đ khoản 1 Điều 31 — Luật Bảo hiểm xã hội số 41/2024/QH15 "
            "(Văn bản hợp nhất số 19/VBHN-VPQH)\n"
            f"{OFFICIAL_BHXH_URL}"
        )

    if sheet_row not in _BLL_ROWS:
        return source

    citation = "Bộ luật Lao động số 45/2019/QH14 (Văn bản hợp nhất số 18/VBHN-VPQH)"
    updated = source.replace("Bộ luật Lao động 2019", citation)
    updated = updated.replace(
        "https://vanban.chinhphu.vn/?classid=2629&docid=217002&pageid=27160",
        OFFICIAL_BLL_URL,
    )
    if citation not in updated or OFFICIAL_BLL_URL not in updated:
        raise ValueError(f"Unexpected source text for Sheet row {sheet_row}: {source!r}")
    return updated
