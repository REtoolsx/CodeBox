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
    project_name: str


class IndexingManager:
    """Centralized indexing workflow management for CLI"""

    @staticmethod
    def prepare_indexing(
        project_path: Optional[str] = None
    ) -> IndexingContext:
        """
        Prepare and validate indexing operation

        Args:
            project_path: Project directory path (None uses current directory)

        Returns:
            IndexingContext with validated project info

        Raises:
            ValueError: If project path is invalid
        """
        # Initialize project context
        project_ctx = ProjectContextManager(project_path)

        # Validate and prepare project
        project_ctx.ensure_project_ready()

        validated_path = project_ctx.project_path

        logger.info(f"Indexing prepared for: {validated_path}")
        logger.info(f"Auto-detecting all supported languages")

        # Get project name
        context = project_ctx.get_context()

        return IndexingContext(
            project_path=validated_path,
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
