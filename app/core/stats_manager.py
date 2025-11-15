from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager


class StatsManager:

    @staticmethod
    def get_database_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
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
    def get_language_breakdown(project_path: Optional[str] = None) -> Dict[str, int]:
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        vector_db = VectorDatabase(project_path=project_path)
        return vector_db.get_language_breakdown()

    @staticmethod
    def get_advanced_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        vector_db = VectorDatabase(project_path=project_path)
        language_breakdown = vector_db.get_language_breakdown()
        chunk_type_breakdown = vector_db.get_chunk_type_breakdown()
        db_size_mb = vector_db.get_database_size_mb()
        db_stats = vector_db.get_stats()
        total_chunks = db_stats.get('count', 0)

        total_files = sum(language_breakdown.values()) if language_breakdown else 0
        avg_chunks_per_file = (total_chunks / total_files) if total_files > 0 else 0

        return {
            'total_chunks': total_chunks,
            'total_files': total_files,
            'avg_chunks_per_file': round(avg_chunks_per_file, 2),
            'language_breakdown': language_breakdown,
            'chunk_type_breakdown': chunk_type_breakdown,
            'database_size_mb': db_size_mb
        }

    @staticmethod
    def get_project_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
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
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        metadata = AppConfig.load_project_metadata(project_path)
        current_model = AppConfig.get_embedding_model()
        indexed_model = metadata.get("embedding_model")

        return {
            'current_model': current_model,
            'indexed_model': indexed_model
        }

    @staticmethod
    def get_full_stats(project_path: Optional[str] = None) -> Dict[str, Any]:
        if project_path is None:
            project_manager = ProjectManager()
            project_path = project_manager.get_current_project_path()

        return {
            'project': StatsManager.get_project_stats(project_path),
            'database': StatsManager.get_database_stats(project_path),
            'model': StatsManager.get_model_info(project_path),
            'version': {
                'app_version': AppConfig.APP_VERSION
            }
        }
