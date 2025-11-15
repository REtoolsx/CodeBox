import os
import hashlib
from pathlib import Path
from typing import Optional
import json


class AppConfig:
    HOME_DIR = Path.home() / ".codebox"
    GLOBAL_CONFIG_FILE = HOME_DIR / "config.json"
    PROJECTS_DIR = HOME_DIR / "projects"

    APP_NAME = None
    APP_VERSION = None
    DB_TABLE_NAME = None
    DEFAULT_CHUNK_SIZE = None
    DEFAULT_CHUNK_OVERLAP = None
    MAX_FILE_SIZE = None
    DEFAULT_SEARCH_LIMIT = None
    RRF_K = None
    CLI_CONTENT_PREVIEW_LENGTH = None
    CLI_MAX_CONTENT_LENGTH = None
    EMBEDDING_MODEL = None
    EMBEDDING_DIM = None
    AVAILABLE_EMBEDDING_MODELS = None
    AUTO_SYNC_ENABLED = None
    AUTO_SYNC_DEBOUNCE_SECONDS = None
    AUTO_SYNC_BATCH_SIZE = None
    DEFAULT_IGNORE_PATTERNS = None
    EMBEDDING_BATCH_SIZE = None  # Aşama 3: Memory Optimization

    _current_project_path = None
    _config_loaded = False

    @classmethod
    def get_auto_sync_enabled(cls) -> bool:
        if cls.AUTO_SYNC_ENABLED is None:
            cls.ensure_config_loaded()
        config = cls.load_global_config()
        return config.get('auto_sync_enabled', cls.AUTO_SYNC_ENABLED)

    @classmethod
    def set_auto_sync_enabled(cls, enabled: bool):
        config = cls.load_global_config()
        config['auto_sync_enabled'] = enabled
        cls.save_global_config(config)
        cls.AUTO_SYNC_ENABLED = enabled

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
    def load_global_config(cls) -> dict:
        if not cls.GLOBAL_CONFIG_FILE.exists():
            return {"projects": {}}

        try:
            with open(cls.GLOBAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config if isinstance(config, dict) else {"projects": {}}
        except Exception:
            return {"projects": {}}

    @classmethod
    def save_global_config(cls, config: dict):
        try:
            cls.HOME_DIR.mkdir(exist_ok=True, parents=True)
            with open(cls.GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise

    @classmethod
    def register_project(cls, project_path: str, name: Optional[str] = None):
        config = cls.load_global_config()
        if "projects" not in config:
            config["projects"] = {}

        project_hash = cls.get_project_hash(project_path)
        resolved_path = str(Path(project_path).resolve())

        config["projects"][project_hash] = {
            "path": resolved_path,
            "name": name or Path(resolved_path).name,
            "indexed_at": None
        }

        cls.save_global_config(config)

    @classmethod
    def get_all_projects(cls) -> dict:
        config = cls.load_global_config()
        return config.get("projects", {})

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
    def get_embedding_model(cls) -> Optional[str]:
        config = cls.load_global_config()
        return config.get('embedding_model', None)

    @classmethod
    def set_embedding_model(cls, model_name: str):
        config = cls.load_global_config()
        config['embedding_model'] = model_name
        cls.save_global_config(config)

    @classmethod
    def get_embedding_model_info(cls, model_key: str) -> Optional[dict]:
        if not cls.AVAILABLE_EMBEDDING_MODELS:
            cls.ensure_config_loaded()
        return cls.AVAILABLE_EMBEDDING_MODELS.get(model_key) if cls.AVAILABLE_EMBEDDING_MODELS else None

    @classmethod
    def load_indexing_settings(cls):
        config = cls.load_global_config()
        settings = config.get('indexing_settings', {})

        cls.DEFAULT_CHUNK_SIZE = settings.get('chunk_size', 512)
        cls.DEFAULT_CHUNK_OVERLAP = settings.get('chunk_overlap', 50)
        cls.MAX_FILE_SIZE = settings.get('max_file_size', 1024 * 1024)

    @classmethod
    def save_indexing_settings(cls, chunk_size: int, chunk_overlap: int, max_file_size: int):
        config = cls.load_global_config()

        config['indexing_settings'] = {
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap,
            'max_file_size': max_file_size
        }

        cls.save_global_config(config)

        cls.DEFAULT_CHUNK_SIZE = chunk_size
        cls.DEFAULT_CHUNK_OVERLAP = chunk_overlap
        cls.MAX_FILE_SIZE = max_file_size

    @classmethod
    def load_search_settings(cls):
        config = cls.load_global_config()
        settings = config.get('search_settings', {})

        cls.DEFAULT_SEARCH_LIMIT = settings.get('search_limit', 50)
        cls.RRF_K = settings.get('rrf_k', 60)

    @classmethod
    def save_search_settings(cls, search_limit: int, rrf_k: int):
        config = cls.load_global_config()

        config['search_settings'] = {
            'search_limit': search_limit,
            'rrf_k': rrf_k
        }

        cls.save_global_config(config)

        cls.DEFAULT_SEARCH_LIMIT = search_limit
        cls.RRF_K = rrf_k

    @classmethod
    def get_indexing_settings(cls) -> dict:
        config = cls.load_global_config()
        return config.get('indexing_settings', {
            'chunk_size': cls.DEFAULT_CHUNK_SIZE,
            'chunk_overlap': cls.DEFAULT_CHUNK_OVERLAP,
            'max_file_size': cls.MAX_FILE_SIZE
        })

    @classmethod
    def get_search_settings(cls) -> dict:
        config = cls.load_global_config()
        return config.get('search_settings', {
            'search_limit': cls.DEFAULT_SEARCH_LIMIT,
            'rrf_k': cls.RRF_K
        })

    @staticmethod
    def get_language_display_name(lang_code: str) -> str:
        return lang_code.replace('_', ' ').title()

    @staticmethod
    def get_language_code_from_display(display_name: str) -> str:
        return display_name.lower().replace(' ', '_')

    @classmethod
    def _load_base_config(cls, config: dict):
        app_config = config.get("app", {})
        cls.APP_NAME = app_config.get("name", "CodeBox")
        cls.APP_VERSION = app_config.get("version", "1.0.0")
        cls.CLI_CONTENT_PREVIEW_LENGTH = app_config.get("cli_preview_length", 200)
        cls.CLI_MAX_CONTENT_LENGTH = app_config.get("cli_max_content_length", 5000)

        db_config = config.get("database", {})
        cls.DB_TABLE_NAME = db_config.get("table_name", "code_chunks")

        auto_sync_config = config.get("auto_sync", {})
        cls.AUTO_SYNC_ENABLED = auto_sync_config.get("enabled", False)
        cls.AUTO_SYNC_DEBOUNCE_SECONDS = auto_sync_config.get("debounce_seconds", 2.0)
        cls.AUTO_SYNC_BATCH_SIZE = auto_sync_config.get("batch_size", 10)

        embedding_config = config.get("embedding", {})
        cls.EMBEDDING_DIM = embedding_config.get("default_dim", 384)
        cls.AVAILABLE_EMBEDDING_MODELS = embedding_config.get("available_models", {})

        ignore_config = config.get("ignore", {})
        path_blacklist = ignore_config.get("path_blacklist", [])
        extension_blacklist = ignore_config.get("extension_blacklist", [])
        cls.DEFAULT_IGNORE_PATTERNS = path_blacklist + extension_blacklist

        cls._config_loaded = True

    @classmethod
    def ensure_config_loaded(cls, project_path: str = None):
        if not project_path:
            project_path = str(Path.cwd().resolve())

        if not cls._config_loaded or cls._current_project_path != project_path:
            cls._current_project_path = project_path
            config = cls.load_project_config(project_path)

            if not config:
                cls.create_default_config(project_path)
                config = cls.load_project_config(project_path)

            if config:
                cls._load_base_config(config)
                active_profile = config.get("active_profile", "auto")
                if active_profile == "auto":
                    active_profile = cls.detect_profile(project_path, config)

                profiles = config.get("profiles", {})
                profile_settings = profiles.get(active_profile, profiles.get("medium", {}))

                cls.DEFAULT_CHUNK_SIZE = profile_settings.get("chunk_size", 512)
                cls.DEFAULT_CHUNK_OVERLAP = profile_settings.get("chunk_overlap", 50)
                cls.MAX_FILE_SIZE = profile_settings.get("max_file_size", 1048576)
                cls.DEFAULT_SEARCH_LIMIT = profile_settings.get("search_limit", 50)
                cls.RRF_K = profile_settings.get("rrf_k", 60)
                cls.CLI_CONTENT_PREVIEW_LENGTH = profile_settings.get("preview_length", cls.CLI_CONTENT_PREVIEW_LENGTH)
                cls.EMBEDDING_BATCH_SIZE = profile_settings.get("embedding_batch_size", 100)  # Aşama 3

    @classmethod
    def load_project_config(cls, project_path: str) -> Optional[dict]:
        config_path = Path(project_path) / ".codebox.config.json"
        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    @classmethod
    def create_default_config(cls, project_path: str) -> bool:
        config_path = Path(project_path) / ".codebox.config.json"
        if config_path.exists():
            return False

        default_config = {
            "active_profile": "auto",
            "app": {
                "name": "CodeBox - Your Project & LLM Friend",
                "version": "2.2.0",
                "cli_preview_length": 200,
                "cli_max_content_length": 5000
            },
            "database": {
                "table_name": "code_chunks"
            },
            "auto_sync": {
                "enabled": False,
                "debounce_seconds": 2.0,
                "batch_size": 10
            },
            "embedding": {
                "default_dim": 384,
                "available_models": {
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
            },
            "ignore": {
                "extension_blacklist": [
                    ".zip", ".tar", ".gz", ".rar", ".7z",
                    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
                    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
                    ".mp3", ".wav", ".flac", ".aac", ".ogg",
                    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                    ".exe", ".dll", ".so", ".dylib", ".bin",
                    ".lock", ".log", ".tmp", ".cache", ".swp"
                ],
                "path_blacklist": [
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
            },
            "auto_settings": {
                "thresholds": {
                    "medium_max_files": 5000,
                    "large_min_files": 5001
                }
            },
            "profiles": {
                "medium": {
                    "description": "Medium projects (< 5000 files)",
                    "chunk_size": 512,
                    "chunk_overlap": 50,
                    "max_file_size": 1048576,
                    "search_limit": 50,
                    "rrf_k": 60,
                    "embedding_model": "all-MiniLM-L6-v2",
                    "preview_length": 200
                },
                "large": {
                    "description": "Large projects (> 5000 files)",
                    "chunk_size": 1024,
                    "chunk_overlap": 100,
                    "max_file_size": 2097152,
                    "search_limit": 100,
                    "rrf_k": 80,
                    "embedding_model": "all-mpnet-base-v2",
                    "preview_length": 300
                }
            }
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    @classmethod
    def detect_profile(cls, project_path: str, config: dict) -> str:
        try:
            from app.core.file_filters import should_index_file

            project_dir = Path(project_path)
            file_count = 0

            for file_path in project_dir.rglob('*'):
                if file_path.is_file() and should_index_file(str(file_path), str(project_dir)):
                    file_count += 1

            thresholds = config.get("auto_settings", {}).get("thresholds", {})
            medium_max = thresholds.get("medium_max_files", 5000)

            return "medium" if file_count <= medium_max else "large"

        except Exception:
            return "medium"

    @classmethod
    def apply_profile(cls, profile_name: str, project_path: str, cli_overrides: Optional[dict] = None):
        cls._current_project_path = project_path
        config = cls.load_project_config(project_path)

        if not config:
            cls.create_default_config(project_path)
            config = cls.load_project_config(project_path)

        if not config:
            return

        cls._load_base_config(config)

        active_profile = profile_name
        if profile_name == "auto":
            active_profile = cls.detect_profile(project_path, config)

        profiles = config.get("profiles", {})
        profile_settings = profiles.get(active_profile, profiles.get("medium", {}))

        cls.DEFAULT_CHUNK_SIZE = profile_settings.get("chunk_size", 512)
        cls.DEFAULT_CHUNK_OVERLAP = profile_settings.get("chunk_overlap", 50)
        cls.MAX_FILE_SIZE = profile_settings.get("max_file_size", 1048576)
        cls.DEFAULT_SEARCH_LIMIT = profile_settings.get("search_limit", 50)
        cls.RRF_K = profile_settings.get("rrf_k", 60)
        cls.CLI_CONTENT_PREVIEW_LENGTH = profile_settings.get("preview_length", cls.CLI_CONTENT_PREVIEW_LENGTH)

        embedding_model = profile_settings.get("embedding_model")
        if embedding_model and not cls.get_embedding_model():
            cls.set_embedding_model(embedding_model)

        if cli_overrides:
            if "chunk_size" in cli_overrides:
                cls.DEFAULT_CHUNK_SIZE = cli_overrides["chunk_size"]
            if "chunk_overlap" in cli_overrides:
                cls.DEFAULT_CHUNK_OVERLAP = cli_overrides["chunk_overlap"]
            if "max_file_size" in cli_overrides:
                cls.MAX_FILE_SIZE = cli_overrides["max_file_size"]
            if "search_limit" in cli_overrides:
                cls.DEFAULT_SEARCH_LIMIT = cli_overrides["search_limit"]
            if "rrf_k" in cli_overrides:
                cls.RRF_K = cli_overrides["rrf_k"]

    @classmethod
    def get_active_profile(cls, project_path: str) -> str:
        config = cls.load_project_config(project_path)
        if not config:
            return "auto"

        active = config.get("active_profile", "auto")
        if active == "auto":
            return cls.detect_profile(project_path, config)

        return active

    @classmethod
    def get_ignore_config(cls, project_path: str) -> dict:
        config = cls.load_project_config(project_path)

        if config and 'ignore' in config:
            return {
                'extension_blacklist': config['ignore'].get('extension_blacklist', []),
                'path_blacklist': config['ignore'].get('path_blacklist', [])
            }

        return {
            'extension_blacklist': ['*.pyc', '*.min.js', '*.min.css'],
            'path_blacklist': cls.DEFAULT_IGNORE_PATTERNS
        }
