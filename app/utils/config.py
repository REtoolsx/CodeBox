import os
import hashlib
from pathlib import Path
from typing import Optional
import json


class AppConfig:
    APP_NAME = "CodeBox - Your Project & LLM Friend"
    APP_VERSION = "2.2.0"

    HOME_DIR = Path.home() / ".codebox"
    GLOBAL_CONFIG_FILE = HOME_DIR / "config.json"
    PROJECTS_DIR = HOME_DIR / "projects"

    DB_TABLE_NAME = "code_chunks"

    DEFAULT_CHUNK_SIZE = 512
    DEFAULT_CHUNK_OVERLAP = 50
    MAX_FILE_SIZE = 1024 * 1024

    DEFAULT_SEARCH_LIMIT = 50
    RRF_K = 60

    CLI_CONTENT_PREVIEW_LENGTH = 200
    CLI_MAX_CONTENT_LENGTH = 5000

    EMBEDDING_MODEL = None
    EMBEDDING_DIM = 384

    AVAILABLE_EMBEDDING_MODELS = {
        'all-MiniLM-L6-v2': {
            'full_name': 'sentence-transformers/all-MiniLM-L6-v2',
            'dim': 384,
            'description': 'Fast & lightweight (default)'
        },
        'all-mpnet-base-v2': {
            'full_name': 'sentence-transformers/all-mpnet-base-v2',
            'dim': 768,
            'description': 'Better quality, slower'
        },
        'codebert-base': {
            'full_name': 'microsoft/codebert-base',
            'dim': 768,
            'description': 'Code-optimized BERT'
        },
        'graphcodebert-base': {
            'full_name': 'microsoft/graphcodebert-base',
            'dim': 768,
            'description': 'Graph-aware code model'
        },
        'bge-small-en-v1.5': {
            'full_name': 'BAAI/bge-small-en-v1.5',
            'dim': 384,
            'description': 'Modern general-purpose model'
        }
    }

    AUTO_SYNC_ENABLED = False
    AUTO_SYNC_DEBOUNCE_SECONDS = 2.0
    AUTO_SYNC_BATCH_SIZE = 10

    DEFAULT_IGNORE_PATTERNS = [
        '__pycache__',
        '*.pyc',
        '.git',
        'node_modules',
        '.next',
        'dist',
        'build',
        '.lancedb',
        '.vscode',
        '.idea',
        '*.min.js',
        '*.min.css',
        'venv',
        'env',
        '.env'
    ]

    @classmethod
    def get_auto_sync_enabled(cls) -> bool:
        config = cls.load_global_config()
        return config.get('auto_sync_enabled', cls.AUTO_SYNC_ENABLED)

    @classmethod
    def set_auto_sync_enabled(cls, enabled: bool):
        config = cls.load_global_config()
        config['auto_sync_enabled'] = enabled
        cls.save_global_config(config)

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
        return cls.AVAILABLE_EMBEDDING_MODELS.get(model_key)

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
