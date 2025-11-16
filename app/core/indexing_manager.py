from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from app.utils.config import AppConfig
from app.core.project_context import ProjectContextManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IndexingContext:
    project_path: str
    project_name: str


class IndexingManager:

    @staticmethod
    def prepare_indexing(
        project_path: Optional[str] = None
    ) -> IndexingContext:
        project_ctx = ProjectContextManager(project_path)

        project_ctx.ensure_project_ready()

        validated_path = project_ctx.project_path

        logger.info(f"Indexing prepared for: {validated_path}")

        context = project_ctx.get_context()

        return IndexingContext(
            project_path=validated_path,
            project_name=context.name
        )

    @staticmethod
    def finalize_indexing(project_path: str, success: bool = True) -> None:
        if not success:
            logger.warning(f"Indexing failed for: {project_path}")
            return

        try:
            project_ctx = ProjectContextManager(project_path)
            project_ctx.update_index_time()

            logger.info(f"Indexing finalized for: {project_path}")

        except Exception as e:
            logger.error(f"Failed to finalize indexing: {str(e)}")
            raise
