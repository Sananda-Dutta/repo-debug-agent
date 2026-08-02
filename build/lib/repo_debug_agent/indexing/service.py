"""
CodebaseIndexingService: the single public entrypoint for Phase 3.

Orchestrates: walk files -> detect language -> parse (Tree-sitter) ->
extract symbols/imports -> assemble CodebaseIndex -> persist as JSON,
with content-hash-based caching so unchanged files are never re-parsed.
"""

import hashlib
import json
from pathlib import Path

from repo_debug_agent.core.logger import logger
from repo_debug_agent.indexing.file_walker import walk_repo_files
from repo_debug_agent.indexing.language_detector import detect_language
from repo_debug_agent.indexing.models import CodebaseIndex, FileIndex, Language
from repo_debug_agent.indexing.parser import parse_source
from repo_debug_agent.indexing.symbol_extractor import extract_imports, extract_symbols


class CodebaseIndexingService:
    def __init__(self, index_store_dir: Path):
        self.index_store_dir = index_store_dir
        self.index_store_dir.mkdir(parents=True, exist_ok=True)

    def build_index(self, repo_root: Path, commit_sha: str, force: bool = False) -> CodebaseIndex:
        """
        Build (or load cached) CodebaseIndex for the given repo at commit_sha.
        """
        cache_path = self._cache_path(commit_sha)
        if not force and cache_path.exists():
            logger.info(f"Loading cached index for commit {commit_sha[:8]}")
            return CodebaseIndex.model_validate_json(cache_path.read_text(encoding="utf-8"))

        files = walk_repo_files(repo_root)
        file_indices: dict[str, FileIndex] = {}

        for file_path in files:
            relative_path = str(file_path.relative_to(repo_root))
            language = detect_language(file_path)

            try:
                raw_bytes = file_path.read_bytes()
            except OSError as exc:
                logger.warning(f"Could not read {relative_path}: {exc}")
                continue

            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            line_count = raw_bytes.count(b"\n") + 1

            symbols, imports, parse_error = [], [], None
            if language != Language.UNKNOWN:
                tree = parse_source(raw_bytes, language)
                if tree is not None:
                    symbols = extract_symbols(tree, raw_bytes, language)
                    imports = extract_imports(tree, raw_bytes, language)
                else:
                    parse_error = "tree-sitter failed to parse this file"

            file_indices[relative_path] = FileIndex(
                relative_path=relative_path,
                absolute_path=str(file_path),
                language=language,
                content_hash=content_hash,
                line_count=line_count,
                symbols=symbols,
                imports=imports,
                parse_error=parse_error,
            )

        index = CodebaseIndex(commit_sha=commit_sha, root_path=str(repo_root), files=file_indices)
        self._persist(index, cache_path)

        logger.info(
            f"Indexed {len(file_indices)} files "
            f"({sum(len(f.symbols) for f in file_indices.values())} symbols) "
            f"for commit {commit_sha[:8]}"
        )
        return index

    def _cache_path(self, commit_sha: str) -> Path:
        return self.index_store_dir / f"index_{commit_sha}.json"

    @staticmethod
    def _persist(index: CodebaseIndex, path: Path) -> None:
        path.write_text(index.model_dump_json(indent=2), encoding="utf-8")