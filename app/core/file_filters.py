from pathlib import Path
from typing import List, Set
from app.utils.config import AppConfig
from app.indexer.parser import TreeSitterParser


def get_all_supported_extensions() -> Set[str]:
    """Get all supported file extensions from Pygments"""
    parser = TreeSitterParser()
    return parser.get_all_supported_extensions()


def should_ignore(file_path: Path, ignore_patterns: List[str] = None, project_path: Path = None) -> bool:
    """
    Check if file should be ignored based on path patterns

    Args:
        file_path: File path to check
        ignore_patterns: Legacy ignore patterns (deprecated)
        project_path: Project root path (for loading config)

    Returns:
        True if file should be ignored
    """
    path_str = str(file_path)

    # Check config-based path_blacklist if project_path is provided
    if project_path:
        from app.utils.config import AppConfig
        ignore_config = AppConfig.get_ignore_config(str(project_path))
        path_blacklist = ignore_config.get('path_blacklist', [])

        for blacklisted_path in path_blacklist:
            if blacklisted_path in path_str:
                return True

    # Fallback to legacy ignore_patterns
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
    """Find all supported files (auto-detected from Pygments)"""
    files = []

    if ignore_patterns is None:
        ignore_patterns = AppConfig.DEFAULT_IGNORE_PATTERNS

    for file_path in base_path.rglob('*'):
        if not file_path.is_file():
            continue

        # Use should_process_file which handles both extension and path blacklists
        if should_process_file(file_path, ignore_patterns, base_path):
            files.append(file_path)

    return files


def should_process_file(
    file_path: Path,
    ignore_patterns: List[str] = None,
    project_path: Path = None
) -> bool:
    """
    Check if file should be processed

    Args:
        file_path: File path to check
        ignore_patterns: Legacy ignore patterns (deprecated)
        project_path: Project root path (for loading config)

    Returns:
        True if file should be processed
    """
    # Check extension_blacklist if project_path is provided
    if project_path:
        from app.utils.config import AppConfig
        ignore_config = AppConfig.get_ignore_config(str(project_path))
        extension_blacklist = ignore_config.get('extension_blacklist', [])

        if file_path.suffix.lower() in extension_blacklist:
            return False

    # Check if extension is supported
    supported_exts = get_all_supported_extensions()
    if file_path.suffix.lower() not in supported_exts:
        return False

    # Check path ignore patterns
    if should_ignore(file_path, ignore_patterns, project_path):
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
