# Repo-Aware Autonomous Debugging Agent

An autonomous agent that clones a GitHub repository, understands its structure
and dependencies, reads failing tests/stack traces, locates only the relevant
code, and iteratively proposes and validates fixes — while using **Paritok**
to minimize LLM prompt token usage compared to a naive full-context baseline.

## Status: Phase 1 Complete — Project Foundation

### Setup
```bash
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env   # fill in OPENAI_API_KEY / GITHUB_TOKEN
make test
make run
```

### Architecture (built incrementally)
- [x] Phase 1: Project Foundation & Config
- [ ] Phase 2: Repository Ingestion
- [ ] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [ ] Phase 4: Dependency Graph
- [ ] Phase 5: Vector Store (FAISS/Chroma)
- [ ] Phase 6: Stack Trace Parsing
- [ ] Phase 7: Relevant File Localization
- [ ] Phase 8: Paritok Context Compression
- [ ] Phase 9: LangGraph Multi-Agent Reasoning
- [ ] Phase 10: Fix Suggestion & Patching
- [ ] Phase 11: Test Execution Loop
- [ ] Phase 12: Token Usage & Savings Dashboard
- [ ] Phase 13: FastAPI Service Layer
- [ ] Phase 14: Evaluation & Packaging

Day2:

feat(ingestion): add repository ingestion layer (clone/load + validate)

- Add RepoSource/RepoMetadata models (Pydantic)
- Add source_resolver: normalize URL/shorthand/local-path input
- Add cloner: GitPython-based shallow clone with token auth + ref checkout
- Add validator: post-clone sanity checks (non-empty, contains source code)
- Add RepoIngestionService orchestrating resolve -> clone -> validate -> metadata
- Pin commit_sha in metadata for reproducible downstream analysis
- Add shared AgentError/IngestionError exception hierarchy
- Add full ingestion test suite (source resolver, validator, service)

Phase 2/14 of Repo-Aware Autonomous Debugging Agent (Token Efficiency Hackathon)

### Status: Phase 2 Complete — Repository Ingestion

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [ ] Phase 3: Codebase Indexing (Tree-sitter/AST)
...

### Usage (Phase 2)

```python
from repo_debug_agent.ingestion.service import RepoIngestionService

service = RepoIngestionService()

# Any of these work:
metadata = service.ingest("psf/requests")                          # shorthand
metadata = service.ingest("https://github.com/psf/requests")       # URL
metadata = service.ingest("/path/to/already/cloned/repo")          # local path

print(metadata.full_name, metadata.commit_sha)
```

Supported inputs: GitHub HTTPS/SSH URLs, `owner/repo` shorthand, or an existing
local directory. Private repos require `GITHUB_TOKEN` set in `.env`.


Day: 3
feat(indexing): add Tree-sitter based multi-language codebase indexing

- Add CodeSymbol/FileIndex/CodebaseIndex models
- Add language_detector: extension -> Language registry
- Add file_walker: gitignore-aware traversal excluding vendor/build noise
- Add parser: cached Tree-sitter wrapper (Python/JS/TS/Java/Go)
- Add symbol_extractor: recursive AST walk extracting functions/classes/
  methods with parent linkage and qualified names, plus import statements
- Add CodebaseIndexingService with commit-sha-keyed JSON caching
- Add full indexing test suite

Phase 3/14 of Repo-Aware Autonomous Debugging Agent (Token Efficiency Hackathon)

### Status: Phase 3 Complete — Codebase Indexing (Tree-sitter/AST)

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [ ] Phase 4: Dependency Graph
...

### Usage (Phase 3)

```python
from pathlib import Path
from repo_debug_agent.indexing.service import CodebaseIndexingService

service = CodebaseIndexingService(index_store_dir=Path("vector_store/indices"))
index = service.build_index(repo_root=Path("workspace/psf__requests"), commit_sha="<sha>")

file_idx = index.get_file("requests/models.py")
for symbol in file_idx.symbols:
    print(symbol.qualified_name, symbol.kind, f"L{symbol.start_line}-{symbol.end_line}")
```

**Supported languages (symbol extraction):** Python, JavaScript, TypeScript, Java, Go.
Other file types are still indexed (path, hash, line count) but without symbol/import extraction.


### Status: Phase 4 Complete — Dependency Graph Construction

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [ ] Phase 5: Vector Store (FAISS/Chroma)
...

### Usage (Phase 4)

```python
from repo_debug_agent.dependency_graph.service import DependencyGraphService

graph = DependencyGraphService().build(index)  # index from Phase 3

graph.imports("app/main.py")            # files/externals main.py directly imports
graph.imported_by("app/utils.py")       # files that directly import utils.py
graph.blast_radius("app/utils.py", depth=2)     # transitive impact if utils.py breaks
graph.dependencies_of("app/main.py", depth=2)   # transitive context needed to understand main.py
graph.find_cycles()                     # circular import detection
graph.stats()                           # GraphStats summary
```

