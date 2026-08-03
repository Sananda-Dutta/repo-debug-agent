# Repo-Aware Autonomous Debugging Agent

An autonomous agent that clones a GitHub repository, understands its structure
and dependencies, reads failing tests/stack traces, locates only the relevant
code, and iteratively proposes and validates fixes - while using **Paritok**
to minimize LLM prompt token usage compared to a naive full-context baseline.

## Status: Phase 1 Complete - Project Foundation

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

### Status: Phase 2 Complete - Repository Ingestion

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

### Status: Phase 3 Complete - Codebase Indexing (Tree-sitter/AST)

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


### Status: Phase 4 Complete - Dependency Graph Construction

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
guessed at - a deliberate scope boundary documented here.

#Day 5
### Status: Phase 5 Complete - Vector Store & Embeddings

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
### Status: Phase 6 Complete - Stack Trace & Failing Test Parser

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
### Status: Phase 7 Complete - Relevant File Localization Engine

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

**Scoring model (tunable):** anchor=1.0, structural=0.6/hop_distance, semantic=0.5xsimilarity.
Scores from multiple sources are summed, not maxed - files corroborated by more than
one signal rank higher. If no stack-frame anchor resolves to a repo file, localization
falls back to semantic-search-only.

### Status: Phase 8 Complete - Context Retrieval & Token Compression

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [x] Phase 6: Stack Trace & Failing Test Parser
- [x] Phase 7: Relevant File Localization Engine
- [x] Phase 8: Context Retrieval & Token Compression
- [x] Phase 9: LLM Agent Layer (LangGraph multi-agent)
...

### [!] Paritok Integration Status

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
as relevant - NOT the entire repository. This isolates compression's specific
contribution from localization's contribution, which is already measured
separately in Phase 7.

Built with [Paritok](https://github.com/Paritok-official/paritok-4b-v1).

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-1f2d3d)](https://github.com/Paritok-official/paritok-4b-v1)

### Status: Phase 11 Complete - Test Execution Loop

- [x] Phase 1: Project Foundation & Config
- [x] Phase 2: Repository Ingestion
- [x] Phase 3: Codebase Indexing (Tree-sitter/AST)
- [x] Phase 4: Dependency Graph
- [x] Phase 5: Vector Store (FAISS/Chroma)
- [x] Phase 6: Stack Trace & Failing Test Parser
- [x] Phase 7: Relevant File Localization Engine
- [x] Phase 8: Context Retrieval & Token Compression
- [x] Phase 9: LLM Agent Layer (LangGraph multi-agent)
- [x] Phase 10: Fix Suggestion & Patching
- [x] Phase 11: Test Execution Loop
- [ ] Phase 12: Token Usage Dashboard
- [ ] Phase 13: FastAPI Service Layer
- [ ] Phase 14: Final Evaluation & Packaging

### Real Paritok integration - SDK mode vs. proxy mode

Phase 8's stub assumed `paritok.ParitokClient` would wrap our LLM client
directly (SDK mode). After installing and reading the real `paritok`
package (v1.2.x) for Phase 9, that assumption needed a correction:

**`paritok.ParitokClient`'s SDK mode only supports `client.messages.create()`
(Anthropic-shaped clients)** - its `_MessagesProxy` hardcodes a call to
`self._parent._client.messages.create(**kwargs)`. This project's LLM client
is `openai.OpenAI()`, whose Chat Completions interface is
`client.chat.completions.create()` - SDK mode cannot wrap it.

So Phase 9 uses Paritok's **proxy mode** instead - the mode Paritok's own
README calls "primary, recommended" anyway:

1. `LLMAgentService` starts a local `paritok proxy` subprocess
   (`agent/paritok_proxy.py`), configured via a generated `paritok.yaml`
   from our own `Settings` (`use_gpu_server: true` + the API key from
   `.env`, satisfying the hackathon's dashboard-verification requirement).
2. `agent/llm_client.py` points the existing `openai.OpenAI()` client's
   `base_url` at that proxy - zero changes to the LLM provider.
3. Every call diffs the proxy's `/stats` endpoint immediately before and
   after, producing real, per-call `ParitokCallStats` (tokens saved,
   compression ratio, estimated cost saved) - these flow into
   `TokenUsageReport.paritok_*` fields via `.with_paritok_stats(...)`,
   alongside Phase 8's own local-compression accounting.

### Usage (Phase 9)

```python
from repo_debug_agent.agent.service import LLMAgentService
from repo_debug_agent.context_retrieval.compressor import get_compressor

with LLMAgentService(compressor=get_compressor("rule_based")) as agent:
    result = agent.debug(
        repo_root=repo_metadata.local_path,
        index=codebase_index,
        localization_result=localization_result,  # from Phase 7
        token_budget=8000,
    )

print(result.fix_suggestion.raw_response)
print("Phase 8 local compression:", result.usage.compression_ratio)
print("Paritok hosted-GPU savings:", result.usage.paritok_tokens_saved, "tokens,",
      result.usage.paritok_estimated_cost_saved_usd)
```

Setup required before running Phase 9 for real (not needed to run the
test suite, which fakes the proxy/LLM client):

```
pip install -e ".[paritok]"
# Sign up at https://paritok.com -> dashboard -> API keys
# Put it in .env:
#   PARITOK_API_KEY=pk_live_...
#   PARITOK_USE_GPU_SERVER=true
#   OPENAI_API_KEY=sk-...
```

## Phase 10: Fix Suggestion & Patching

Turns Phase 9's raw LLM fix suggestion (`FixSuggestion.raw_response` -
free-form text) into actual changes on disk, safely.

### Why a parser is needed at all

Phase 9's system prompt (`agent/prompts.py`) asks the LLM for one of two
shapes: a **full-file replacement**, marked with a `File: <path>` header
immediately before a fenced code block containing the complete new file
content, or a **unified diff**, fenced as a ```diff block. `patching/parser.py`
recognizes several common header spellings (`### File:`, `**File:**`,
plain `File:`) so a reasonable-looking response isn't silently dropped
over a formatting nitpick - but a code block with no attached file path
is intentionally ignored rather than guessed at.

