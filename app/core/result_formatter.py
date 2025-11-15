from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
import json


def format_content_with_line_numbers(content: str, start_line: int) -> str:
    if not content:
        return ""

    lines = content.split('\n')
    formatted_lines = []

    for i, line in enumerate(lines):
        line_num = start_line + i
        formatted_lines.append(f"{line_num:>4}│ {line}")

    return '\n'.join(formatted_lines)


def _parse_json_field(value: str) -> Any:
    if not value or value == "":
        return None

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _parse_imports_string(imports_str: str) -> List[str]:
    if not imports_str or imports_str == "":
        return []

    imports_list = [imp.strip() for imp in imports_str.split(',') if imp.strip()]
    return imports_list


def add_truncation_indicator(content: str, total_lines: int, shown_lines: int) -> str:
    indicator = f"\n... [truncated: showing {shown_lines}/{total_lines} lines]"
    return content + indicator


def detect_code_structure(lines: List[str], max_line_idx: int) -> int:
    import re

    if max_line_idx >= len(lines):
        return max_line_idx

    last_line = lines[max_line_idx - 1].strip() if max_line_idx > 0 else ""

    structure_patterns = [
        r'^\s*(def|class|async\s+def)\s+\w+',
        r'^\s*(if|for|while|try|with|elif|else)\s*.*:\s*$',
        r'^\s*@\w+',
    ]

    for pattern in structure_patterns:
        if re.match(pattern, last_line):
            additional_lines = min(5, len(lines) - max_line_idx)
            return max_line_idx + additional_lines

    return max_line_idx


def smart_truncate_code(
    content: str,
    max_chars: int = 800,
    max_lines: int = 20,
    preserve_structure: bool = True
) -> Tuple[str, bool, int, int]:
    if not content:
        return ("", False, 0, 0)

    lines = content.split('\n')

    if len(content) <= max_chars and len(lines) <= max_lines:
        return (content, False, len(lines), len(lines))

    truncate_at_line = min(max_lines, len(lines))

    accumulated_chars = 0
    for i in range(truncate_at_line):
        accumulated_chars += len(lines[i]) + 1
        if accumulated_chars > max_chars:
            truncate_at_line = max(1, i)
            break

    if preserve_structure and truncate_at_line < len(lines):
        truncate_at_line = detect_code_structure(lines, truncate_at_line)

    truncated_lines = lines[:truncate_at_line]
    truncated_content = '\n'.join(truncated_lines)

    is_truncated = truncate_at_line < len(lines)
    return (truncated_content, is_truncated, truncate_at_line, len(lines))


def _format_compact(
    result: Dict[str, Any],
    formatted_content: str,
    score: float
) -> Dict[str, Any]:
    file_path = result.get("file_path", "")
    start_line = result.get("start_line", 0)
    end_line = result.get("end_line", 0)
    chunk_type = result.get("chunk_type", "code")
    node_name = result.get("node_name", "")
    parent_scope = result.get("parent_scope", "")
    signature = result.get("signature", "")

    compact_result = {
        "file": f"{file_path}:{start_line}-{end_line}",
        "type": chunk_type,
        "score": round(score, 4)
    }

    if node_name:
        compact_result["name"] = node_name

    if parent_scope:
        compact_result["scope"] = parent_scope

    if signature:
        compact_result["signature"] = signature

    compact_result["code"] = formatted_content.split('\n') if formatted_content else []

    return compact_result


