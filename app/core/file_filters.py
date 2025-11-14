from pathlib import Path
from typing import List, Set
from app.utils.config import AppConfig


def get_enabled_extensions(languages: List[str]) -> Set[str]:
    enabled_exts = set()
    for lang in languages:
        ext_value = AppConfig.SUPPORTED_LANGUAGES.get(lang)
        if isinstance(ext_value, list):
            enabled_exts.update(ext_value)
        else:
            enabled_exts.add(ext_value)
    return enabled_exts


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
    languages: List[str],
    ignore_patterns: List[str] = None
) -> List[Path]:
    files = []
    enabled_exts = get_enabled_extensions(languages)

    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    for file_path in base_path.rglob('*'):
        if not file_path.is_file():
            continue

        if should_ignore(file_path, ignore_patterns):
            continue

        if file_path.suffix in enabled_exts:
            files.append(file_path)

    return files


def should_process_file(
    file_path: Path,
    languages: List[str],
    ignore_patterns: List[str] = None
) -> bool:
    enabled_exts = get_enabled_extensions(languages)

    if file_path.suffix not in enabled_exts:
        return False

    if should_ignore(file_path, ignore_patterns):
        return False

    return True


def get_watch_patterns(languages: List[str]) -> List[str]:
    patterns = []
    for lang in languages:
        ext_value = AppConfig.SUPPORTED_LANGUAGES.get(lang)
        if isinstance(ext_value, list):
            for ext in ext_value:
                patterns.append(f"*{ext}")
        else:
            patterns.append(f"*{ext_value}")
    return patterns


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
