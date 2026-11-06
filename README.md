# filename-checker-cli

Check filenames follow lowercase kebab-case, fail CI on a bad name.

[![CI](https://github.com/haiderstudio/filename-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/filename-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`filename_checker` reads the files or folders you name and
checks every filename against one naming rule:

- lowercase kebab-case — the name is split into dot-separated
  parts, and every part is lowercase letters a-z, digits, and
  hyphens only: no spaces, no uppercase, no underscores, no
  leading or trailing hyphen, no double hyphen

So `user-guide.md` and `archive.tar.gz` pass, and `My File.txt`
(space and uppercase), `my_file.txt` (underscore), `UPPERCASE.md`
(uppercase), `double--hyphen.txt` (double hyphen), `-leading.txt`
(leading hyphen), `trailing-.txt` (trailing hyphen), `photo.JPG`
(uppercase extension), and `weird@name.txt` (bad character) all
fail. Each problem is reported with its file path and a plain
reason, and the tool exits 1 when any problem is found — so it
can fail a CI run. A clean tree exits 0.

- Dots only separate parts: `archive.tar.gz` passes because
  every part (`archive`, `tar`, `gz`) is a clean kebab segment.
  A name with an empty part fails — `my..file.txt` has an empty
  part, and `file.` has an empty extension.
- A file with no dot is checked as one part (`no-extension`
  passes, `Makefile` fails on the uppercase letters — use
  `--allow Makefile` for names your project keeps on purpose).
- A hidden file (a name starting with a dot, like `.gitignore`)
  is checked without its leading dot, so `.gitignore` passes
  and `.My File` fails.
- One name can carry more than one reason: `My File.txt` is
  reported once for the uppercase letter and once for the space,
  so the fix is clear. A reason shared by two parts of one name
  is reported once.
- Folders are walked recursively by default (`--no-recursive`
  stops at the top level). `.git` folders are never walked, and
  directory links are never followed, so a link cycle cannot loop
  the check.
- `--exclude PATTERN` skips files by glob, for example
  `--exclude '*.min.js'`. It can be repeated.
- `--allow NAME` skips files with that exact name, for example
  `--allow Makefile --allow LICENSE`. It can be repeated.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON).
- It is report-only and runs fully offline: it never renames a
  file, sends nothing anywhere, and needs no API key.

## What it does NOT do

- It does not rename files. A bad name is reported; renaming
  the file is your job.
- It does not check folder names — only the names of files.
- It does not check anything else about a file — no contents,
  no syntax, no size, no secrets. Filenames only.
- It does not pick your naming rule. The rule is lowercase
  kebab-case; if your project uses another style, this tool is
  not the one for it.

## Who it is for

Anyone who has ever opened a repo full of `Final v2 (1).docx`
and `My File.TXT`: a developer adding a CI step that fails the
build on a sloppy filename, a team lead who wants every file in
the repo to follow one naming rule, or anyone who wants one
small check instead of a naming rule buried inside a big linter
setup. If every name is clean, you get a plain OK line; if one
is not, the report says exactly which file and why.

## How this differs from similar tools

The exact name `filename-checker-cli` matches 0 repositories
on GitHub. The unquoted search for `filename checker` returns
61 results, and none of them is this tool:

- The top real rival, kenjis/codeigniter3-filename-checker
  (22 stars), checks file naming for one PHP framework
  (CodeIgniter3) only — not any folder, any project.
- The next, AgusQuintanar/FileNameChecker (0 stars), is a set
  of scripts that check a name against a convention, with no
  CI gate and no tests.
- The rest are a Bitbucket credentials checker (17 stars), a
  duplicate finder (6 stars), a test-case checker (7 stars),
  and a Chrome extension (2 stars) that checks for characters
  banned on some operating systems — different jobs.
- The search for `filename convention checker` returns 1
  result, the 0-star scripts above.

This tool does a narrower job: a Python standard-library-only
CLI that checks local filenames against one rule (lowercase
kebab-case), reports each bad name with its path and reason,
and exits 1 for CI — no install beyond Python, no framework,
no network.

## Install

Python standard library only — no packages to download. You need
Python 3.11 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/filename-checker-cli.git
cd filename-checker-cli
python3 src/filename_checker.py examples/clean-files/
```

```
OK — 4 file(s) checked, all names follow lowercase kebab-case.
```

## Usage

Check one file:

```
python3 src/filename_checker.py examples/bad-files/my_file.txt
```

```
FAIL examples/bad-files/my_file.txt: underscore in name
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

Check a whole folder (walked recursively):

```
python3 src/filename_checker.py examples/bad-files/
```

```
FAIL examples/bad-files/-leading.txt: starts with a hyphen
FAIL examples/bad-files/My File.txt: uppercase letter
FAIL examples/bad-files/My File.txt: space in name
FAIL examples/bad-files/UPPERCASE.md: uppercase letter
FAIL examples/bad-files/double--hyphen.txt: double hyphen
FAIL examples/bad-files/my_file.txt: underscore in name
FAIL examples/bad-files/photo.JPG: uppercase extension
FAIL examples/bad-files/trailing-.txt: ends with a hyphen
FAIL examples/bad-files/weird@name.txt: bad character '@'
Checked 8 file(s), 9 problem(s) in 8 file(s).
```

Check a folder and allow one conventional name:

```
python3 src/filename_checker.py examples/bad-files/ --allow UPPERCASE.md
```

```
FAIL examples/bad-files/-leading.txt: starts with a hyphen
FAIL examples/bad-files/My File.txt: uppercase letter
FAIL examples/bad-files/My File.txt: space in name
FAIL examples/bad-files/double--hyphen.txt: double hyphen
FAIL examples/bad-files/my_file.txt: underscore in name
FAIL examples/bad-files/photo.JPG: uppercase extension
FAIL examples/bad-files/trailing-.txt: ends with a hyphen
FAIL examples/bad-files/weird@name.txt: bad character '@'
Checked 7 file(s), 8 problem(s) in 7 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/filename_checker.py examples/bad-files/my_file.txt --json
```

```
{
  "files": [
    {
      "file": "examples/bad-files/my_file.txt",
      "reasons": [
        "underscore in name"
      ]
    }
  ],
  "summary": {
    "checked": 1,
    "files_with_problems": 1,
    "problems": 1
  }
}
```

Exit codes: 0 when no problem is found, 1 when any problem is
found, 2 for a usage or input problem (a missing file or folder,
a bad flag, no file to check).

## Examples

### 1. A folder with clean names

`examples/clean-files/` holds `readme.md`, `user-guide.md`,
`photo-1.jpg`, and `data-2026.csv`:

```
python3 src/filename_checker.py examples/clean-files/
```

```
OK — 4 file(s) checked, all names follow lowercase kebab-case.
```

### 2. A folder with bad names

`examples/bad-files/` holds eight files that each break the
rule in a different way — a space, an underscore, uppercase,
a double hyphen, a leading hyphen, a trailing hyphen, an
uppercase extension, and a bad character:

```
python3 src/filename_checker.py examples/bad-files/
```

```
FAIL examples/bad-files/-leading.txt: starts with a hyphen
FAIL examples/bad-files/My File.txt: uppercase letter
FAIL examples/bad-files/My File.txt: space in name
FAIL examples/bad-files/UPPERCASE.md: uppercase letter
FAIL examples/bad-files/double--hyphen.txt: double hyphen
FAIL examples/bad-files/my_file.txt: underscore in name
FAIL examples/bad-files/photo.JPG: uppercase extension
FAIL examples/bad-files/trailing-.txt: ends with a hyphen
FAIL examples/bad-files/weird@name.txt: bad character '@'
Checked 8 file(s), 9 problem(s) in 8 file(s).
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the clean files (pass), then the files with
bad names (fail, on purpose). Its full output is in
`examples/sample-output.txt`, ending with
`Checked 8 file(s), 9 problem(s) in 8 file(s).` The bad-files
run exits 1, which is the expected result — the script ends
with exit 0 so it can be run as a demo.

## How it is tested

47 tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_filename_checker.py
```

The tests cover: every naming fault (uppercase, space,
underscore, leading and trailing hyphen, double hyphen, bad
character, bad character in the extension, uppercase and
space in the extension, empty part, empty extension,
non-ASCII letter, one name with two reasons), clean names
(including `archive.tar.gz`, `my.file.txt`, a file with no
extension, and hidden files), folder walking (recursive,
`--no-recursive`, `.git` skipped, `--exclude`, `--allow`),
the CLI (exit 0/1/2, `--json` output, `--version`, bad flags,
missing paths, empty folders, input files left unchanged),
the bundled examples (sample output compared byte-for-byte
against a fresh run, and the README-quoted outputs checked
against it), and hygiene checks (no placeholder text, no
absolute paths, stdlib imports only, `.env` first in
`.gitignore`).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking filenames is not new — the similar tools named above
(the CodeIgniter3 filename checker, the FileNameChecker
scripts) are listed in "How this differs" — but every line of
code here is original, and the tool builds on nothing but
Python's standard library.
