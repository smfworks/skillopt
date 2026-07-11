# AGENTS.md — SkillOpt

**Project:** SkillOpt — Self-optimizing agent skills with automatic capability diagnosis  
**Status:** Active public prototype (v0.13)

---

## Mission

Build a practical, reproducible system for automatically improving agent skills through bounded optimization and automatic discovery of missing capabilities.

Current focus: Optimize the Edit Planning Skill while demonstrating closed-loop self-improvement (verification + diagnosis + adaptation).

---

## Core Principles

1. **Verification first** — Never accept an edit without measurable improvement.
2. **Bounded changes** — All edits must be small, auditable, and reversible.
3. **Reproducibility** — Every run must be deterministic or explicitly seeded.
4. **Targeted diagnosis** — Use contrastive analysis to identify which capabilities are missing.
5. **No silent failures** — Surface errors immediately.

---

## Key Components

- `skillopt_loop.py` — Main optimization loop with integrated capability diagnostic
- `capability_diagnostic.py` — TRACE-inspired contrastive capability discovery
- `llm_verifier_evaluator.py` — Real continuous scoring using token logit expectation
- `mock_evaluator.py` — Fast deterministic evaluator for development

---

## Running the System

```bash
# With mock evaluator (fast)
python skillopt_loop.py

# With real verifier (requires OPENAI_BASE_URL)
export OPENAI_BASE_URL=http://your-vllm-host:8000/v1
python skillopt_loop.py
```

---

## Extending the System

- Add new criteria in `criteria/`
- Extend `capability_diagnostic.py` for new domains
- Modify the reflection step in `skillopt_loop.py` to use diagnosed gaps

---

## Related Research

- SkillOpt (arXiv:2605.23904)
- TRACE (arXiv:2604.05336)
- LLM-as-a-Verifier (arXiv:2607.05391)

---

This file is intended for anyone working with or extending the public SkillOpt prototype.