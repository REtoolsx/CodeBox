import os
import hashlib
from pathlib import Path
from typing import Optional
import json


class ConfigMeta(type):
    _property_names = {
        'APP_NAME', 'APP_VERSION', 'DB_TABLE_NAME', 'DEFAULT_CHUNK_SIZE',
        'DEFAULT_CHUNK_OVERLAP', 'MAX_FILE_SIZE', 'DEFAULT_SEARCH_LIMIT',
        'RRF_K', 'CLI_CONTENT_PREVIEW_LENGTH', 'CLI_MAX_CONTENT_LENGTH',
        'EMBEDDING_MODEL', 'EMBEDDING_DIM', 'AVAILABLE_EMBEDDING_MODELS',
        'AUTO_SYNC_ENABLED', 'AUTO_SYNC_DEBOUNCE_SECONDS', 'AUTO_SYNC_BATCH_SIZE',
        'DEFAULT_IGNORE_PATTERNS', 'EMBEDDING_BATCH_SIZE'
    }

    def __getattribute__(cls, name):
        if name in ConfigMeta._property_names:
            cls.ensure_config_loaded()
            return type.__getattribute__(cls, f'_{name}')
        return type.__getattribute__(cls, name)

    def __setattr__(cls, name, value):
        if name in ConfigMeta._property_names:
            type.__setattr__(cls, f'_{name}', value)
        else:
            type.__setattr__(cls, name, value)


