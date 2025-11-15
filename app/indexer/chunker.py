from typing import List, Dict, Optional
from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CodeChunk:
    def __init__(
        self,
        content: str,
        file_path: str,
        start_line: int,
        end_line: int,
        language: str,
        chunk_type: str = "code",
        node_name: Optional[str] = None,
        size_bytes: int = 0,
        modified_at: Optional[str] = None,
        signature: Optional[str] = None,
        parameters: Optional[str] = None,
        return_type: Optional[str] = None,
        docstring: Optional[str] = None,
        decorators: Optional[str] = None,
        imports: Optional[str] = None,
        parent_scope: Optional[str] = None,
        full_path: Optional[str] = None,
        scope_depth: int = 0,
        calls: Optional[str] = None
    ):
        self.content = content
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.language = language
        self.chunk_type = chunk_type
        self.node_name = node_name
        self.size_bytes = size_bytes
        self.modified_at = modified_at
        self.signature = signature
        self.parameters = parameters
        self.return_type = return_type
        self.docstring = docstring
        self.decorators = decorators
        self.imports = imports
        self.parent_scope = parent_scope
        self.full_path = full_path
        self.scope_depth = scope_depth
        self.calls = calls

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "chunk_type": self.chunk_type,
            "node_name": self.node_name or '',
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at or '',
            "signature": self.signature or '',
            "parameters": self.parameters or '',
            "return_type": self.return_type or '',
            "docstring": self.docstring or '',
            "decorators": self.decorators or '',
            "imports": self.imports or '',
            "parent_scope": self.parent_scope or '',
            "full_path": self.full_path or '',
            "scope_depth": self.scope_depth,
            "calls": self.calls or ''
        }


class CodeChunker:
    def __init__(
        self,
        chunk_size: int = AppConfig.DEFAULT_CHUNK_SIZE,
        overlap: int = AppConfig.DEFAULT_CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_code(
        self,
        content: str,
        file_path: str,
        language: str,
        nodes: List = None
    ) -> List[CodeChunk]:
        if nodes:
            return self._semantic_chunk(content, file_path, language, nodes)
        else:
            return self._sliding_window_chunk(content, file_path, language)

    def _semantic_chunk(
        self,
        content: str,
        file_path: str,
        language: str,
        nodes: List
    ) -> List[CodeChunk]:
        chunks = []
        lines = content.split('\n')

        for node in nodes:
            start_line = node.get('start_line', 0)
            end_line = node.get('end_line', 0)
            node_type = node.get('type', 'code')

            if start_line < len(lines) and end_line < len(lines):
                chunk_content = '\n'.join(lines[start_line:end_line + 1])

                if len(chunk_content) > self.chunk_size * 2:
                    sub_chunks = self._sliding_window_chunk(
                        chunk_content,
                        file_path,
                        language,
                        start_line_offset=start_line
                    )
                    chunks.extend(sub_chunks)
                else:
                    chunk = CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        language=language,
                        chunk_type=node_type,
                        node_name=node.get('name'),
                        signature=node.get('signature'),
                        parameters=node.get('parameters'),
                        return_type=node.get('return_type'),
                        docstring=node.get('docstring'),
                        decorators=node.get('decorators'),
                        parent_scope=node.get('parent_scope'),
                        full_path=node.get('full_path'),
                        scope_depth=node.get('scope_depth', 0),
                        calls=node.get('calls')
                    )
                    chunks.append(chunk)

        if not chunks:
            chunks = self._sliding_window_chunk(content, file_path, language)

        return chunks

    def _sliding_window_chunk(
        self,
        content: str,
        file_path: str,
        language: str,
        start_line_offset: int = 0
    ) -> List[CodeChunk]:
        chunks = []
        lines = content.split('\n')
        total_lines = len(lines)

        avg_line_length = sum(len(line) for line in lines) / max(total_lines, 1)
        lines_per_chunk = max(
            int(self.chunk_size / max(avg_line_length, 1)),
            1
        )
        overlap_lines = max(
            int(self.overlap / max(avg_line_length, 1)),
            0
        )

        i = 0
        while i < total_lines:
            end = min(i + lines_per_chunk, total_lines)
            chunk_content = '\n'.join(lines[i:end])

            chunk = CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=i + start_line_offset,
                end_line=end - 1 + start_line_offset,
                language=language,
                chunk_type="code"
            )
            chunks.append(chunk)

            i += lines_per_chunk - overlap_lines

            if i <= chunks[-1].start_line - start_line_offset:
                break

        return chunks
