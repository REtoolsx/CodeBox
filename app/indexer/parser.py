from pathlib import Path
from typing import Optional, List, Dict
import json
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
                    'signature': self._extract_signature(node, language),
                    'parameters': self._extract_parameters(node, language),
                    'return_type': self._extract_return_type(node, language),
                    'docstring': self._extract_docstring(node, language),
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

    def _extract_signature(self, node, language: str) -> Optional[str]:
        try:
            if language == 'python':
                return self._extract_python_signature(node)
            elif language in ['typescript', 'javascript']:
                return self._extract_ts_js_signature(node, language)
            else:
                return None
        except Exception as e:
            logger.debug(f"Failed to extract signature: {e}")
            return None

    def _extract_parameters(self, node, language: str) -> Optional[str]:
        try:
            if language == 'python':
                return self._extract_python_parameters(node)
            elif language in ['typescript', 'javascript']:
                return self._extract_ts_js_parameters(node)
            else:
                return None
        except Exception as e:
            logger.debug(f"Failed to extract parameters: {e}")
            return None

    def _extract_return_type(self, node, language: str) -> Optional[str]:
        try:
            if language == 'python':
                return self._extract_python_return_type(node)
            elif language == 'typescript':
                return self._extract_ts_return_type(node)
            else:
                return None
        except Exception as e:
            logger.debug(f"Failed to extract return type: {e}")
            return None

    def _extract_docstring(self, node, language: str) -> Optional[str]:
        try:
            if language == 'python':
                return self._extract_python_docstring(node)
            elif language in ['typescript', 'javascript']:
                return self._extract_js_docstring(node)
            else:
                return None
        except Exception as e:
            logger.debug(f"Failed to extract docstring: {e}")
            return None

    def _extract_python_signature(self, node) -> Optional[str]:
        if node.type == 'decorated_definition':
            for child in node.children:
                if child.type == 'function_definition':
                    node = child
                    break

        if node.type not in ['function_definition', 'class_definition']:
            return None

        name = self._get_node_name(node)
        if not name:
            return None

        if node.type == 'class_definition':
            return f"class {name}"

        params_node = node.child_by_field_name('parameters')
        return_type_node = node.child_by_field_name('return_type')

        params_text = params_node.text.decode('utf8') if params_node else "()"
        return_type_text = ""

        if return_type_node:
            return_type_text = f" -> {return_type_node.text.decode('utf8')}"

        return f"def {name}{params_text}{return_type_text}"

    def _extract_python_parameters(self, node) -> Optional[str]:
        if node.type == 'decorated_definition':
            for child in node.children:
                if child.type == 'function_definition':
                    node = child
                    break

        if node.type != 'function_definition':
            return None

        params_node = node.child_by_field_name('parameters')
        if not params_node:
            return None

        params = []
        for child in params_node.children:
            if child.type == 'identifier':
                params.append({"name": child.text.decode('utf8'), "type": None})
            elif child.type == 'typed_parameter':
                param_name = None
                param_type = None
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param_name = subchild.text.decode('utf8')
                    elif subchild.type == 'type':
                        param_type = subchild.text.decode('utf8')
                if param_name:
                    params.append({"name": param_name, "type": param_type})
            elif child.type == 'default_parameter':
                param_name = None
                param_type = None
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param_name = subchild.text.decode('utf8')
                    elif subchild.type == 'type':
                        param_type = subchild.text.decode('utf8')
                if param_name:
                    params.append({"name": param_name, "type": param_type})

        return json.dumps(params) if params else None

    def _extract_python_return_type(self, node) -> Optional[str]:
        if node.type == 'decorated_definition':
            for child in node.children:
                if child.type == 'function_definition':
                    node = child
                    break

        if node.type != 'function_definition':
            return None

        return_type_node = node.child_by_field_name('return_type')
        if return_type_node:
            return return_type_node.text.decode('utf8')
        return None

    def _extract_ts_js_signature(self, node, language: str) -> Optional[str]:
        name = self._get_node_name(node)
        if not name:
            return None

        if node.type in ['class_declaration', 'interface_declaration']:
            return f"class {name}" if node.type == 'class_declaration' else f"interface {name}"

        params_node = node.child_by_field_name('parameters')
        params_text = params_node.text.decode('utf8') if params_node else "()"

        return_type_text = ""
        if language == 'typescript':
            return_type_node = node.child_by_field_name('return_type')
            if return_type_node:
                return_type_text = return_type_node.text.decode('utf8')

        if node.type == 'arrow_function':
            return f"{params_text} => {return_type_text}".strip()
        else:
            return f"function {name}{params_text}{return_type_text}"

    def _extract_ts_js_parameters(self, node) -> Optional[str]:
        params_node = node.child_by_field_name('parameters')
        if not params_node:
            return None

        params = []
        for child in params_node.children:
            if child.type in ['required_parameter', 'optional_parameter']:
                param_name = None
                param_type = None
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param_name = subchild.text.decode('utf8')
                    elif subchild.type == 'type_annotation':
                        for type_child in subchild.children:
                            if type_child.type != ':':
                                param_type = type_child.text.decode('utf8')
                                break
                if param_name:
                    params.append({"name": param_name, "type": param_type})
            elif child.type == 'identifier':
                params.append({"name": child.text.decode('utf8'), "type": None})

        return json.dumps(params) if params else None

    def _extract_ts_return_type(self, node) -> Optional[str]:
        return_type_node = node.child_by_field_name('return_type')
        if not return_type_node:
            return None

        for child in return_type_node.children:
            if child.type != ':':
                return child.text.decode('utf8')
        return None

    def _extract_python_docstring(self, node) -> Optional[str]:
        if node.type == 'decorated_definition':
            for child in node.children:
                if child.type == 'function_definition':
                    node = child
                    break

        if node.type not in ['function_definition', 'class_definition']:
            return None

        body = node.child_by_field_name('body')
        if not body:
            return None

        for child in body.children:
            if child.type == 'expression_statement':
                for subchild in child.children:
                    if subchild.type == 'string':
                        docstring_text = subchild.text.decode('utf8')
                        docstring_text = docstring_text.strip()
                        if docstring_text.startswith('"""') or docstring_text.startswith("'''"):
                            return docstring_text[3:-3].strip()
                        elif docstring_text.startswith('"') or docstring_text.startswith("'"):
                            return docstring_text[1:-1].strip()
                break

        return None

    def _extract_js_docstring(self, node) -> Optional[str]:
        parent = node.parent
        if not parent:
            return None

        node_index = None
        for i, child in enumerate(parent.children):
            if child == node:
                node_index = i
                break

        if node_index is None or node_index == 0:
            return None

        prev_sibling = parent.children[node_index - 1]

        if prev_sibling.type == 'comment':
            comment_text = prev_sibling.text.decode('utf8')
            if comment_text.strip().startswith('/**'):
                docstring = comment_text.strip()[3:-2].strip()
                return docstring

        return None
