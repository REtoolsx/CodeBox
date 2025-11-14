from typing import List, Optional
from pathlib import Path

from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationHelpers:
    """Common validation functions for both CLI and GUI"""

    @staticmethod
    def validate_project_path(path: str, raise_error: bool = True) -> bool:
        """
        Validate project directory exists and is accessible

        Args:
            path: Project directory path
            raise_error: If True, raises ValueError on invalid path

        Returns:
            True if path is valid

        Raises:
            ValueError: If path is invalid and raise_error is True
        """
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
    def validate_languages(languages: List[str], raise_error: bool = True) -> List[str]:
        """
        Validate and filter language list to only supported languages

        Args:
            languages: List of language codes
            raise_error: If True, raises ValueError if no valid languages

        Returns:
            List of valid language codes

        Raises:
            ValueError: If no valid languages and raise_error is True
        """
        if not languages:
            if raise_error:
                raise ValueError("Language list cannot be empty")
            return []

        supported_langs = set(AppConfig.SUPPORTED_LANGUAGES.keys())
        valid_languages = [lang for lang in languages if lang in supported_langs]

        if not valid_languages:
            if raise_error:
                raise ValueError("No valid languages found in the provided list")
            return []

        # Log filtered languages
        invalid_langs = set(languages) - set(valid_languages)
        if invalid_langs:
            logger.warning(f"Filtered out unsupported languages: {', '.join(invalid_langs)}")

        return valid_languages

    @staticmethod
    def validate_search_params(
        query: str,
        mode: str,
        limit: int,
        raise_error: bool = True
    ) -> bool:
        """
        Validate search parameters

        Args:
            query: Search query string
            mode: Search mode (hybrid, vector, keyword)
            limit: Maximum number of results
            raise_error: If True, raises ValueError on invalid params

        Returns:
            True if all parameters are valid

        Raises:
            ValueError: If any parameter is invalid and raise_error is True
        """
        # Validate query
        if not query or not query.strip():
            if raise_error:
                raise ValueError("Search query cannot be empty")
            return False

        # Validate mode
        valid_modes = ["hybrid", "vector", "keyword"]
        if mode not in valid_modes:
            if raise_error:
                raise ValueError(f"Invalid search mode: {mode}. Must be one of {valid_modes}")
            return False

        # Validate limit
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
        """
        Validate embedding model name

        Args:
            model_name: Model name or key
            raise_error: If True, raises ValueError on invalid model

        Returns:
            True if model is valid

        Raises:
            ValueError: If model is invalid and raise_error is True
        """
        if not model_name:
            if raise_error:
                raise ValueError("Model name cannot be empty")
            return False

        # Check if it's a known model key
        if model_name in AppConfig.AVAILABLE_EMBEDDING_MODELS:
            return True

        # Check if it's a full model name
        for key, info in AppConfig.AVAILABLE_EMBEDDING_MODELS.items():
            if model_name == info['full_name']:
                return True

        # Custom model - accept it but log warning
        logger.warning(f"Using custom embedding model: {model_name}")
        return True

    @staticmethod
    def validate_context_lines(context: int, raise_error: bool = True) -> bool:
        """
        Validate context lines parameter

        Args:
            context: Number of context lines before/after results
            raise_error: If True, raises ValueError on invalid value

        Returns:
            True if context value is valid

        Raises:
            ValueError: If context is invalid and raise_error is True
        """
        if context < 0:
            if raise_error:
                raise ValueError("Context lines cannot be negative")
            return False

        if context > 100:
            if raise_error:
                raise ValueError("Context lines cannot exceed 100")
            return False

        return True
