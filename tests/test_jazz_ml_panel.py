from pathlib import Path

from api import routes


def test_jazz_ml_markdown_table_parser_extracts_aggregate_rows():
    md = """
# Report

| version | pitches scored | chord-tone hit |
|---|---:|---:|
| v6.3.0 | 2688 | 0.537 |
| v6.3.1 | 2688 | 0.530 |

## Next table
| ignored | value |
|---|---|
| x | y |
"""
    rows = routes._jazz_ml_parse_eval_table(md)
    assert rows == [
        {"version": "v6.3.0", "pitches scored": "2688", "chord-tone hit": "0.537"},
        {"version": "v6.3.1", "pitches scored": "2688", "chord-tone hit": "0.530"},
    ]


def test_jazz_ml_helpers_tolerate_missing_project_artifacts(tmp_path: Path):
    checkpoints = routes._jazz_ml_checkpoint_info(tmp_path)
    solos = routes._jazz_ml_solo_dirs(tmp_path)

    assert checkpoints
    assert all(item["exists"] is False for item in checkpoints)
    assert solos == []


def test_jazz_ml_frontend_hook_is_present():
    html = Path("static/index.html").read_text(encoding="utf-8")
    panels = Path("static/panels.js").read_text(encoding="utf-8")

    assert 'data-panel="jazzml"' in html
    assert 'id="jazzmlContent"' in html
    assert "async function loadJazzMl" in panels
    assert "api('/api/jazz-ml')" in panels
