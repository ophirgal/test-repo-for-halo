"""Render a ``SiteResult`` as deterministic JSON or Markdown text."""

import json
import re
from itertools import groupby

from linkcheck.check import SiteResult

_MD_SPECIAL = re.compile(r"([\\`|*_\[\]<>])")


def finding_line(finding) -> str:
    """The terminal form of one finding: ``path:line: kind: target``."""
    return f"{finding.path}:{finding.line}: {finding.kind}: {finding.target}"


def to_json(result: SiteResult) -> str:
    doc = {
        "pages": result.pages,
        "links": result.links,
        "ignored": result.ignored,
        "external": [
            {"path": e.path, "line": e.line, "target": e.target} for e in sorted(result.external)
        ],
        "findings": [
            {"path": f.path, "line": f.line, "kind": f.kind, "target": f.target}
            for f in sorted(result.findings)
        ],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _md(text: str) -> str:
    """Escape text for a Markdown table cell or heading."""
    return _MD_SPECIAL.sub(r"\\\1", text).replace("\r", " ").replace("\n", " ")


def to_markdown(result: SiteResult) -> str:
    findings = sorted(result.findings)
    out = [
        "# Link check report",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Pages | {result.pages} |",
        f"| Links | {result.links} |",
        f"| External | {len(result.external)} |",
        f"| Ignored | {result.ignored} |",
        f"| Findings | {len(findings)} |",
        "",
    ]
    if not findings:
        out += ["No findings.", ""]
    for path, group in groupby(findings, key=lambda f: f.path):
        out += [f"## {_md(path)}", "", "| Line | Kind | Target |", "| ---: | --- | --- |"]
        out += [f"| {f.line} | {f.kind} | {_md(f.target)} |" for f in group]
        out.append("")
    return "\n".join(out)
