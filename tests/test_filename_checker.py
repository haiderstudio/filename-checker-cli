"""Tests for filename_checker — standard library unittest only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(SRC))

import filename_checker  # noqa: E402


def run_cli(*args, cwd=None):
    argv = [sys.executable, str(SRC / "filename_checker.py"), *args]
    return subprocess.run(
        argv, capture_output=True, text=True, cwd=cwd or ROOT
    )


def write(tmp, name, text="content\n"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class CheckNameTests(unittest.TestCase):
    def check(self, name):
        return filename_checker.check_name(name)

    def test_clean_names(self):
        for name in (
            "readme.md",
            "user-guide.md",
            "photo-1.jpg",
            "data-2026.csv",
            "a.txt",
            "123.txt",
            "my-file-2.txt",
            "no-extension",
            "archive.tar.gz",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.check(name), [])

    def test_hidden_file_is_clean(self):
        self.assertEqual(self.check(".gitignore"), [])
        self.assertEqual(self.check(".hidden-file"), [])

    def test_uppercase_letter(self):
        self.assertIn("uppercase letter", self.check("MyFile.txt"))
        self.assertIn("uppercase letter", self.check("UPPERCASE.md"))

    def test_space_in_name(self):
        self.assertIn("space in name", self.check("My File.txt"))

    def test_underscore_in_name(self):
        self.assertIn("underscore in name", self.check("my_file.txt"))

    def test_leading_hyphen(self):
        self.assertIn("starts with a hyphen", self.check("-leading.txt"))

    def test_trailing_hyphen(self):
        self.assertIn("ends with a hyphen", self.check("trailing-.txt"))

    def test_double_hyphen(self):
        self.assertIn("double hyphen", self.check("double--hyphen.txt"))

    def test_bad_character(self):
        reasons = self.check("weird@name.txt")
        self.assertIn("bad character '@'", reasons)

    def test_bad_character_in_extension(self):
        reasons = self.check("file.tx@t")
        self.assertIn("bad character '@' in extension", reasons)

    def test_uppercase_extension(self):
        self.assertIn("uppercase extension", self.check("photo.JPG"))
        self.assertIn("uppercase extension", self.check("photo.Jpg"))

    def test_space_in_extension(self):
        self.assertIn("space in extension", self.check("file. txt"))

    def test_dots_separate_clean_segments(self):
        # Dots only separate parts: archive.tar.gz and my.file.txt
        # are clean, because every part is a clean kebab segment.
        self.assertEqual(self.check("my.file.txt"), [])
        self.assertEqual(self.check("archive.tar.gz"), [])

    def test_double_dot_is_empty_name(self):
        reasons = self.check("my..file.txt")
        self.assertIn("empty name", reasons)

    def test_empty_name(self):
        self.assertIn("empty name", self.check("..txt"))

    def test_empty_extension(self):
        self.assertIn("empty extension", self.check("file."))

    def test_hidden_file_named_txt_is_clean(self):
        # ".txt" is a hidden file named "txt", not an empty name.
        self.assertEqual(self.check(".txt"), [])

    def test_non_ascii_letter(self):
        reasons = self.check("café.txt")
        self.assertIn("bad character 'é'", reasons)

    def test_one_name_many_reasons(self):
        reasons = self.check("My File.txt")
        self.assertEqual(reasons, ["uppercase letter", "space in name"])

    def test_hidden_file_with_bad_name(self):
        reasons = self.check(".My File")
        self.assertIn("uppercase letter", reasons)
        self.assertIn("space in name", reasons)


class CollectFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_collects_files_and_folders(self):
        write(self.root, "good-name.txt")
        write(self.root, "sub/bad name.txt")
        files = filename_checker.collect_files([str(self.root)])
        names = sorted(p.name for p in files)
        self.assertEqual(names, ["bad name.txt", "good-name.txt"])

    def test_no_recursive(self):
        write(self.root, "top.txt")
        write(self.root, "sub/deep.txt")
        files = filename_checker.collect_files(
            [str(self.root)], recursive=False
        )
        self.assertEqual([p.name for p in files], ["top.txt"])

    def test_git_folder_never_walked(self):
        write(self.root, ".git/Bad Name.txt")
        write(self.root, "good-name.txt")
        files = filename_checker.collect_files([str(self.root)])
        self.assertEqual([p.name for p in files], ["good-name.txt"])

    def test_exclude_glob(self):
        write(self.root, "keep.txt")
        write(self.root, "skip me.txt")
        files = filename_checker.collect_files(
            [str(self.root)], excludes=["*skip*"]
        )
        self.assertEqual([p.name for p in files], ["keep.txt"])

    def test_allow_exact_name(self):
        write(self.root, "Makefile")
        write(self.root, "good-name.txt")
        files = filename_checker.collect_files(
            [str(self.root)], allowed=["Makefile"]
        )
        self.assertEqual([p.name for p in files], ["good-name.txt"])

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            filename_checker.collect_files([str(self.root / "nope")])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_clean_folder_exits_zero(self):
        write(self.root, "good-name.txt")
        write(self.root, "another-one.md")
        result = run_cli(str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "OK — 2 file(s) checked, all names follow lowercase kebab-case.",
            result.stdout,
        )

    def test_bad_folder_exits_one_with_paths(self):
        write(self.root, "My File.txt")
        write(self.root, "good-name.txt")
        result = run_cli(str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("My File.txt: uppercase letter", result.stdout)
        self.assertIn("My File.txt: space in name", result.stdout)
        self.assertIn(
            "Checked 2 file(s), 2 problem(s) in 1 file(s).", result.stdout
        )

    def test_single_file(self):
        path = write(self.root, "bad_name.txt")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("underscore in name", result.stdout)

    def test_default_path_is_current_folder(self):
        write(self.root, "good-name.txt")
        result = run_cli(cwd=str(self.root))
        self.assertEqual(result.returncode, 0)

    def test_allow_flag(self):
        write(self.root, "Makefile")
        write(self.root, "good-name.txt")
        result = run_cli(str(self.root), "--allow", "Makefile")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)

    def test_exclude_flag(self):
        write(self.root, "Bad Name.txt")
        write(self.root, "good-name.txt")
        result = run_cli(str(self.root), "--exclude", "*Bad*")
        self.assertEqual(result.returncode, 0)

    def test_json_output(self):
        write(self.root, "My File.txt")
        result = run_cli(str(self.root), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 2)
        self.assertEqual(payload["summary"]["checked"], 1)
        self.assertEqual(
            payload["files"][0]["reasons"],
            ["uppercase letter", "space in name"],
        )
        # The summary goes to stderr, so stdout stays clean JSON.
        self.assertIn("Checked 1 file(s)", result.stderr)

    def test_json_clean(self):
        write(self.root, "good-name.txt")
        result = run_cli(str(self.root), "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["files"], [])
        self.assertEqual(payload["summary"]["problems"], 0)

    def test_version_flag(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("filename_checker 1.0.0", result.stdout)

    def test_missing_path_exits_two(self):
        result = run_cli(str(self.root / "nope"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such file or folder", result.stderr)

    def test_empty_folder_exits_two(self):
        result = run_cli(str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no files to check", result.stderr)

    def test_bad_flag_exits_two(self):
        result = run_cli("--no-such-flag")
        self.assertEqual(result.returncode, 2)

    def test_input_files_unchanged(self):
        path = write(self.root, "My File.txt", "keep me\n")
        before = path.read_bytes()
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(path.read_bytes(), before)

    def test_bundled_examples(self):
        clean = run_cli("examples/clean-files/")
        self.assertEqual(clean.returncode, 0)
        bad = run_cli("examples/bad-files/")
        self.assertEqual(bad.returncode, 1)
        self.assertIn(
            "Checked 8 file(s), 9 problem(s) in 8 file(s).", bad.stdout
        )
        whole = run_cli("examples/")
        self.assertEqual(whole.returncode, 1)
        self.assertIn(
            "Checked 14 file(s), 9 problem(s) in 8 file(s).", whole.stdout
        )

    def test_sample_output_matches_a_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout, (EXAMPLES / "sample-output.txt").read_text()
        )

    def test_run_example_script_exits_zero(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)


class HygieneTests(unittest.TestCase):
    """The template gate: no placeholder text, no secrets, no local
    paths, stdlib imports only. The scan skips .git and __pycache__
    (Day 21 rule) and skips tests/ itself (Day 22 pattern), because
    this file's own banned-word list would otherwise trip it."""

    BANNED = ("TODO", "FIXME", "coming soon", "lorem", "API_KEY")

    def _repo_files(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            yield path

    def test_no_placeholder_text(self):
        hits = []
        for path in self._repo_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for word in self.BANNED:
                if word in text:
                    hits.append(f"{path.relative_to(ROOT)}: {word}")
        self.assertEqual(hits, [])

    def test_no_absolute_local_paths(self):
        hits = []
        for path in self._repo_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "/home/" in text or "/Users/" in text or "C:\\" in text:
                hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_stdlib_only_imports(self):
        import ast

        allowed = {
            "argparse",
            "contextlib",
            "fnmatch",
            "json",
            "sys",
            "pathlib",
            # Test file only: json, subprocess, tempfile, unittest.
            "subprocess",
            "tempfile",
            "unittest",
        }
        src = ROOT / "src" / "filename_checker.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        self.assertEqual(imported - allowed, set())

    def test_gitignore_lists_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_readme_quoted_outputs_are_real(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn(
            "FAIL examples/bad-files/My File.txt: uppercase letter",
            readme,
        )
        self.assertIn("Checked 8 file(s), 9 problem(s) in 8 file(s).", readme)
        self.assertIn(
            "OK — 4 file(s) checked, all names follow lowercase kebab-case.",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
