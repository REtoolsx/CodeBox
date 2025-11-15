from typing import List, Optional
from pathlib import Path

from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationHelpers:

    @staticmethod
    def validate_project_path(path: str, raise_error: bool = True) -> bool:
        try:
            path_obj = Path(path)

            if not path_obj.exists():
                if raise_error:
                    raise ValueError(f"Project path does not exist: {path}")
                return False

            if not path_obj.is_dir():
                if raise_error:
                    raise ValueError(f"Project path is not a directory: {path}")
                return False

            return True

        except Exception as e:
            if raise_error:
                raise ValueError(f"Invalid project path: {str(e)}")
            return False

    @staticmethod
    def validate_search_params(
        query: str,
        mode: str,
        limit: int,
        raise_error: bool = True
    ) -> bool:
        if not query or not query.strip():
            if raise_error:
                raise ValueError("Search query cannot be empty")
            return False

        valid_modes = ["hybrid", "vector", "keyword"]
        if mode not in valid_modes:
            if raise_error:
                raise ValueError(f"Invalid search mode: {mode}. Must be one of {valid_modes}")
            return False

        if limit <= 0:
            if raise_error:
                raise ValueError("Limit must be a positive integer")
            return False

        if limit > 1000:
            if raise_error:
                raise ValueError("Limit cannot exceed 1000")
            return False

        return True

    @staticmethod
    def validate_embedding_model(model_name: str, raise_error: bool = True) -> bool:
        if not model_name:
            if raise_error:
                raise ValueError("Model name cannot be empty")
            return False

        if model_name in AppConfig.AVAILABLE_EMBEDDING_MODELS:
            return True

        for key, info in AppConfig.AVAILABLE_EMBEDDING_MODELS.items():
            if model_name == info['full_name']:
                return True

        logger.warning(f"Using custom embedding model: {model_name}")
        return True

    @staticmethod
    def validate_context_lines(context: int, raise_error: bool = True) -> bool:
        if context < 0:
            if raise_error:
                raise ValueError("Context lines cannot be negative")
            return False

        if context > 100:
            if raise_error:
                raise ValueError("Context lines cannot exceed 100")
            return False

        return True