class AppConfig(metaclass=ConfigMeta):
    HOME_DIR = Path.home() / ".codebox"
    PROJECTS_DIR = HOME_DIR / "projects"

    _APP_NAME = "CodeBox - Your Project & LLM Friend"
    _APP_VERSION = "2.2.0"
    _DB_TABLE_NAME = "code_chunks"
    _CLI_CONTENT_PREVIEW_LENGTH = 200
    _CLI_MAX_CONTENT_LENGTH = 5000

    _AUTO_SYNC_ENABLED = False
    _AUTO_SYNC_DEBOUNCE_SECONDS = 2.0
    _AUTO_SYNC_BATCH_SIZE = 10

    _EMBEDDING_DIM = 384
    _EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    _EMBEDDING_BATCH_SIZE = 100

    _AVAILABLE_EMBEDDING_MODELS = {
        "all-MiniLM-L6-v2": {
            "full_name": "sentence-transformers/all-MiniLM-L6-v2",
            "dim": 384,
            "description": "Fast & lightweight (default)"
        },
        "all-mpnet-base-v2": {
            "full_name": "sentence-transformers/all-mpnet-base-v2",
            "dim": 768,
            "description": "Better quality, slower"
        },
        "codebert-base": {
            "full_name": "microsoft/codebert-base",
            "dim": 768,
            "description": "Code-optimized BERT"
        },
        "graphcodebert-base": {
            "full_name": "microsoft/graphcodebert-base",
            "dim": 768,
            "description": "Graph-aware code model"
        },
        "bge-small-en-v1.5": {
            "full_name": "BAAI/bge-small-en-v1.5",
            "dim": 384,
            "description": "Modern general-purpose model"
        }
    }

    EXTENSION_BLACKLIST = [
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
        ".mp3", ".wav", ".flac", ".aac", ".ogg",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".exe", ".dll", ".so", ".dylib", ".bin",
        ".lock", ".log", ".tmp", ".cache", ".swp"
    ]

    PATH_BLACKLIST = [
        "node_modules",
        "__pycache__",
        "venv",
        "env",
        "dist",
        "build",
        "migrations",
        "test_data",
        "vendor",
        "coverage",
        "htmlcov"
    ]

    _DEFAULT_IGNORE_PATTERNS = EXTENSION_BLACKLIST + PATH_BLACKLIST

    PROFILE_THRESHOLD_MEDIUM_MAX = 5000

    PROFILES = {
        "medium": {
            "description": "Medium projects (< 5000 files)",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "max_file_size": 1048576,
            "search_limit": 50,
            "rrf_k": 60,
            "embedding_model": "all-MiniLM-L6-v2",
            "preview_length": 200,
            "embedding_batch_size": 100
        },
        "large": {
            "description": "Large projects (> 5000 files)",
            "chunk_size": 1024,
            "chunk_overlap": 100,
            "max_file_size": 2097152,
            "search_limit": 100,
            "rrf_k": 80,
            "embedding_model": "all-mpnet-base-v2",
            "preview_length": 300,
            "embedding_batch_size": 50
        }
    }

    _DEFAULT_CHUNK_SIZE = None
    _DEFAULT_CHUNK_OVERLAP = None
    _MAX_FILE_SIZE = None
    _DEFAULT_SEARCH_LIMIT = None
    _RRF_K = None

    _current_project_path = None
    _config_loaded = False
    _active_profile = "auto"

    @classmethod
    def init_directories(cls):
        cls.HOME_DIR.mkdir(exist_ok=True, parents=True)
        cls.PROJECTS_DIR.mkdir(exist_ok=True, parents=True)

    @classmethod
    def get_project_hash(cls, project_path: str) -> str:
        normalized = str(Path(project_path).resolve())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @classmethod
    def get_project_dir(cls, project_path: str) -> Path:
        project_hash = cls.get_project_hash(project_path)
        return cls.PROJECTS_DIR / project_hash

    @classmethod
    def get_project_data_dir(cls, project_path: str) -> Path:
        return cls.get_project_dir(project_path) / ".lancedb"

    @classmethod
    def get_project_metadata_file(cls, project_path: str) -> Path:
        return cls.get_project_dir(project_path) / "metadata.json"

    @classmethod
    def get_current_working_project(cls) -> Optional[str]:
        return str(Path.cwd().resolve())

    @classmethod
    def register_project(cls, project_path: str, name: Optional[str] = None):
        resolved_path = str(Path(project_path).resolve())
        metadata = {
            "path": resolved_path,
            "name": name or Path(resolved_path).name,
            "indexed_at": None
        }
        cls.save_project_metadata(project_path, metadata)

    @classmethod
    def get_all_projects(cls) -> dict:
        projects = {}
        if not cls.PROJECTS_DIR.exists():
            return projects

        for project_dir in cls.PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                metadata = cls.load_project_metadata_by_hash(project_dir.name)
                if metadata:
                    projects[project_dir.name] = metadata

        return projects

    @classmethod
    def load_project_metadata(cls, project_path: str) -> dict:
        metadata_file = cls.get_project_metadata_file(project_path)
        if not metadata_file.exists():
            return {}

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def load_project_metadata_by_hash(cls, project_hash: str) -> dict:
        metadata_file = cls.PROJECTS_DIR / project_hash / "metadata.json"
        if not metadata_file.exists():
            return {}

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def save_project_metadata(cls, project_path: str, metadata: dict):
        try:
            project_dir = cls.get_project_dir(project_path)
            project_dir.mkdir(exist_ok=True, parents=True)

            metadata_file = cls.get_project_metadata_file(project_path)
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise

    @classmethod
    def get_embedding_model(cls) -> str:
        return cls._EMBEDDING_MODEL

    @classmethod
    def set_embedding_model(cls, model_name: str):
        pass

    @classmethod
    def get_embedding_model_info(cls, model_key: str) -> Optional[dict]:
        return cls._AVAILABLE_EMBEDDING_MODELS.get(model_key)

    @staticmethod
    def get_language_display_name(lang_code: str) -> str:
        return lang_code.replace('_', ' ').title()

    @staticmethod
    def get_language_code_from_display(display_name: str) -> str:
        return display_name.lower().replace(' ', '_')

    @classmethod
    def ensure_config_loaded(cls, project_path: str = None, profile: str = "auto"):
        if not project_path:
            project_path = str(Path.cwd().resolve())

        if not cls._config_loaded or cls._current_project_path != project_path or cls._active_profile != profile:
            cls._current_project_path = project_path
            cls._active_profile = profile
            cls.apply_profile(profile, project_path)
            cls._config_loaded = True

    @classmethod
    def detect_profile(cls, project_path: str) -> str:
        try:
            from app.core.file_filters import should_index_file

            project_dir = Path(project_path)
            file_count = 0

            for file_path in project_dir.rglob('*'):
                if file_path.is_file() and should_index_file(str(file_path), str(project_dir)):
                    file_count += 1

            return "medium" if file_count <= cls.PROFILE_THRESHOLD_MEDIUM_MAX else "large"

        except Exception:
            return "medium"

    @classmethod
    def apply_profile(cls, profile_name: str, project_path: str):
        cls._current_project_path = project_path

        active_profile = profile_name
        if profile_name == "auto":
            active_profile = cls.detect_profile(project_path)

        profile_settings = cls.PROFILES.get(active_profile, cls.PROFILES.get("medium", {}))

        cls._DEFAULT_CHUNK_SIZE = profile_settings.get("chunk_size", 512)
        cls._DEFAULT_CHUNK_OVERLAP = profile_settings.get("chunk_overlap", 50)
        cls._MAX_FILE_SIZE = profile_settings.get("max_file_size", 1048576)
        cls._DEFAULT_SEARCH_LIMIT = profile_settings.get("search_limit", 50)
        cls._RRF_K = profile_settings.get("rrf_k", 60)
        cls._CLI_CONTENT_PREVIEW_LENGTH = profile_settings.get("preview_length", cls._CLI_CONTENT_PREVIEW_LENGTH)
        cls._EMBEDDING_BATCH_SIZE = profile_settings.get("embedding_batch_size", 100)

    @classmethod
    def get_active_profile(cls, project_path: str) -> str:
        if cls._active_profile == "auto":
            return cls.detect_profile(project_path)
        return cls._active_profile

    @classmethod
    def get_ignore_config(cls, project_path: str = None) -> dict:
        return {
            'extension_blacklist': cls.EXTENSION_BLACKLIST,
            'path_blacklist': cls.PATH_BLACKLIST
        }