### Why `git apply` for diffs, not hand-rolled hunk matching

Phase 2 (`ingestion/service.py`) guarantees `repo_root` is always a real
git checkout - every ingested repo is cloned and pinned to a commit SHA
via GitPython. `patching/applicator.py` takes advantage of that: unified
diffs are applied via `git apply` (real patch tooling - handles fuzzy
context and whitespace correctly), while full-file replacements are just
written directly (no hunk-matching to fail on in the first place).

### Backup and rollback

Every file `PatchApplicator.apply()` touches is backed up first (to a
temp directory) before it's changed. `PatchApplyResult` carries enough
info (`backup_dir`, per-file `existed_before`) to fully undo the patch
via `PatchApplicator.rollback()` - including deleting files the patch
created that didn't exist before. This is what Phase 11's test-execution
loop will use: apply a candidate fix, run the test suite, and roll back
automatically if it doesn't actually fix the failure.

### Usage (Phase 10)

```python
from repo_debug_agent.patching.service import PatchService

patch_service = PatchService(repo_root=repo_metadata.local_path)

# Preview without touching disk:
parsed = patch_service.parse(result.fix_suggestion)  # result from Phase 9
for change in parsed.file_changes:
    print(change.file_path, change.format)

# Apply for real, with automatic backup:
apply_result = patch_service.apply(result.fix_suggestion)
if not apply_result.success:
    print("Could not apply:", apply_result.error)

# ...later, if the fix turns out to be wrong:
patch_service.rollback(apply_result)
```

## Phase 11: Test Execution Loop

Ties Phases 6, 9, and 10 together into the actual "autonomous" part of
the agent: run the repo's own tests, ask the LLM for a fix, apply it,
re-run the tests, and decide whether to keep it - repeating up to
`max_debug_iterations` (from `Settings`, default 5).

### Why re-run the FULL test suite, not just the target test

A fix that makes the target test pass but breaks two others isn't a
fix - `TestExecutionLoopService` re-runs the whole scoped test suite
(or `test_target` if you narrow it) after every attempt and diffs the
failing node IDs against the baseline:

- **Target(s) now pass, nothing new broke** -> `FIXED`, kept.
- **Target(s) now pass, but something else broke** -> `REGRESSED`,
  automatically rolled back via Phase 10's `PatchApplicator.rollback()`
  - a regression is never silently kept just because the original bug
  is gone.
- **Target(s) still failing** -> `NO_CHANGE`, rolled back, loop continues.
- **pytest itself couldn't run after the patch** (e.g. a syntax error
  the LLM introduced) -> `RUN_FAILED`, rolled back.
- **The fix suggestion wasn't parseable, or didn't apply at all** ->
  `NO_CHANGE` recorded without ever touching the filesystem.

### Why the prompt changes between iterations

Localization (Phase 7) is deliberately NOT re-run between iterations -
the loop is given one fixed target (a `LocalizationResult`, precomputed
or via a `localization_service`). What DOES change is the description
fed to Phase 9: after a rejected attempt, the next call is told exactly
which target test(s) are still failing and with what exception, so a
bad first attempt doesn't just get silently re-asked the same question
and produce the same (or an equally wrong) answer.

### Usage (Phase 11)

```python
from repo_debug_agent.agent.service import LLMAgentService
from repo_debug_agent.test_loop.service import TestExecutionLoopService
from repo_debug_agent.context_retrieval.compressor import get_compressor

with LLMAgentService(compressor=get_compressor("rule_based")) as agent:
    loop = TestExecutionLoopService(agent, max_iterations=5)
    result = loop.run(
        repo_root=repo_metadata.local_path,
        index=codebase_index,
        localization_result=localization_result,  # from Phase 7
    )

print("Fixed!" if result.success else "Gave up after all iterations.")
print(f"{len(result.iterations)} attempt(s) made")
print(f"Paritok hosted-GPU savings across the whole run: "
      f"{result.total_paritok_tokens_saved} tokens, "
      f"{result.total_paritok_requests} requests")

for record in result.iterations:
    print(record.iteration, record.outcome.value, record.notes)
```

If the baseline test run already has no failures, `run()` returns
`success=True` immediately without ever calling the LLM - nothing to
fix means no Paritok usage either, which matters for interpreting the
dashboard numbers on a run that finds nothing wrong.

Turning `TestLoopResult` into a report worth showing a judge (aggregate
Paritok savings across a full run, iteration-by-iteration token/cost
breakdown) is Phase 12's job, not this one.

### Status: Phase 11 Complete — Test Execution Loop