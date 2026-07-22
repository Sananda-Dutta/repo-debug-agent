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
