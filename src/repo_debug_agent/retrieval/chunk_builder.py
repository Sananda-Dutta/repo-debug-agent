"""
Converts CodeSymbols (from Phase 3's CodebaseIndex) into CodeChunks
ready for embedding.

The embedding_text is deliberately NOT the full raw source of the
symbol — it's a compact representation (qualified name + docstring +
truncated body) designed to maximize semantic signal per token spent
on embedding, while the chunk still records exact start/end lines so
the FULL body can be fetched later by Phase 7/8 when this chunk is
selected as relevant.
"""
#chunk_builder.py converts every extracted function, method, or class into a compact text "chunk" with metadata, 
#making it ready for embedding and semantic search in the next phase.


from pathlib import Path

from repo_debug_agent.indexing.models import CodebaseIndex
from repo_debug_agent.retrieval.models import CodeChunk

_MAX_EMBED_TEXT_CHARS = 1500


def build_chunks(index: CodebaseIndex, repo_root: Path) -> list["CodeChunk"]:
    from repo_debug_agent.retrieval.models import CodeChunk  # local import avoids cycles at module load

    chunks: list[CodeChunk] = []

    for relative_path, file_idx in index.files.items():
        if not file_idx.symbols:
            continue

        try:
            full_source = (repo_root / relative_path).read_text(encoding="utf-8", errors="ignore")
            source_lines = full_source.splitlines()
        except OSError:
            continue

        for symbol in file_idx.symbols:
            body_lines = source_lines[symbol.start_line - 1: symbol.end_line]
            body_preview = "\n".join(body_lines)[: _MAX_EMBED_TEXT_CHARS]

            embedding_text_parts = [
                f"File: {relative_path}",
                f"Symbol: {symbol.qualified_name} ({symbol.kind.value})",
            ]
            if symbol.docstring:
                embedding_text_parts.append(f"Docstring: {symbol.docstring}")
            embedding_text_parts.append(f"Code:\n{body_preview}")

            chunks.append(CodeChunk(
                chunk_id=f"{relative_path}::{symbol.qualified_name}",
                file_path=relative_path,
                symbol_name=symbol.name,
                qualified_name=symbol.qualified_name,
                kind=symbol.kind.value,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                embedding_text="\n".join(embedding_text_parts),
            ))

    return chunks