"""Command line: ``python -m linkcheck <dir> [--json FILE] [--markdown FILE] [--ignore PATTERN ...]``.

Exit codes: 0 no findings, 1 findings, 2 usage error or I/O error (an
unreadable page or a report that cannot be written). On exit 2 no report is
left behind.
"""

import argparse
import os
import sys
import tempfile

from linkcheck.check import LinkcheckIOError, check_site
from linkcheck.report import finding_line, to_json, to_markdown

EXIT_OK, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m linkcheck",
        description="Check every HTML page under DIR for broken internal links "
        "and missing anchors, offline. External links are listed, never fetched.",
    )
    parser.add_argument("dir", help="directory holding the site's .html pages")
    parser.add_argument("--json", metavar="FILE", help="write a JSON report to FILE")
    parser.add_argument("--markdown", metavar="FILE", help="write a Markdown report to FILE")
    parser.add_argument(
        "--ignore",
        metavar="PATTERN",
        action="append",
        default=[],
        help="skip links whose target matches this fnmatch pattern (repeatable)",
    )
    return parser


def _write_all(reports) -> None:
    """Write every (path, text) report, or none: temp files, then os.replace."""
    staged = []
    try:
        for path, text in reports:
            try:
                fd, tmp = tempfile.mkstemp(
                    dir=os.path.dirname(os.path.abspath(path)), prefix=".linkcheck-"
                )
            except OSError as exc:
                raise OSError(exc.errno, exc.strerror, path) from exc
            staged.append((tmp, path))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        for tmp, path in staged:
            try:
                os.replace(tmp, path)
            except OSError as exc:
                raise OSError(exc.errno, exc.strerror, path) from exc
    finally:
        for tmp, _ in staged:
            if os.path.exists(tmp):
                os.unlink(tmp)


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not os.path.exists(args.dir):
        parser.error(f"{args.dir}: no such directory")
    if not os.path.isdir(args.dir):
        parser.error(f"{args.dir}: not a directory")

    try:
        result = check_site(args.dir, ignore=args.ignore)
    except LinkcheckIOError as exc:
        print(f"linkcheck: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    reports = []
    if args.json:
        reports.append((args.json, to_json(result)))
    if args.markdown:
        reports.append((args.markdown, to_markdown(result)))
    try:
        _write_all(reports)
    except OSError as exc:
        print(
            f"linkcheck: error: cannot write report {exc.filename}: {exc.strerror}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    for finding in sorted(result.findings):
        print(finding_line(finding))
    return EXIT_FINDINGS if result.findings else EXIT_OK
