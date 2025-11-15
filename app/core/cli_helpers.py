import json
import sys
import re
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


def pretty_print_with_clean_code(data: Dict[str, Any]) -> str:
    def serialize(obj, indent=0):
        indent_str = "  " * indent
        next_indent_str = "  " * (indent + 1)

        if isinstance(obj, dict):
            if not obj:
                return "{}"

            lines = ["{"]
            items = list(obj.items())

            for i, (key, value) in enumerate(items):
                is_last = i == len(items) - 1
                comma = "" if is_last else ","

                if (key == "code" or key == "content") and isinstance(value, list):
                    lines.append(f'{next_indent_str}"{key}": [')
                    for code_line in value:
                        lines.append(f'{next_indent_str}  {code_line}')
                    lines.append(f'{next_indent_str}]{comma}')
                else:
                    serialized = serialize(value, indent + 1)
                    if isinstance(value, (dict, list)) and value:
                        lines.append(f'{next_indent_str}"{key}": {serialized}{comma}')
                    else:
                        lines.append(f'{next_indent_str}"{key}": {serialized}{comma}')

            lines.append(f'{indent_str}}}')
            return '\n'.join(lines)

        elif isinstance(obj, list):
            if not obj:
                return "[]"

            if all(isinstance(item, dict) for item in obj):
                lines = ["["]
                for i, item in enumerate(obj):
                    is_last = i == len(obj) - 1
                    comma = "" if is_last else ","
                    serialized = serialize(item, indent + 1)
                    item_lines = serialized.split('\n')
                    for j, line in enumerate(item_lines):
                        if j == 0:
                            lines.append(f'{next_indent_str}{line}')
                        else:
                            lines.append(f'{next_indent_str}{line}')
                    if not is_last:
                        lines[-1] = lines[-1].rstrip('}') + '},'
                lines.append(f'{indent_str}]')
                return '\n'.join(lines)
            else:
                return json.dumps(obj, ensure_ascii=False)

        else:
            return json.dumps(obj, ensure_ascii=False)

    return serialize(data)


class CLIErrorHandler:
    @staticmethod
    def handle_error(operation: str, error: Exception, output_json: bool = True) -> None:
        error_msg = f"{operation} failed: {str(error)}"
        logger.error(error_msg)

        if output_json:
            print(json.dumps({
                "success": False,
                "error": str(error),
                "operation": operation.lower()
            }, indent=2, ensure_ascii=False))

        sys.exit(1)

    @staticmethod
    def handle_success(data: Dict[str, Any]) -> None:
        data["success"] = True
        print(pretty_print_with_clean_code(data))


class CLIProjectPathResolver:
    def __init__(self, project_manager):
        self.project_manager = project_manager
        self._cached_path = None

    def get_path(self, force_refresh: bool = False) -> str:
        if self._cached_path is None or force_refresh:
            self._cached_path = self.project_manager.get_current_project_path()
        return self._cached_path

    def clear_cache(self) -> None:
        self._cached_path = None
