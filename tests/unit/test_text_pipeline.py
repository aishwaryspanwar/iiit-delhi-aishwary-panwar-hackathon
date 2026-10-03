from datetime import datetime, timezone

import pytest

from src.riskengine.dedup import clean_and_dedup
from src.riskengine.models import RawDoc
from src.riskengine.normalize import clean_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Stocks fall @trader_joe https://t.co/abc", "Stocks fall @user"),
        ("<script>alert(1)</script> $META looks cheap", "alert(1) $META looks cheap"),
        ("Oil &amp; gas   rally", "Oil & gas rally"),
        ("Russia invades Ukraine - Reuters", "Russia invades Ukraine"),
        ("Russia invades Ukraine | BBC News", "Russia invades Ukraine"),
        ("Fed raises rates to 5% - analysts", "Fed raises rates to 5% - analysts"),
        ("Bad �char", "Bad char"),
    ],
)
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected


def doc(source_id: str, text: str, outlet: str | None, minute: int) -> RawDoc:
    return RawDoc("stub_news", source_id, datetime(2022, 2, 24, 3, minute, tzinfo=timezone.utc), text, None, outlet)


def test_dedup_merges_syndicated_titles_and_keeps_breadth():
    docs = [
        doc("a", "Russia invades Ukraine - Reuters", "reuters.com", 1),
        doc("b", "Russia invades Ukraine | BBC News", "bbc.com", 2),
        doc("c", "Oil jumps on invasion", "ft.com", 3),
    ]
    unique = clean_and_dedup(docs)
    assert len(unique) == 2
    merged = next(d for d in unique if d.source_id == "a")
    assert merged.duplicate_count == 2
    assert merged.outlets == {"reuters.com", "bbc.com"}


def test_dedup_drops_empty_text():
    assert clean_and_dedup([doc("a", "https://t.co/x", None, 1)]) == []
