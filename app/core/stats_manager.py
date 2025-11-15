from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager


class StatsManager:
    """Centralized statistics management for CLI"""

    @staticmethod
    def get_database_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get database statistics for a project

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            Dictionary containing database stats
        """
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        vector_db = VectorDatabase(project_path=project_path)
        db_stats = vector_db.get_stats()

        return {
            'db_path': db_stats.get('db_path', 'N/A'),
            'table_name': db_stats.get('table_name', 'N/A'),
            'total_chunks': db_stats.get('count', 0)
        }

    @staticmethod
    def get_project_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get project metadata and statistics

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            Dictionary containing project stats
        """
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        project_manager = ProjectManager()
        stats = project_manager.get_project_stats(project_path)

        return {
            'name': stats.get('name'),
            'path': project_path,
            'hash': AppConfig.get_project_hash(project_path),
            'indexed_at': stats.get('indexed_at')
        }

    @staticmethod
    def get_model_info(project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get embedding model information for a project

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            Dictionary containing model info
        """
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        metadata = AppConfig.load_project_metadata(project_path)
        current_model = AppConfig.get_embedding_model()
        indexed_model = metadata.get("embedding_model")

        return {
            'current_model': current_model,
            'indexed_model': indexed_model,
            'schema_version': metadata.get("schema_version", "1.0")
        }

    @staticmethod
    def get_full_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete statistics including database, project and model info

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            Dictionary containing all statistics
        """
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        return {
            'project': StatsManager.get_project_stats(project_path),
            'database': StatsManager.get_database_stats(project_path),
            'model': StatsManager.get_model_info(project_path),
            'version': {
                'app_version': AppConfig.APP_VERSION,
                'schema_version': AppConfig.SCHEMA_VERSION
            }
        }
