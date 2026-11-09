"""Build-time tables from document-reported M1 aggregates, without API calls."""
from decimal import Decimal
from html import escape
import json
from pathlib import Path


def load_results():
    path = Path(__file__).parent / "data" / "reported_results.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    arxiv = data["arxiv"]["ranges"]
    s2 = data["semantic_scholar"]["ranges"]
    if [r["range"] for r in arxiv] != [1, 2, 3, 4, 5]:
        raise ValueError("Expected five ordered arXiv ranges")
    if [r["range"] for r in s2] != [1, 2, 3, 4, 5]:
        raise ValueError("Expected five ordered Semantic Scholar ranges")
    for row in arxiv:
        if sum(row[k] for k in ("ok", "error", "no_tex", "not_found")) != row["assigned"]:
            raise ValueError("arXiv status counts do not cover assigned IDs")
        if row["metadata"] > row["assigned"]:
            raise ValueError("Metadata count exceeds assigned IDs")
    for row in s2:
        if sum(row[k] for k in ("ok", "not_indexed", "failed", "invalid_id")) != row["input_papers"]:
            raise ValueError("Semantic Scholar status counts do not cover inputs")
        if not 0 <= row["cache_hits"] <= row["ok"]:
            raise ValueError("Cache counts are inconsistent")
        if not 0 <= row["refs_with_arxiv"] <= row["refs_total"]:
            raise ValueError("Reference counts are inconsistent")
    return data


def total(rows, key):
    return sum(row[key] for row in rows)


def integer(value):
    return f"{value:,}"


def percent(numerator, denominator, places=2):
    if not denominator:
        return "Not available"
    value = Decimal(str(numerator)) * 100 / Decimal(str(denominator))
    return f"{value:.{places}f}%"


def seconds(value):
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def hms(value):
    return f"{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}"


def table(headers, rows):
    """Generate an accessible HTML table as a build-time notebook output."""
    from IPython.display import HTML, display

    th = 'style="padding:0.6em;border:1px solid #94a3b8;text-align:left"'
    td = 'style="padding:0.6em;border:1px solid #94a3b8;text-align:left;vertical-align:top"'
    output = ['<div style="overflow-x:auto;margin:1em 0"><table style="border-collapse:collapse;font:inherit">',
              '<thead><tr>' + ''.join(f'<th scope="col" {th}>{escape(str(h))}</th>' for h in headers) + '</tr></thead><tbody>']
    for row in rows:
        if len(row) != len(headers):
            raise ValueError("Table row has an unexpected number of columns")
        output.append('<tr>' + ''.join(f'<td {td}>{escape(str(value))}</td>' for value in row) + '</tr>')
    output.append('</tbody></table></div>')
    display(HTML(''.join(output)))
