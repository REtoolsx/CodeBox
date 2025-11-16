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

    def to_embedding_text(self) -> str:
        parts = []

        if self.file_path:
            parts.append(f"File: {self.file_path}")

        if self.chunk_type and self.chunk_type != "code":
            parts.append(f"Type: {self.chunk_type}")

        if self.full_path:
            parts.append(f"Path: {self.full_path}")
        elif self.node_name and self.parent_scope:
            parts.append(f"Path: {self.parent_scope}.{self.node_name}")
        elif self.node_name:
            parts.append(f"Name: {self.node_name}")

        if self.signature:
            parts.append(f"Signature: {self.signature}")

        if self.docstring:
            parts.append(f"Description: {self.docstring}")

        if parts:
            parts.append("")

        parts.append(self.content)

        return "\n".join(parts)

    def is_high_quality(self) -> bool:
        if self.chunk_type in ['class_definition', 'function_definition', 'decorated_definition',
                                'method_definition', 'interface_declaration']:
            return True

        content_stripped = self.content.strip()

        if self.node_name and self.node_name.strip():
            if len(content_stripped) < 30:
                return False
        else:
            if len(content_stripped) < 50:
                return False

            lines = content_stripped.split('\n')
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            if len(code_lines) < 3:
                return False

        import_only_patterns = [
            'import ', 'from ', 'require(', 'include ', '#include'
        ]
        lines = content_stripped.split('\n')
        non_empty_lines = [l.strip() for l in lines if l.strip()]

        if non_empty_lines:
            import_count = sum(1 for l in non_empty_lines
                             if any(l.startswith(p) for p in import_only_patterns))
            if import_count / len(non_empty_lines) > 0.8:
                return False

        comment_only_patterns = ['#', '//', '/*', '*', '"""', "'''"]
        if non_empty_lines:
            comment_count = sum(1 for l in non_empty_lines
                              if any(l.startswith(p) for p in comment_only_patterns))
            if comment_count / len(non_empty_lines) > 0.9:
                return False

        return True


class CodeChunker:
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ):
        self.chunk_size = chunk_size if chunk_size is not None else AppConfig.DEFAULT_CHUNK_SIZE
        self.overlap = overlap if overlap is not None else AppConfig.DEFAULT_CHUNK_OVERLAP

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
        overlap_lines = 3

        for node in nodes:
            original_start = node.get('start_line', 0)
            original_end = node.get('end_line', 0)

            start_line = max(0, original_start - overlap_lines)
            end_line = min(len(lines) - 1, original_end + overlap_lines)
            node_type = node.get('type', 'code')

            if start_line < len(lines) and end_line < len(lines):
                chunk_content = '\n'.join(lines[start_line:end_line + 1])

                if len(chunk_content) > self.chunk_size * 2:
                    sub_chunks = self._split_at_logical_boundaries(
                        chunk_content,
                        file_path,
                        language,
                        start_line_offset=start_line,
                        node_info=node
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

    def _split_at_logical_boundaries(
        self,
        content: str,
        file_path: str,
        language: str,
        start_line_offset: int,
        node_info: dict
    ) -> List[CodeChunk]:
        chunks = []
        lines = content.split('\n')
        current_chunk_lines = []
        current_start_line = 0

        for i, line in enumerate(lines):
            current_chunk_lines.append(line)
            current_content = '\n'.join(current_chunk_lines)

            if not line.strip() and len(current_content) >= self.chunk_size:
                chunk = CodeChunk(
                    content=current_content,
                    file_path=file_path,
                    start_line=start_line_offset + current_start_line,
                    end_line=start_line_offset + i,
                    language=language,
                    chunk_type=node_info.get('type', 'code'),
                    node_name=node_info.get('name'),
                    signature=node_info.get('signature'),
                    parent_scope=node_info.get('parent_scope'),
                    full_path=node_info.get('full_path'),
                    scope_depth=node_info.get('scope_depth', 0)
                )
                chunks.append(chunk)
                current_chunk_lines = []
                current_start_line = i + 1

        if current_chunk_lines:
            chunk = CodeChunk(
                content='\n'.join(current_chunk_lines),
                file_path=file_path,
                start_line=start_line_offset + current_start_line,
                end_line=start_line_offset + len(lines) - 1,
                language=language,
                chunk_type=node_info.get('type', 'code'),
                node_name=node_info.get('name'),
                signature=node_info.get('signature'),
                parent_scope=node_info.get('parent_scope'),
                full_path=node_info.get('full_path'),
                scope_depth=node_info.get('scope_depth', 0)
            )
            chunks.append(chunk)

        return chunks if chunks else self._sliding_window_chunk(
            content, file_path, language, start_line_offset
        )

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
