from pathlib import Path
from typing import Optional, List, Dict, Set
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
from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound
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

    # Pygments lexer name → tree-sitter parser mapping
    PYGMENTS_TO_PARSER = {
        'Python': 'python',
        'Python 3': 'python',
        'JavaScript': 'javascript',
        'JSX': 'javascript',
        'TypeScript': 'typescript',
        'TSX': 'typescript',
        'Java': 'java',
        'C++': 'cpp',
        'C': 'cpp',
        'C#': 'c_sharp',
        'Go': 'go',
        'Rust': 'rust',
        'HTML': 'html',
        'HTML+Django/Jinja': 'html',
        'CSS': 'css',
        'JSON': 'json',
        'YAML': 'json',  # YAML files will be treated as JSON for tree-sitter
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

    def get_all_supported_extensions(self) -> Set[str]:
        """Return all file extensions that have tree-sitter parser support"""
        from pygments.lexers import get_all_lexers

        supported_exts = set()

        # Get all Pygments lexers
        for lexer_name, aliases, patterns, mimetypes in get_all_lexers():
            # Check if this lexer maps to one of our tree-sitter parsers
            if lexer_name in self.PYGMENTS_TO_PARSER:
                # Add all file patterns (extensions) for this lexer
                for pattern in patterns:
                    # Extract extension from pattern (e.g., "*.py" -> ".py")
                    if pattern.startswith('*.'):
                        ext = pattern[1:]  # Remove the '*'
                        supported_exts.add(ext.lower())

        return supported_exts

    def get_language_from_extension(self, file_path: str) -> Optional[str]:
        """Auto-detect language from file extension using Pygments"""
        try:
            # Try Pygments first (supports 500+ languages)
            lexer = get_lexer_for_filename(file_path)
            lexer_name = lexer.name

            # Map Pygments lexer name to tree-sitter parser name
            parser_lang = self.PYGMENTS_TO_PARSER.get(lexer_name)

            if parser_lang and parser_lang in self._parsers:
                logger.debug(f"Detected language '{parser_lang}' for {file_path} via Pygments")
                return parser_lang

            # If Pygments detected a language but we don't have a parser, log and return None
            if lexer_name:
                logger.debug(f"Pygments detected '{lexer_name}' for {file_path}, but no tree-sitter parser available")
                return None

        except ClassNotFound:
            # Pygments couldn't detect the language
            logger.debug(f"Pygments couldn't detect language for {file_path}")
            return None
        except Exception as e:
            logger.debug(f"Error detecting language for {file_path}: {e}")
            return None

        return None

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

            file_imports = self._extract_imports(tree.root_node, language)

            return {
                'tree': tree,
                'language': language,
                'nodes': important_nodes,
                'imports': file_imports
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

        def traverse(node, parent_chain=None):
            if parent_chain is None:
                parent_chain = []

            if node.type in important_types:
                name = self._get_node_name(node)

                parent_scope = '.'.join(parent_chain) if parent_chain else None
                full_path = '.'.join(parent_chain + [name]) if name else None
                scope_depth = len(parent_chain)

                function_calls = self._extract_function_calls(node, language, name)
                calls_json = json.dumps(function_calls) if function_calls else None

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
                    'decorators': self._extract_decorators(node, language),
                    'parent_scope': parent_scope,
                    'full_path': full_path,
                    'scope_depth': scope_depth,
                    'calls': calls_json,
                })

                new_chain = parent_chain + [name] if name else parent_chain
                for child in node.children:
                    traverse(child, new_chain)
            else:
                for child in node.children:
                    traverse(child, parent_chain)

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

    def _extract_decorators(self, node, language: str) -> Optional[str]:
        """Extract decorator/annotation information from a node"""
        decorators = []

        try:
            if language == 'python':
                if node.type == 'decorated_definition':
                    for child in node.children:
                        if child.type == 'decorator':
                            decorator_text = child.text.decode('utf8').strip()
                            decorators.append(decorator_text)

            elif language in ['typescript', 'javascript']:
                for child in node.children:
                    if child.type == 'decorator':
                        decorator_text = child.text.decode('utf8').strip()
                        decorators.append(decorator_text)

            elif language == 'java':
                for child in node.children:
                    if child.type in ['marker_annotation', 'annotation']:
                        annotation_text = child.text.decode('utf8').strip()
                        decorators.append(annotation_text)

            elif language == 'rust':
                for child in node.children:
                    if child.type == 'attribute_item':
                        attribute_text = child.text.decode('utf8').strip()
                        decorators.append(attribute_text)

            elif language == 'c_sharp':
                for child in node.children:
                    if child.type == 'attribute_list':
                        attribute_text = child.text.decode('utf8').strip()
                        decorators.append(attribute_text)

        except Exception as e:
            logger.debug(f"Failed to extract decorators for {language}: {e}")
            return None

        return json.dumps(decorators) if decorators else None

    def _extract_imports(self, root_node, language: str) -> List[str]:
        """Extract all import statements from file"""
        imports = []

        import_node_types = {
            'python': ['import_statement', 'import_from_statement'],
            'javascript': ['import_statement'],
            'typescript': ['import_statement'],
            'java': ['import_declaration'],
            'go': ['import_spec', 'import_declaration'],
            'rust': ['use_declaration'],
            'cpp': ['preproc_include'],
            'c_sharp': ['using_directive'],
        }

        target_types = import_node_types.get(language, [])
        if not target_types:
            return imports

        def traverse(node):
            if node.type in target_types:
                import_text = node.text.decode('utf8').strip()
                if import_text and import_text not in imports:
                    imports.append(import_text)

            for child in node.children:
                traverse(child)

        try:
            traverse(root_node)
        except Exception as e:
            logger.debug(f"Failed to extract imports for {language}: {e}")

        return imports

    def _get_call_target(self, node, language: str) -> Optional[str]:
        """Extract the target function/method name from a call node"""
        try:
            if language == 'python':
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf8')
                    elif child.type == 'attribute':
                        return child.text.decode('utf8')

            elif language in ['javascript', 'typescript']:
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf8')
                    elif child.type == 'member_expression':
                        return child.text.decode('utf8')

            elif language == 'java':
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf8')

            elif language == 'go':
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf8')
                    elif child.type == 'selector_expression':
                        return child.text.decode('utf8')

            elif language == 'rust':
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf8')
                    elif child.type == 'field_expression':
                        return child.text.decode('utf8')

        except Exception as e:
            logger.debug(f"Failed to extract call target: {e}")

        return None

    def _extract_function_calls(self, node, language: str, current_function: str = None) -> List[Dict]:
        """Extract function calls within the given node scope"""
        calls = []

        call_node_types = {
            'python': ['call'],
            'javascript': ['call_expression'],
            'typescript': ['call_expression'],
            'java': ['method_invocation'],
            'go': ['call_expression'],
            'rust': ['call_expression'],
            'cpp': ['call_expression'],
            'c_sharp': ['invocation_expression'],
        }

        target_call_types = call_node_types.get(language, [])

        function_def_types = self.IMPORTANT_NODE_TYPES.get(language, [])

        def traverse(node, func_name=None):
            if node.type in function_def_types:
                new_func_name = self._get_node_name(node)
                for child in node.children:
                    traverse(child, new_func_name)
            elif node.type in target_call_types:
                callee = self._get_call_target(node, language)
                if callee and func_name:
                    calls.append({
                        'caller': func_name,
                        'callee': callee,
                        'line': node.start_point[0]
                    })
                for child in node.children:
                    traverse(child, func_name)
            else:
                for child in node.children:
                    traverse(child, func_name)

        try:
            traverse(node, current_function)
        except Exception as e:
            logger.debug(f"Failed to extract function calls: {e}")

        return calls
