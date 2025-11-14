import json
import sys
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
        print(json.dumps(data, indent=2, ensure_ascii=False))


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
