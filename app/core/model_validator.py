from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelValidationResult:
    """Result of model validation check"""
    is_valid: bool
    has_mismatch: bool
    indexed_model: Optional[str]
    current_model: Optional[str]
    warning_message: Optional[str]


class ModelValidator:
    """Centralized model validation for search operations"""

    @staticmethod
    def _normalize_model_name(model_name: Optional[str]) -> Optional[str]:
        """
        Normalize model name to full format for comparison

        Args:
            model_name: Model name (short or full)

        Returns:
            Normalized full model name
        """
        if not model_name:
            return None

        # Check if it's a known model key
        model_info = AppConfig.get_embedding_model_info(model_name)
        if model_info:
            return model_info['full_name']

        # Check if it's already a full name by looking through all models
        for key, info in AppConfig.AVAILABLE_EMBEDDING_MODELS.items():
            if model_name == info['full_name']:
                return model_name
            if model_name == key:
                return info['full_name']

        # Custom model or unknown - return as is
        return model_name

    @staticmethod
    def validate_search_models(project_path: str) -> ModelValidationResult:
        """
        Validate that indexed model matches current search model

        Args:
            project_path: Path to the project

        Returns:
            ModelValidationResult with validation details
        """
        metadata = AppConfig.load_project_metadata(project_path)
        indexed_model = metadata.get("embedding_model")
        current_model = AppConfig.get_embedding_model()

        # Normalize both models for comparison
        normalized_indexed = ModelValidator._normalize_model_name(indexed_model)
        normalized_current = ModelValidator._normalize_model_name(current_model)

        has_mismatch = bool(
            normalized_indexed and
            normalized_current and
            normalized_indexed != normalized_current
        )
        warning_message = None

        if has_mismatch:
            warning_message = (
                f"Warning: Index was created with '{indexed_model}' "
                f"but searching with '{current_model}'. "
                f"Results may be suboptimal."
            )
            logger.warning(warning_message)

        is_valid = not has_mismatch

        return ModelValidationResult(
            is_valid=is_valid,
            has_mismatch=has_mismatch,
            indexed_model=indexed_model,
            current_model=current_model,
            warning_message=warning_message
        )

    @staticmethod
    def should_reindex_on_model_change(old_model: str, new_model: str) -> bool:
        """
        Check if re-indexing is needed when model changes

        Args:
            old_model: Previous model name
            new_model: New model name

        Returns:
            True if re-indexing is required
        """
        return old_model != new_model

    @staticmethod
    def get_model_display_name(model_name: Optional[str]) -> str:
        """
        Get user-friendly display name for a model

        Args:
            model_name: Model name/path

        Returns:
            Display name for the model
        """
        if not model_name:
            return "Unknown"

        # Check if it's a known model
        for key, info in AppConfig.AVAILABLE_EMBEDDING_MODELS.items():
            if model_name == info['full_name'] or model_name == key:
                return f"{key} ({info['description']})"

        # Custom model
        return model_name

    @staticmethod
    def format_model_info_for_display(
        indexed_model: Optional[str],
        current_model: Optional[str]
    ) -> str:
        """
        Format model information for user display

        Args:
            indexed_model: Model used for indexing
            current_model: Model used for searching

        Returns:
            Formatted string for display
        """
        indexed_display = ModelValidator.get_model_display_name(indexed_model)
        current_display = ModelValidator.get_model_display_name(current_model)

        if indexed_model == current_model:
            return f"Model: {indexed_display}"
        else:
            return f"Model: {indexed_display} (indexed) | {current_display} (searching)"

    @staticmethod
    def format_model_info_for_json(validation: ModelValidationResult) -> Dict[str, Any]:
        # Normalize both model names to full format for consistent display
        indexed_full = ModelValidator._normalize_model_name(validation.indexed_model) or "unknown"
        current_full = ModelValidator._normalize_model_name(validation.current_model)

        info = {
            "indexed_with": indexed_full,
            "searching_with": current_full
        }

        if validation.warning_message:
            info["mismatch_warning"] = validation.warning_message

        return info
