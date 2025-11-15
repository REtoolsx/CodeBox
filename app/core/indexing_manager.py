from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from app.utils.config import AppConfig
from app.core.project_context import ProjectContextManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IndexingContext:
    """Prepared context for indexing operation"""
    project_path: str
    languages: List[str]
    project_name: str


class IndexingManager:
    """Centralized indexing workflow management for CLI"""

    @staticmethod
    def prepare_indexing(
        project_path: Optional[str] = None,
        languages: Optional[List[str]] = None
    ) -> IndexingContext:
        """
        Prepare and validate indexing operation

        Args:
            project_path: Project directory path (None uses current directory)
            languages: List of languages to index (None uses all supported)

        Returns:
            IndexingContext with validated project and language info

        Raises:
            ValueError: If project path is invalid or no languages selected
        """
        # Initialize project context
        project_ctx = ProjectContextManager(project_path)

        # Validate and prepare project
        project_ctx.ensure_project_ready()

        validated_path = project_ctx.project_path

        # Validate and prepare languages
        if not languages:
            languages = list(AppConfig.SUPPORTED_LANGUAGES.keys())

        # Filter to only supported languages
        supported_langs = set(AppConfig.SUPPORTED_LANGUAGES.keys())
        valid_languages = [lang for lang in languages if lang in supported_langs]

        if not valid_languages:
            raise ValueError("No valid languages selected for indexing")

        # Save enabled languages to config
        AppConfig.set_enabled_languages(valid_languages)

        logger.info(f"Indexing prepared for: {validated_path}")
        logger.info(f"Languages: {', '.join(valid_languages)}")

        # Get project name
        context = project_ctx.get_context()

        return IndexingContext(
            project_path=validated_path,
            languages=valid_languages,
            project_name=context.name
        )

    @staticmethod
    def finalize_indexing(project_path: str, success: bool = True) -> None:
        """
        Finalize indexing operation and update metadata

        Args:
            project_path: Project directory path
            success: Whether indexing completed successfully
        """
        if not success:
            logger.warning(f"Indexing failed for: {project_path}")
            return

        try:
            # Update index time in project metadata
            project_ctx = ProjectContextManager(project_path)
            project_ctx.update_index_time()

            logger.info(f"Indexing finalized for: {project_path}")

        except Exception as e:
            logger.error(f"Failed to finalize indexing: {str(e)}")
            raise
