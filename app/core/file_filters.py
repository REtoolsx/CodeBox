from pathlib import Path
from typing import List, Set
from app.utils.config import AppConfig
from app.indexer.parser import TreeSitterParser


def get_all_supported_extensions() -> Set[str]:
    parser = TreeSitterParser()
    return parser.get_all_supported_extensions()


def should_ignore(file_path: Path, ignore_patterns: List[str] = None, project_path: Path = None) -> bool:
    path_str = str(file_path)

    path_parts = file_path.parts
    for part in path_parts:
        if part.startswith('.') and len(part) > 1:
            return True

    if project_path:
        ignore_config = AppConfig.get_ignore_config(str(project_path))
        path_blacklist = ignore_config.get('path_blacklist', [])

        for blacklisted_path in path_blacklist:
            if blacklisted_path in path_str:
                return True

    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    for pattern in ignore_patterns:
        if pattern in path_str:
            return True

    return False


def find_files(
    base_path: Path,
    ignore_patterns: List[str] = None
) -> List[Path]:
    files = []

    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    for file_path in base_path.rglob('*'):
        if not file_path.is_file():
            continue

        if should_process_file(file_path, ignore_patterns, base_path):
            files.append(file_path)

    return files


def should_process_file(
    file_path: Path,
    ignore_patterns: List[str] = None,
    project_path: Path = None
) -> bool:
    if project_path:
        ignore_config = AppConfig.get_ignore_config(str(project_path))
        extension_blacklist = ignore_config.get('extension_blacklist', [])

        if file_path.suffix.lower() in extension_blacklist:
            return False

    supported_exts = get_all_supported_extensions()
    if file_path.suffix.lower() not in supported_exts:
        return False

    if should_ignore(file_path, ignore_patterns, project_path):
        return False

    return True


def get_watch_patterns() -> List[str]:
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
