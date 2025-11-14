from pathlib import Path
from typing import Optional, List, Dict
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_java as tsjava
import tree_sitter_cpp as tscpp
import tree_sitter_c_sharp as tscsharp
import tree_sitter_go as tsgo
import tree_sitter_rust as tsrust
import tree_sitter_html as tshtml
import tree_sitter_css as tscss
import tree_sitter_json as tsjson

from tree_sitter import Language, Parser
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TreeSitterParser:
    PARSERS = {
        'python': tspython,
        'javascript': tsjavascript,
        'typescript': tstypescript,
        'java': tsjava,
        'cpp': tscpp,
        'c_sharp': tscsharp,
        'go': tsgo,
        'rust': tsrust,
        'html': tshtml,
        'css': tscss,
        'json': tsjson,
    }

    IMPORTANT_NODE_TYPES = {
        'python': ['function_definition', 'class_definition', 'decorated_definition'],
        'javascript': ['function_declaration', 'class_declaration', 'method_definition', 'arrow_function'],
        'typescript': ['function_declaration', 'class_declaration', 'method_definition', 'arrow_function', 'interface_declaration'],
        'java': ['class_declaration', 'method_declaration', 'interface_declaration'],
        'cpp': ['function_definition', 'class_specifier', 'struct_specifier'],
        'c_sharp': ['class_declaration', 'method_declaration', 'interface_declaration'],
        'go': ['function_declaration', 'method_declaration', 'type_declaration'],
        'rust': ['function_item', 'impl_item', 'trait_item', 'struct_item'],
        'html': ['element'],
        'css': ['rule_set'],
        'json': ['object'],
    }

    def __init__(self):
        self._parsers = {}
        self._init_parsers()

    def _init_parsers(self):
        for lang_name, lang_module in self.PARSERS.items():
            try:
                if lang_name == 'typescript':
                    language = Language(lang_module.language_typescript())
                else:
                    language = Language(lang_module.language())
                parser = Parser(language)
                self._parsers[lang_name] = {
                    'parser': parser,
                    'language': language
                }
            except Exception as e:
                logger.error(f"Failed to initialize parser for {lang_name}: {e}")

    def get_language_from_extension(self, file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.hpp': 'cpp',
            '.h': 'cpp',
            '.cs': 'c_sharp',
            '.go': 'go',
            '.rs': 'rust',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        return ext_map.get(ext)

    def parse_file(self, file_path: str, content: str) -> Optional[Dict]:
        language = self.get_language_from_extension(file_path)
        if not language or language not in self._parsers:
            logger.warning(f"No parser available for {file_path}")
            return None

        try:
            parser_info = self._parsers[language]
            parser = parser_info['parser']

            tree = parser.parse(bytes(content, 'utf8'))

            important_nodes = self._extract_important_nodes(
                tree.root_node,
                language,
                content
            )

            return {
                'tree': tree,
                'language': language,
                'nodes': important_nodes
            }

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def _extract_important_nodes(
        self,
        root_node,
        language: str,
        content: str
    ) -> List[Dict]:
        important_types = self.IMPORTANT_NODE_TYPES.get(language, [])
        nodes = []

        def traverse(node):
            if node.type in important_types:
                name = self._get_node_name(node)

                nodes.append({
                    'type': node.type,
                    'name': name,
                    'start_line': node.start_point[0],
                    'end_line': node.end_point[0],
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte,
                })

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return nodes

    def _get_node_name(self, node) -> Optional[str]:
        name_fields = ['name', 'identifier', 'tag_name']

        for field in name_fields:
            name_node = node.child_by_field_name(field)
            if name_node:
                return name_node.text.decode('utf8')

        for child in node.children:
            if 'identifier' in child.type:
                return child.text.decode('utf8')

        return None