**Scope note:** import resolution handles direct/relative Python imports and
relative JS/TS imports precisely. Java/Go imports and JS/TS bundler aliases
(webpack/tsconfig paths) are recorded as external dependencies rather than
guessed at — a deliberate scope boundary documented here.

#Day 5
### Status: Phase 5 Complete — Vector Store & Embeddings

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [ ] Phase 6: Stack Trace & Failing Test Parser
...

### Usage (Phase 5)

```python
from repo_debug_agent.retrieval.service import SemanticSearchService
from repo_debug_agent.retrieval.embedding_provider import get_embedding_provider
from repo_debug_agent.retrieval.vector_store import get_vector_store

embedder = get_embedding_provider("local")   # or "openai" (needs OPENAI_API_KEY)
store = get_vector_store("faiss", persist_dir, embedder.dimension)  # or "chroma"

service = SemanticSearchService(embedder, store)
service.index_codebase(index, repo_root)      # index from Phase 3

results = service.search("connection timeout while refreshing token", k=5)
for r in results:
    print(r.score, r.chunk.qualified_name, r.chunk.file_path, r.chunk.start_line)
```

**Backend choice:** Local embeddings (`sentence-transformers`, free/offline) are the
default. Set `OPENAI_API_KEY` and pass `"openai"` for higher-quality embeddings at
API cost. FAISS is the default vector store; pass `"chroma"` to use ChromaDB instead.


#Phase 6/14
### Status: Phase 6 Complete — Stack Trace & Failing Test Parser

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [x] Phase 6: Stack Trace & Failing Test Parser
- [ ] Phase 7: Relevant File Localization Engine
...

### Usage (Phase 6)

```python
from repo_debug_agent.failure_analysis.service import FailureAnalysisService

service = FailureAnalysisService()

# Path A: user-provided stack trace text
parsed = service.analyze_pasted_traceback(raw_traceback_text)
print(parsed.exception_type, parsed.innermost_frame.file_path, parsed.innermost_frame.line_number)

# Path B: run the repo's own tests
report = service.run_and_analyze_tests(repo_root, test_target="tests/")
for failure in report.failures:
    print(failure.node_id, failure.exception.exception_type if failure.exception else None)
```

**Scope note:** target-repo test dependencies must already be installed in the
environment executing tests. Automatic per-repo virtualenv + dependency
installation is a documented future enhancement, not implemented in Phase 6.
Chained exceptions are parsed as their final (most recently raised) block only.

#phase 7
### Status: Phase 7 Complete — Relevant File Localization Engine

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [x] Phase 6: Stack Trace & Failing Test Parser
- [x] Phase 7: Relevant File Localization Engine
- [ ] Phase 8: Context Retrieval & Paritok Token Compression
...

### Usage (Phase 7)

```python
from repo_debug_agent.localization.service import FileLocalizationService

service = FileLocalizationService(index, graph, search_service, repo_root=str(repo_root))
result = service.localize(exception=parsed_exception, user_description="fails intermittently under load")

for ranked in result.top_files(10):
    print(f"{ranked.score:.2f}  {ranked.file_path}  sources={ranked.sources}  symbols={ranked.relevant_symbols}")
```

**Scoring model (tunable):** anchor=1.0, structural=0.6/hop_distance, semantic=0.5×similarity.
Scores from multiple sources are summed, not maxed — files corroborated by more than
one signal rank higher. If no stack-frame anchor resolves to a repo file, localization
falls back to semantic-search-only.

### Status: Phase 8 Complete — Context Retrieval & Token Compression

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [x] Phase 6: Stack Trace & Failing Test Parser
- [x] Phase 7: Relevant File Localization Engine
- [x] Phase 8: Context Retrieval & Token Compression
- [ ] Phase 9: LLM Agent Layer (LangGraph multi-agent)
...

### ⚠️ Paritok Integration Status

`context_retrieval/paritok_adapter.py` is currently a **documented stub**
delegating to a rule-based compressor, pending confirmation of Paritok's
actual package name and API. See that file's docstring for the exact
integration point.

### Usage (Phase 8)

```python
from repo_debug_agent.context_retrieval.service import ContextRetrievalService
from repo_debug_agent.context_retrieval.compressor import get_compressor

service = ContextRetrievalService(get_compressor("rule_based"))  # or "naive" / "paritok"
context = service.build_context(localization_result, index, repo_root, token_budget=8000)

print(context.usage.baseline_token_count, "->", context.usage.compressed_token_count)
print(f"{context.usage.compression_ratio:.1%} reduction")
print(context.assembled_text)  # ready to hand to Phase 9's LLM agent
```

**Baseline definition (important for interpreting the metric):** the baseline
is the full, uncompressed text of every file the localization engine ranked
as relevant — NOT the entire repository. This isolates compression's specific
contribution from localization's contribution, which is already measured
separately in Phase 7.
