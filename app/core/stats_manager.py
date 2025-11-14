from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.search.vector_db import VectorDatabase
from app.utils.config import AppConfig
from app.utils.project_manager import ProjectManager


class StatsManager:
    """Centralized statistics management for both CLI and GUI"""

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

    @staticmethod
    def format_stats_html(project_path: Optional[str] = None) -> str:
        """
        Format statistics as HTML for GUI display (database only)

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            HTML formatted statistics string
        """
        try:
            db_stats = StatsManager.get_database_stats(project_path)

            return f"""
<b>Database Location:</b> {db_stats['db_path']}<br>
<b>Table Name:</b> {db_stats['table_name']}<br>
<b>Total Chunks:</b> {db_stats['total_chunks']:,}<br>
            """
        except Exception as e:
            return f"Error loading stats: {str(e)}"

    @staticmethod
    def format_full_stats_html(project_path: Optional[str] = None) -> str:
        """
        Format complete statistics as HTML for GUI display
        Includes project info, database stats, model info, and version

        Args:
            project_path: Project path (if None, uses current project)

        Returns:
            HTML formatted complete statistics string
        """
        try:
            stats = StatsManager.get_full_stats(project_path)
            project = stats['project']
            database = stats['database']
            model = stats['model']
            version = stats['version']

            # Format indexed time
            indexed_at = project.get('indexed_at')
            if indexed_at:
                try:
                    dt = datetime.fromisoformat(indexed_at)
                    indexed_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    indexed_display = indexed_at
            else:
                indexed_display = "Never"

            # Format model names
            indexed_model = model.get('indexed_model', 'Unknown')
            current_model = model.get('current_model', 'Unknown')

            # Model mismatch warning
            model_warning = ""
            if indexed_model != current_model and indexed_model != 'Unknown':
                model_warning = '<br><span style="color: #d9534f;">⚠ Model mismatch detected!</span>'

            return f"""
<h3 style="margin-top: 0;">Project Information</h3>
<b>Name:</b> {project.get('name', 'Unknown')}<br>
<b>Path:</b> {project.get('path', 'N/A')}<br>
<b>Last Indexed:</b> {indexed_display}<br>

<h3>Database Statistics</h3>
<b>Location:</b> {database['db_path']}<br>
<b>Table Name:</b> {database['table_name']}<br>
<b>Total Chunks:</b> {database['total_chunks']:,}<br>

<h3>Embedding Model</h3>
<b>Indexed With:</b> {indexed_model}<br>
<b>Current Model:</b> {current_model}{model_warning}<br>

<h3>Version Information</h3>
<b>App Version:</b> {version['app_version']}<br>
<b>Schema Version:</b> {version['schema_version']}<br>
            """
        except Exception as e:
            return f"Error loading stats: {str(e)}"
