import io
import zipfile

from src.riskengine.ingest.gdelt import filter_gkg_rows, parse_gkg_date


def gkg_row(record_id: str, outlet: str, themes: str, title: str) -> str:
    columns = [""] * 27
    columns[0] = record_id
    columns[1] = "20220224030000"
    columns[3] = outlet
    columns[4] = f"https://{outlet}/story"
    columns[7] = themes
    columns[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
    return "\t".join(columns)


def zipped(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("x.gkg.csv", "\n".join(lines))
    return buffer.getvalue()


def test_filter_keeps_allowlisted_finance_titles_only():
    payload = zipped([
        gkg_row("1", "reuters.com", "ECON_STOCKMARKET;", "Russia invades Ukraine as global stocks slump"),
        gkg_row("2", "randomblog.net", "ECON_STOCKMARKET;", "Russia invades Ukraine as global stocks slump"),
        gkg_row("3", "reuters.com", "SPORTS;", "Local team wins the championship final tonight"),
        gkg_row("4", "reuters.com", "ECON_INFLATION;", "Too short"),
        gkg_row("5", "reuters.com", "ECON_INFLATION;", ""),
    ])
    rows = filter_gkg_rows(payload)
    assert [r["source_id"] for r in rows] == ["1"]
    assert rows[0]["published_at"] == "2022-02-24T03:00:00Z"
    assert rows[0]["outlet"] == "reuters.com"


def test_parse_gkg_date():
    assert parse_gkg_date("20220316180000") == "2022-03-16T18:00:00Z"
