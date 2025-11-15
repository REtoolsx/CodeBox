from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProjectContext:
    path: str
    name: str
    hash: str
    exists: bool
    is_indexed: bool
    indexed_at: Optional[str]
    metadata: dict


class ProjectContextManager:

    def __init__(self, project_path: Optional[str] = None):
        self.project_manager = ProjectManager()

        if project_path is None:
            self.project_path = self.project_manager.get_current_project_path()
        else:
            self.project_path = str(Path(project_path).resolve())

    def get_context(self) -> ProjectContext:
        path_obj = Path(self.project_path)
        exists = path_obj.exists() and path_obj.is_dir()

        project_stats = self.project_manager.get_project_stats(self.project_path)
        metadata = AppConfig.load_project_metadata(self.project_path)

        is_indexed = project_stats.get('indexed_at') is not None

        return ProjectContext(
            path=self.project_path,
            name=project_stats.get('name', path_obj.name),
            hash=AppConfig.get_project_hash(self.project_path),
            exists=exists,
            is_indexed=is_indexed,
            indexed_at=project_stats.get('indexed_at'),
            metadata=metadata
        )

    def ensure_project_ready(self) -> None:
        path_obj = Path(self.project_path)

        if not path_obj.exists():
            raise ValueError(f"Project path does not exist: {self.project_path}")

        if not path_obj.is_dir():
            raise ValueError(f"Project path is not a directory: {self.project_path}")

        self.project_manager.ensure_project_directories(self.project_path)

        all_projects = AppConfig.get_all_projects()
        project_hash = AppConfig.get_project_hash(self.project_path)

        if project_hash not in all_projects:
            AppConfig.register_project(self.project_path, path_obj.name)
            logger.info(f"Registered new project: {self.project_path}")

    def update_index_time(self) -> None:
        self.project_manager.update_project_index_time(self.project_path)

    def get_database_path(self) -> Path:
        return AppConfig.get_project_data_dir(self.project_path)

    def get_metadata_path(self) -> Path:
        return AppConfig.get_project_metadata_file(self.project_path)

    @staticmethod
    def get_current_project_path() -> str:
        return str(Path.cwd().resolve())

    @staticmethod
    def validate_project_path(path: str) -> bool:
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir()
        except Exception:
            return False
