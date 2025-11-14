from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from app.utils.config import AppConfig


class ProjectManager:
    def __init__(self, cli_mode: bool = False):
        self.cli_mode = cli_mode
        self._current_project_path: Optional[str] = None

    def get_current_project_path(self) -> Optional[str]:
        if self.cli_mode:
            return AppConfig.get_current_working_project()
        else:
            return self._current_project_path

    def set_current_project(self, project_path: str):
        if not self.cli_mode:
            resolved = str(Path(project_path).resolve())
            self._current_project_path = resolved

            if not self.is_project_registered(resolved):
                AppConfig.register_project(resolved)

    def is_project_registered(self, project_path: str) -> bool:
        project_hash = AppConfig.get_project_hash(project_path)
        projects = AppConfig.get_all_projects()
        return project_hash in projects

    def get_project_info(self, project_path: str) -> Dict:
        project_hash = AppConfig.get_project_hash(project_path)
        projects = AppConfig.get_all_projects()

        if project_hash in projects:
            return projects[project_hash]

        return {
            "path": str(Path(project_path).resolve()),
            "name": Path(project_path).name,
            "indexed_at": None
        }

    def list_all_projects(self) -> Dict[str, Dict]:
        return AppConfig.get_all_projects()

    def update_project_index_time(self, project_path: str):
        config = AppConfig.load_global_config()
        project_hash = AppConfig.get_project_hash(project_path)

        if "projects" not in config:
            config["projects"] = {}

        if project_hash in config["projects"]:
            config["projects"][project_hash]["indexed_at"] = datetime.now().isoformat()
        else:
            resolved = str(Path(project_path).resolve())
            config["projects"][project_hash] = {
                "path": resolved,
                "name": Path(resolved).name,
                "indexed_at": datetime.now().isoformat()
            }

        AppConfig.save_global_config(config)

    def get_project_data_dir(self, project_path: Optional[str] = None) -> Path:
        if project_path is None:
            project_path = self.get_current_project_path()

        if project_path is None:
            raise ValueError("No project path specified")

        return AppConfig.get_project_data_dir(project_path)

    def ensure_project_directories(self, project_path: Optional[str] = None):
        if project_path is None:
            project_path = self.get_current_project_path()

        if project_path is None:
            raise ValueError("No project path specified")

        project_dir = AppConfig.get_project_dir(project_path)
        project_dir.mkdir(exist_ok=True, parents=True)

        data_dir = AppConfig.get_project_data_dir(project_path)
        data_dir.mkdir(exist_ok=True, parents=True)

    def get_project_stats(self, project_path: Optional[str] = None) -> Dict:
        if project_path is None:
            project_path = self.get_current_project_path()

        if project_path is None:
            return {}

        metadata = AppConfig.load_project_metadata(project_path)
        info = self.get_project_info(project_path)

        return {
            "path": project_path,
            "name": info.get("name", Path(project_path).name),
            "indexed_at": info.get("indexed_at"),
            "metadata": metadata
        }
