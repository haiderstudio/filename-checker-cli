#!/usr/bin/env python3
"""Check filenames follow lowercase kebab-case, fail CI on a bad name.

Run: python3 src/filename_checker.py examples/clean-files/
     python3 src/filename_checker.py src/ docs/
     python3 src/filename_checker.py examples/bad-files/ --allow UPPERCASE.md

The rule is one simple naming rule, applied to every file named:

    lowercase kebab-case — the name is split into dot-separated
    parts, and every part is lowercase letters a-z, digits, and
    hyphens only, with no spaces, no uppercase, no underscores, no
    leading or trailing hyphen, and no double hyphen. The last part
    is the extension. A file with no dot is checked as one part, and
    a hidden file (a name starting with a dot, like `.gitignore`) is
    checked without its leading dot.

So `user-guide.md` and `archive.tar.gz` pass and `My File.txt`,
`my_file.txt`, `UPPERCASE.md`, `double--hyphen.txt`, and `photo.JPG`
all fail. Dots only separate parts — `my..file.txt` fails because
one part is empty, and `file.` fails because the extension is empty.

Every problem is reported with its file path and a plain reason,
and the tool exits 1 when any problem is found — so it can fail a
CI run — and 0 when every file is clean.

It never renames a file. It is report-only and runs fully offline:
it sends nothing anywhere and needs no API key.

Exit codes: 0 when no problem is found, 1 when any problem is
found, 2 for a usage or input problem (a missing file or folder,
a bad flag, no file to check).

Python standard library only.
"""

import argparse
import contextlib
import fnmatch
import json
import sys
from pathlib import Path

VERSION = "1.0.0"


def _add(reasons, reason):
    """Append a reason once, in first-seen order."""
    if reason not in reasons:
        reasons.append(reason)


def check_name(name):
    """Return the list of reasons a filename breaks the rule, or [].

    The name is split into dot-separated parts. Every part but the
    last is a name segment; the last part is the extension when the
    name holds a dot at all. A leading dot (a hidden file) is set
    aside first and is not itself a problem. Each reason names the
    fault in plain words, once even if two parts share it.
    """
    reasons = []
    rest = name[1:] if name.startswith(".") else name
    parts = rest.split(".")
    if len(parts) == 1:
        segments, ext = parts, None
    else:
        segments, ext = parts[:-1], parts[-1]

    for segment in segments:
        if segment == "":
            _add(reasons, "empty name")
            continue
        if any(c.isupper() for c in segment):
            _add(reasons, "uppercase letter")
        if " " in segment:
            _add(reasons, "space in name")
        if "_" in segment:
            _add(reasons, "underscore in name")
        if segment.startswith("-"):
            _add(reasons, "starts with a hyphen")
        if segment.endswith("-"):
            _add(reasons, "ends with a hyphen")
        if "--" in segment:
            _add(reasons, "double hyphen")
        for c in segment:
            if c == "-" or (c.isascii() and c.isalnum()):
                continue
            if c in " _" or c.isupper():
                continue  # already reported above
            _add(reasons, f"bad character '{c}'")
            break

    if ext is not None:
        if ext == "":
            _add(reasons, "empty extension")
        elif ext != ext.lower():
            _add(reasons, "uppercase extension")
        elif " " in ext:
            _add(reasons, "space in extension")
        elif "_" in ext:
            _add(reasons, "underscore in extension")
        else:
            for c in ext:
                if not (c.isascii() and c.isalnum()):
                    _add(reasons, f"bad character '{c}' in extension")
                    break
    return reasons


def collect_files(paths, recursive=True, excludes=(), allowed=()):
    """Turn file and folder arguments into a sorted list of files.

    Folders are walked (recursively unless --no-recursive), `.git`
    folders are never walked, and directory links are never followed,
    so a link cycle cannot loop the check. Files matching an
    --exclude glob (checked against the name and the path) are left
    out, as are files named in --allow.
    """
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            if not _skipped(path, excludes, allowed):
                found.append(path)
        elif path.is_dir():
            if recursive:
                for root, dirs, files in path.walk():
                    dirs[:] = sorted(d for d in dirs if d != ".git")
                    for name in sorted(files):
                        candidate = root / name
                        if not _skipped(candidate, excludes, allowed):
                            found.append(candidate)
            else:
                for child in sorted(path.iterdir()):
                    if child.is_file() and not _skipped(
                        child, excludes, allowed
                    ):
                        found.append(child)
        else:
            raise FileNotFoundError(raw)
    return found


def _skipped(path, excludes, allowed):
    if path.name in allowed:
        return True
    name = path.name
    text = str(path)
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(text, pattern)
        for pattern in excludes
    )


def check_files(files):
    """Check each file's name. Returns a dict of file -> reasons."""
    return {path: check_name(path.name) for path in files}


def summarize(results):
    """Build the summary numbers from per-file results."""
    checked = len(results)
    bad_files = sum(1 for reasons in results.values() if reasons)
    problems = sum(len(reasons) for reasons in results.values())
    return {
        "checked": checked,
        "files_with_problems": bad_files,
        "problems": problems,
    }


def format_problems(results):
    """Format the per-problem FAIL lines, in file order."""
    lines = []
    for path in sorted(results, key=str):
        for reason in results[path]:
            lines.append(f"FAIL {path}: {reason}")
    return lines


def run(argv=None, stdout=None, stderr=None):
    """Run the CLI. Returns the exit code."""
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr

    parser = argparse.ArgumentParser(
        prog="filename_checker",
        description=(
            "Check filenames follow lowercase kebab-case, "
            "fail CI on a bad name."
        ),
    )
    parser.add_argument(
        "paths", nargs="*", help="files or folders to check (default: .)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not walk into subfolders of a named folder",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip files matching this glob (repeatable)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="NAME",
        help="skip files with this exact name, e.g. Makefile (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON on stdout",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    # argparse exits (SystemExit) on --version and on bad flags. Catch
    # it so the message lands in the caller's streams and run() returns
    # the code instead of raising.
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
            stderr
        ):
            args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    paths = args.paths if args.paths else ["."]
    try:
        files = collect_files(
            paths,
            recursive=not args.no_recursive,
            excludes=args.exclude,
            allowed=args.allow,
        )
    except FileNotFoundError as exc:
        print(f"error: no such file or folder: {exc}", file=stderr)
        return 2
    if not files:
        print("error: no files to check", file=stderr)
        return 2
    results = check_files(files)
    summary = summarize(results)

    if args.json:
        payload = {
            "files": [
                {
                    "file": str(path),
                    "reasons": results[path],
                }
                for path in sorted(results, key=str)
                if results[path]
            ],
            "summary": summary,
        }
        print(json.dumps(payload, indent=2), file=stdout)
    else:
        for line in format_problems(results):
            print(line, file=stdout)

    if summary["problems"] == 0:
        line = (
            f"OK — {summary['checked']} file(s) checked, "
            "all names follow lowercase kebab-case."
        )
        print(line, file=stderr if args.json else stdout)
        return 0

    line = (
        f"Checked {summary['checked']} file(s), "
        f"{summary['problems']} problem(s) in "
        f"{summary['files_with_problems']} file(s)."
    )
    print(line, file=stderr if args.json else stdout)
    return 1


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