def _format_standard(
    result: Dict[str, Any],
    formatted_content: str,
    score: float,
    content_length: int,
    is_truncated: bool
) -> Dict[str, Any]:
    file_path = result.get("file_path", "")
    start_line = result.get("start_line", 0)
    end_line = result.get("end_line", 0)
    language = result.get("language", "")
    chunk_type = result.get("chunk_type", "code")
    node_name = result.get("node_name", "")
    full_path = result.get("full_path", "")
    signature = result.get("signature", "")
    parameters = _parse_json_field(result.get("parameters", ""))
    return_type = result.get("return_type", "")
    docstring = result.get("docstring", "")

    standard_result = {
        "file": file_path,
        "lines": f"{start_line}-{end_line}",
        "language": language,
        "type": chunk_type,
        "score": round(score, 4),
        "code": formatted_content.split('\n') if formatted_content else []
    }

    if node_name:
        standard_result["name"] = node_name

    if full_path:
        standard_result["scope"] = full_path

    if signature:
        standard_result["signature"] = signature

    if parameters:
        standard_result["params"] = parameters

    if return_type:
        standard_result["returns"] = return_type

    if docstring:
        standard_result["docstring"] = docstring

    if is_truncated:
        standard_result["truncated"] = True
        standard_result["length"] = content_length

    return standard_result


def _format_verbose(
    result: Dict[str, Any],
    formatted_content: str,
    score: float,
    content_length: int,
    is_truncated: bool
) -> Dict[str, Any]:
    verbose_result = {
        "location": {
            "file": result.get("file_path", ""),
            "lines": {
                "start": result.get("start_line", 0),
                "end": result.get("end_line", 0)
            },
            "language": result.get("language", "")
        },
        "symbol": {
            "type": result.get("chunk_type", "code")
        },
        "code": {
            "content": formatted_content.split('\n') if formatted_content else [],
            "length": content_length,
            "truncated": is_truncated
        },
        "relevance": {
            "score": round(score, 4)
        }
    }

    node_name = result.get("node_name", "")
    if node_name:
        verbose_result["symbol"]["name"] = node_name

    full_path = result.get("full_path", "")
    if full_path:
        verbose_result["symbol"]["scope"] = full_path

    scope_depth = result.get("scope_depth", 0)
    if scope_depth > 0:
        verbose_result["symbol"]["depth"] = scope_depth

    signature = result.get("signature", "")
    if signature:
        verbose_result["symbol"]["signature"] = signature

    parameters = _parse_json_field(result.get("parameters", ""))
    if parameters:
        verbose_result["symbol"]["params"] = parameters

    return_type = result.get("return_type", "")
    if return_type:
        verbose_result["symbol"]["returns"] = return_type

    decorators = _parse_json_field(result.get("decorators", ""))
    if decorators:
        verbose_result["symbol"]["decorators"] = decorators

    calls = _parse_json_field(result.get("calls", ""))
    imports = _parse_imports_string(result.get("imports", ""))
    docstring = result.get("docstring", "")

    if calls or imports or docstring:
        verbose_result["metadata"] = {}

        if calls:
            verbose_result["metadata"]["calls"] = calls

        if imports:
            verbose_result["metadata"]["imports"] = imports

        if docstring:
            verbose_result["metadata"]["docstring"] = docstring

    return verbose_result


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
    preview_length: int = 800,
    preview_lines: int = 20,
    full_content: bool = False,
    max_content_length: int = 10000,
    output_format: str = "compact",
    smart_truncate: bool = True
) -> List[Dict[str, Any]]:
    processed_results = []

    for idx, r in enumerate(results):
        raw_content = r.get("content", "")

        if smart_truncate and not full_content:
            truncated_content, is_truncated, shown_lines, total_lines = smart_truncate_code(
                raw_content,
                max_chars=preview_length,
                max_lines=preview_lines,
                preserve_structure=True
            )
        else:
            truncated_content = raw_content[:max_content_length] if full_content else raw_content[:preview_length]
            is_truncated = len(raw_content) > (max_content_length if full_content else preview_length)
            shown_lines = 0
            total_lines = 0

        formatted_content = truncated_content

        if is_truncated and shown_lines > 0:
            formatted_content = add_truncation_indicator(formatted_content, total_lines, shown_lines)

        content_length = len(raw_content)
        score = calculate_score(r, mode, idx + 1, len(results))

        if output_format == "compact":
            result_dict = _format_compact(r, formatted_content, score)
        elif output_format == "standard":
            result_dict = _format_standard(r, formatted_content, score, content_length, is_truncated)
        else:
            result_dict = _format_verbose(r, formatted_content, score, content_length, is_truncated)

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
