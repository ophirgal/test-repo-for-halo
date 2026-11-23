"""Command line: ``python -m ledger report FILE --month YYYY-MM ...``.

Exit codes: 0 success, 2 usage error or unreadable FILE, 3 bad ledger row.
"""

import argparse
import json
import sys

from .model import LedgerError
from .parse import parse_csv
from .report import RATES, check_month, monthly_report

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DATA = 3


def _month(text):
    try:
        return check_month(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid month {text!r}: expected YYYY-MM") from None


def _top(text):
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"invalid top {text!r}: expected an integer of at least 1")
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m ledger", description="Reports on a CSV ledger."
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    commands.required = True
    report = commands.add_parser(
        "report",
        help="total one month by category",
        description="Total one month of a CSV ledger by category in a base currency.",
    )
    report.add_argument("file", metavar="FILE", help="ledger CSV file (UTF-8)")
    report.add_argument("--month", required=True, type=_month, metavar="YYYY-MM",
                        help="month to report, e.g. 2026-03")
    report.add_argument("--base", choices=sorted(RATES), default="ILS",
                        help="base currency for all figures (default: ILS)")
    report.add_argument("--top", type=_top, default=None, metavar="N",
                        help="list only the N largest categories")
    report.add_argument("--json", action="store_true",
                        help="print the report as one JSON object")
    return parser


def render_text(report):
    lines = [
        f"month: {report.month}",
        f"base: {report.base}",
        f"transactions: {report.count}",
        f"income: {report.income}",
        f"expense: {report.expense}",
        f"net: {report.net}",
    ]
    if report.categories:
        lines.append("categories:")
        lines.extend(f"  {c.name}: {c.total} ({c.count})" for c in report.categories)
    else:
        lines.append("categories: none")
    return "\n".join(lines) + "\n"


def render_json(report):
    return json.dumps(report.to_dict()) + "\n"


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        transactions = parse_csv(args.file)
    except LedgerError as e:
        sys.stderr.write(f"error: {args.file}:{e.line}: {e.reason}\n")
        return EXIT_DATA
    except UnicodeDecodeError as e:
        sys.stderr.write(f"error: cannot read {args.file}: not valid UTF-8 ({e.reason})\n")
        return EXIT_USAGE
    except OSError as e:
        sys.stderr.write(f"error: cannot read {args.file}: {e.strerror or e}\n")
        return EXIT_USAGE
    report = monthly_report(transactions, args.month, base=args.base, top=args.top)
    output = render_json(report) if args.json else render_text(report)
    sys.stdout.write(output)
    return EXIT_OK
