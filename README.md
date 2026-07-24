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
