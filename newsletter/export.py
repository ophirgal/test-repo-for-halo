"""CSV export of every stored signup: ``python3 -m newsletter export [-o FILE]``.

Run on the machine that hosts the site; no HTTP route ever returns signups.
The CSV is UTF-8 with no BOM, ``csv`` default quoting and ``\\r\\n`` line
endings: the header ``name,email,signed_up_at``, then one row per signup,
oldest first, with its time in ISO 8601 UTC (``Z``).
"""

import argparse
import csv
import io
import os
import sys
import tempfile

from .store import TIME_FORMAT, read_records

DEFAULT_PATH = "./newsletter.jsonl"
HEADER = ("name", "email", "signed_up_at")
# A cell starting with one of these is read as a formula by spreadsheets.
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def guard(cell):
    """Prefix ``'`` to a cell a spreadsheet would run as a formula."""
    return "'" + cell if cell.startswith(FORMULA_STARTS) else cell


def store_path():
    """The signup file: ``NEWSLETTER_PATH``, else ``./newsletter.jsonl``."""
    return os.environ.get("NEWSLETTER_PATH") or DEFAULT_PATH


def write_csv(records, out):
    """Write the header and one guarded row per record to text stream ``out``."""
    writer = csv.writer(out)
    writer.writerow(HEADER)
    for record in records:
        writer.writerow((guard(record.name), guard(record.email), record.time.strftime(TIME_FORMAT)))


def export(path, output=None):
    """Export ``path`` to ``output`` (a file path) or stdout.

    Raises ``OSError`` when the store cannot be read or ``output`` written;
    ``output`` is then left untouched (written to a temporary file first).
    """
    records = list(read_records(path))  # read errors surface before any write
    if output is None:
        out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="", write_through=True)
        try:
            write_csv(records, out)
            out.flush()
        finally:
            out.detach()
        return
    directory = os.path.dirname(os.path.abspath(output))
    fd, tmp = tempfile.mkstemp(prefix=".newsletter-export-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            write_csv(records, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, output)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m newsletter", description="Newsletter signups.")
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True
    cmd = commands.add_parser("export", help="write every signup as CSV (stdout, or -o FILE)")
    cmd.add_argument("-o", "--output", metavar="FILE", help="write the CSV to FILE instead of stdout")
    args = parser.parse_args(argv)
    path = store_path()
    try:
        export(path, args.output)
    except OSError as err:
        print(f"newsletter export: {err}", file=sys.stderr, flush=True)
        return 1
    return 0
