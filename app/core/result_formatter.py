from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path


def calculate_score(result: Dict[str, Any], mode: str, rank: int = 1, total: int = 1) -> float:
    if mode == "hybrid":
        return result.get('rrf_score', 0.0)
    elif mode == "vector":
        distance = result.get('_distance', 1.0)
        return 1.0 / (1.0 + distance)
    elif mode == "keyword":
        return (total - rank + 1) / max(total, 1)
    else:
        return 0.0


def get_context_lines(
    file_path: str,
    start_line: int,
    end_line: int,
    context: int,
    project_path: str
) -> Tuple[List[str], List[str]]:
    try:
        full_path = Path(project_path) / file_path
        if not full_path.exists():
            return ([], [])

        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()

        context_start = max(0, start_line - context)
        lines_before = all_lines[context_start:start_line]

        context_end = min(len(all_lines), end_line + 1 + context)
        lines_after = all_lines[end_line + 1:context_end]

        return (
            [line.rstrip() for line in lines_before],
            [line.rstrip() for line in lines_after]
        )
    except Exception:
        return ([], [])


def process_cli_results(
    results: List[Dict[str, Any]],
    mode: str,
    project_path: str,
    context: int = 0,
    preview_length: int = 200,
    full_content: bool = False,
    max_content_length: int = 10000
) -> List[Dict[str, Any]]:
    """
    Process search results for CLI output format

    Args:
        results: Raw search results
        mode: Search mode (hybrid, vector, keyword)
        project_path: Project directory path
        context: Number of context lines before/after
        preview_length: Length of content preview
        full_content: Whether to include full content
        max_content_length: Maximum content length when full_content=True

    Returns:
        List of processed result dictionaries
    """
    processed_results = []

    for idx, r in enumerate(results):
        result_dict = {
            "file_path": r.get("file_path"),
            "start_line": r.get("start_line"),
            "end_line": r.get("end_line"),
            "language": r.get("language"),
            "chunk_type": r.get("chunk_type"),
            "node_name": r.get("node_name", ""),
            "size_bytes": r.get("size_bytes", 0),
            "modified_at": r.get("modified_at", ""),
            "content": r.get("content", "")[:max_content_length] if full_content
                      else r.get("content", "")[:preview_length],
            "content_preview": r.get("content", "")[:preview_length],
            "content_length": len(r.get("content", "")),
            "is_truncated": len(r.get("content", "")) > (max_content_length if full_content else preview_length),
            "score": calculate_score(r, mode, idx + 1, len(results))
        }

        # Add metadata fields (Schema v2.5)
        metadata_fields = {
            "signature": r.get("signature", ""),
            "parameters": r.get("parameters", ""),
            "return_type": r.get("return_type", ""),
            "docstring": r.get("docstring", ""),
            "decorators": r.get("decorators", ""),
            "imports": r.get("imports", ""),
            "parent_scope": r.get("parent_scope", ""),
            "full_path": r.get("full_path", ""),
            "scope_depth": r.get("scope_depth", 0),
            "calls": r.get("calls", "")
        }

        # Only include non-empty metadata fields
        for key, value in metadata_fields.items():
            if value:  # Include if not empty string or 0 (for scope_depth we keep 0)
                result_dict[key] = value
            elif key == "scope_depth":  # Always include scope_depth even if 0
                result_dict[key] = value

        # Add context lines if requested
        if context > 0:
            lines_before, lines_after = get_context_lines(
                r.get("file_path"),
                r.get("start_line"),
                r.get("end_line"),
                context,
                project_path
            )
            result_dict["context"] = {
                "lines_before": lines_before,
                "lines_after": lines_after,
                "range_before": f"{max(0, r.get('start_line') - context)}-{r.get('start_line') - 1}",
                "range_after": f"{r.get('end_line') + 1}-{r.get('end_line') + context}"
            }

        processed_results.append(result_dict)

    return processed_results


def add_context_to_result(
    result: Dict[str, Any],
    context: int,
    project_path: str
) -> Dict[str, Any]:
    """
    Add context lines to a single result

    Args:
        result: Single search result
        context: Number of context lines before/after
        project_path: Project directory path

    Returns:
        Result dictionary with added context
    """
    if context <= 0:
        return result

    lines_before, lines_after = get_context_lines(
        result.get("file_path"),
        result.get("start_line"),
        result.get("end_line"),
        context,
        project_path
    )

    result["context"] = {
        "lines_before": lines_before,
        "lines_after": lines_after,
        "range_before": f"{max(0, result.get('start_line') - context)}-{result.get('start_line') - 1}",
        "range_after": f"{result.get('end_line') + 1}-{result.get('end_line') + context}"
    }

    return result
