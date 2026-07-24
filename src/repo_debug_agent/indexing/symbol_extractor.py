"""
Walks a Tree-sitter AST and extracts CodeSymbol objects.

Each language's grammar uses different node-type names for the same
concept (e.g. Python: 'function_definition', JS: 'function_declaration').
This module centralizes that mapping so adding a language means adding
entries here, not rewriting the walk algorithm.
"""

from tree_sitter import Tree, Node

from repo_debug_agent.indexing.models import CodeSymbol, Language, SymbolKind

# node type name -> SymbolKind, per language
_FUNCTION_NODE_TYPES: dict[Language, set[str]] = {
    Language.PYTHON: {"function_definition"},
    Language.JAVASCRIPT: {"function_declaration", "method_definition"},
    Language.TYPESCRIPT: {"function_declaration", "method_definition"},
    Language.JAVA: {"method_declaration"},
    Language.GO: {"function_declaration", "method_declaration"},
}

_CLASS_NODE_TYPES: dict[Language, set[str]] = {
    Language.PYTHON: {"class_definition"},
    Language.JAVASCRIPT: {"class_declaration"},
    Language.TYPESCRIPT: {"class_declaration"},
    Language.JAVA: {"class_declaration"},
    Language.GO: {"type_declaration"},  # Go doesn't have classes; structs are the closest analog
}

_IMPORT_NODE_TYPES: dict[Language, set[str]] = {
    Language.PYTHON: {"import_statement", "import_from_statement"},
    Language.JAVASCRIPT: {"import_statement"},
    Language.TYPESCRIPT: {"import_statement"},
    Language.JAVA: {"import_declaration"},
    Language.GO: {"import_spec"},
}


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_name_node(node: Node) -> Node | None:
    """Find the identifier child that represents this node's name."""
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return child
    return None


def _extract_docstring(node: Node, source: bytes, language: Language) -> str | None:
    """Best-effort docstring extraction (Python-focused; other languages return None for now)."""
    if language != Language.PYTHON:
        return None
    body = next((c for c in node.children if c.type == "block"), None)
    if not body or not body.children:
        return None
    first_stmt = body.children[0]
    if first_stmt.type == "expression_statement" and first_stmt.children:
        expr = first_stmt.children[0]
        if expr.type == "string":
            text = _node_text(expr, source)
            return text.strip("\"'")
    return None


def extract_symbols(tree: Tree, source: bytes, language: Language) -> list[CodeSymbol]:
    """
    Walk the AST and return all functions/classes/methods as CodeSymbol objects.

    Methods (functions nested inside a class body) get:
      - kind = SymbolKind.METHOD
      - parent = enclosing class name
      - qualified_name = "ClassName.method_name"
    """
    function_types = _FUNCTION_NODE_TYPES.get(language, set())
    class_types = _CLASS_NODE_TYPES.get(language, set())
    symbols: list[CodeSymbol] = []

    def walk(node: Node, current_class: str | None) -> None:
        if node.type in class_types:
            name_node = _find_name_node(node)
            class_name = _node_text(name_node, source) if name_node else "<anonymous>"
            symbols.append(CodeSymbol(
                name=class_name,
                qualified_name=class_name,
                kind=SymbolKind.CLASS,
                parent=None,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=_extract_docstring(node, source, language),
            ))
            for child in node.children:
                walk(child, current_class=class_name)
            return

        if node.type in function_types:
            name_node = _find_name_node(node)
            func_name = _node_text(name_node, source) if name_node else "<anonymous>"
            kind = SymbolKind.METHOD if current_class else SymbolKind.FUNCTION
            qualified = f"{current_class}.{func_name}" if current_class else func_name
            symbols.append(CodeSymbol(
                name=func_name,
                qualified_name=qualified,
                kind=kind,
                parent=current_class,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=_extract_docstring(node, source, language),
            ))
            # Do not recurse further with current_class for nested defs inside
            # functions (closures) — treat them as flat top-level-ish functions.
            for child in node.children:
                walk(child, current_class=current_class)
            return

        for child in node.children:
            walk(child, current_class=current_class)

    walk(tree.root_node, current_class=None)
    return symbols


def extract_imports(tree: Tree, source: bytes, language: Language) -> list[str]:
    """Extract raw import statement text (later resolved into a dependency graph in Phase 4)."""
    import_types = _IMPORT_NODE_TYPES.get(language, set())
    imports: list[str] = []

    def walk(node: Node) -> None:
        if node.type in import_types:
            imports.append(_node_text(node, source).strip())
            return
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return imports