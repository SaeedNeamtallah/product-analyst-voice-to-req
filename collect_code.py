"""
Collect all project source code into a single .txt file.
Skips: venv, node_modules, __pycache__, .git, uploads, *.pyc, etc.
"""
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent

# Extensions to include
INCLUDE_EXTENSIONS = {
    ".py", ".js", ".html", ".css", ".json", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".md", ".txt", ".env", ".bat", ".ps1", ".sh",
    ".sql", ".dockerfile",
}

# Directories to skip entirely
SKIP_DIRS = {
    "venv", "node_modules", "__pycache__", ".git", ".github",
    "uploads", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info", ".tox", ".idea", ".vscode",
    ".gemini", "brain",
}

# Files to skip
SKIP_FILES = {
    "collect_code.py",  # Don't include this script itself
    "package-lock.json",
    "poetry.lock",
    "uv.lock",
}

OUTPUT_FILE = PROJECT_ROOT / "project_code.txt"


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def should_include_file(file_path: Path) -> bool:
    if file_path.name in SKIP_FILES:
        return False
    # Include files with known extensions OR extensionless config files
    ext = file_path.suffix.lower()
    if ext in INCLUDE_EXTENSIONS:
        return True
    # Include Dockerfile, Makefile, etc. (no extension)
    if file_path.name in {"Dockerfile", "Makefile", "Procfile", ".env.example"}:
        return True
    return False


def collect_files() -> list[Path]:
    """Walk the project tree and collect relevant files."""
    files = []
    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        # Filter out skipped directories (in-place to prevent os.walk from descending)
        dirs[:] = [d for d in sorted(dirs) if not should_skip_dir(d)]

        for fname in sorted(filenames):
            fpath = Path(root) / fname
            if should_include_file(fpath):
                files.append(fpath)
    return files


def main():
    files = collect_files()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"{'=' * 80}\n")
        out.write(f"  PROJECT CODE DUMP\n")
        out.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"  Root: {PROJECT_ROOT}\n")
        out.write(f"  Total files: {len(files)}\n")
        out.write(f"{'=' * 80}\n\n")

        # Table of contents
        out.write("TABLE OF CONTENTS\n")
        out.write("-" * 40 + "\n")
        for i, fpath in enumerate(files, 1):
            relative = fpath.relative_to(PROJECT_ROOT)
            out.write(f"  {i:3d}. {relative}\n")
        out.write("\n" + "=" * 80 + "\n\n")

        # File contents
        for i, fpath in enumerate(files, 1):
            relative = fpath.relative_to(PROJECT_ROOT)
            out.write(f"{'#' * 80}\n")
            out.write(f"# FILE: {relative}\n")
            out.write(f"{'#' * 80}\n\n")

            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                out.write(content)
                if not content.endswith("\n"):
                    out.write("\n")
            except Exception as e:
                out.write(f"[ERROR reading file: {e}]\n")

            out.write("\n")

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"Done! Collected {len(files)} files into: {OUTPUT_FILE}")
    print(f"Output size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
