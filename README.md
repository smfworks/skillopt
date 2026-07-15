# SkillOpt: Self-Optimizing Agent Skills

> 📌 **SMF skill-optimizer family (2026-07-15):** Related repos include `skillopt-content`, `smf-SkillTrain`, and SkillOpt patterns in `smf-forgewright`.  
> **Canon direction:** treat **skillopt** as the primary open implementation; avoid forking effort across three optimizers without a written merge plan.


A practical implementation of **SkillOpt** (arXiv:2605.23904) with **TRACE-inspired capability diagnosis** (arXiv:2604.05336) and **real continuous verification** via LLM-as-a-Verifier (arXiv:2607.05391).

## Overview

This repository contains a working prototype for automatically improving agent skills through:

- Bounded text-space optimization (`add` / `delete` / `replace` edits)
- Real continuous scoring using token logit expectation
- Automatic discovery of missing capabilities from failed trajectories
- Dynamic generation of new evaluation criteria

## Key Features

- **Real Verifier**: Runs on a remote vLLM instance (DGX Spark) with support for reasoning models.
- **Capability Diagnostic**: Contrastive analysis of successful vs. failed runs to identify capability gaps (inspired by TRACE).
- **Closed-Loop Improvement**: The system can now diagnose its own weaknesses and generate new evaluation criteria automatically.
- **Production-Ready Structure**: Includes `AGENTS.md`, decomposed criteria, and clear extension points.

## Repository Structure

```
skillopt-public/
├── skillopt_loop.py              # Main optimization loop (v0.13)
├── capability_diagnostic.py      # TRACE-style capability discovery
├── llm_verifier_evaluator.py     # Real continuous scoring
├── mock_evaluator.py             # Fast deterministic evaluator
├── AGENTS.md                     # Project instructions & conventions
├── criteria/                     # Decomposed evaluation criteria
├── run_capability_diagnostic.py  # Example usage of the diagnostic
└── README.md
```

## Quick Start

### 1. Using the Mock Evaluator (Fast Iteration)

```bash
python skillopt_loop.py
```

### 2. Using Real Continuous Scoring

Set the following environment variables:

```bash
export OPENAI_BASE_URL=http://your-vllm-host:8000/v1
export VERIFIER_MODEL=your-model-name
python skillopt_loop.py
```

### 3. Running the Capability Diagnostic

```bash
python run_capability_diagnostic.py
```

## Philosophy

This project follows a "build in public" approach. Every significant research step — paper review, implementation, and integration — is documented so the community can follow along and build upon the work.

## Related Papers

- [SkillOpt: Executive Strategy for Self-Evolving Agent Skills](https://arxiv.org/abs/2605.23904)
- [TRACE: Capability-Targeted Agentic Training](https://arxiv.org/abs/2604.05336)
- [LLM-as-a-Verifier: A General-Purpose Verification Framework](https://arxiv.org/abs/2607.05391)

## License

MIT

## Citation

If you use this work, please consider citing the original papers and linking back to this repository.