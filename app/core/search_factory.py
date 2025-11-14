from typing import Optional, Tuple

from app.search.vector_db import VectorDatabase
from app.search.hybrid import HybridSearch
from app.indexer.embeddings import EmbeddingGenerator
from app.utils.project_manager import ProjectManager


def create_search_engine(
    project_path: Optional[str] = None,
    model_name: Optional[str] = None
) -> Tuple[VectorDatabase, HybridSearch, EmbeddingGenerator]:
    if project_path is None:
        project_manager = ProjectManager()
        project_path = project_manager.get_current_project_path()

    vector_db = VectorDatabase(project_path=project_path)
    embedding_gen = EmbeddingGenerator(model_name=model_name)
    hybrid_search = HybridSearch(vector_db, embedding_gen)

    return vector_db, hybrid_search, embedding_gen
