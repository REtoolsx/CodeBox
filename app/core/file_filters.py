from pathlib import Path
from typing import List, Set
from app.utils.config import AppConfig
from app.indexer.parser import TreeSitterParser


def get_all_supported_extensions() -> Set[str]:
    """Get all supported file extensions from Pygments"""
    parser = TreeSitterParser()
    return parser.get_all_supported_extensions()


def should_ignore(file_path: Path, ignore_patterns: List[str] = None) -> bool:
    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    path_str = str(file_path)
    for pattern in ignore_patterns:
        if pattern in path_str:
            return True
    return False


def find_files(
    base_path: Path,
    ignore_patterns: List[str] = None
) -> List[Path]:
    """Find all supported files (auto-detected from Pygments)"""
    files = []
    supported_exts = get_all_supported_extensions()

    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    for file_path in base_path.rglob('*'):
        if not file_path.is_file():
            continue

        if should_ignore(file_path, ignore_patterns):
            continue

        if file_path.suffix.lower() in supported_exts:
            files.append(file_path)

    return files


def should_process_file(
    file_path: Path,
    ignore_patterns: List[str] = None
) -> bool:
    """Check if file should be processed (auto-detected from Pygments)"""
    supported_exts = get_all_supported_extensions()

    if file_path.suffix.lower() not in supported_exts:
        return False

    if should_ignore(file_path, ignore_patterns):
        return False

    return True


def get_watch_patterns() -> List[str]:
    """Get watch patterns for all supported file extensions"""
    supported_exts = get_all_supported_extensions()
    return [f"*{ext}" for ext in supported_exts]


def get_ignore_patterns(base_patterns: List[str] = None) -> List[str]:
    if base_patterns is None:
        base_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    ignore = []
    for pattern in base_patterns:
        if pattern.startswith('*.'):
            ignore.append(pattern)
        else:
            ignore.append(f"*/{pattern}/*")
            ignore.append(f"*{pattern}*")
    return ignore
