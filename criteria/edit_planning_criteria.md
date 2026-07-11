# Edit Planning Skill — Decomposed Evaluation Criteria

**Skill:** `edit_planning_skill.md` (Triage + Concrete Edit Plan)  
**Source:** Bilevel-Autoresearch `domains/article_opt/pipeline/edit_planning.py`  
**Purpose:** Break the original two-phase skill into measurable sub-criteria for LLM-as-a-Verifier style evaluation.

---

## Phase 1: Triage Quality

### T1 — Hypothesis Prioritization
**Question:** Does the triage select the 2–3 hypotheses that would most improve the overall rubric score?

**Good (9–10):** Ruthlessly ranks hypotheses by expected impact; correctly identifies the highest-leverage changes.  
**Acceptable (7–8):** Reasonable selection with minor mis-ranking.  
**Poor (≤6):** Selects low-impact or redundant hypotheses; ignores high-impact ones.

### T2 — Risk Awareness
**Question:** Does the triage explicitly call out implementation risks and dependencies?

**Good (9–10):** Clearly states risks and notes ordering dependencies.  
**Acceptable (7–8):** Mentions at least one risk or dependency.  
**Poor (≤6):** No risk or dependency analysis.

### T3 — Rejection Rationale
**Question:** Are rejected hypotheses given a concise, defensible reason?

**Good (9–10):** One-sentence justification that references the article’s current state.  
**Acceptable (7–8):** Generic but plausible reason.  
**Poor (≤6):** No reason or circular reasoning.

---

## Phase 2: Edit Plan Quality

### P1 — Specificity
**Question:** Is every edit plan item specific enough that another editor could execute it without asking follow-up questions?

**Good (9–10):** Exact section, exact change type, exact original text to replace, exact new text to insert.  
**Acceptable (7–8):** Mostly specific but leaves minor ambiguity.  
**Poor (≤6):** Vague instructions (“improve the introduction”, “add an example”).

### P2 — Executability
**Question:** Is the “New Text” field ready-to-paste prose with no placeholders?

**Good (9–10):** Every “New Text” is final, complete sentences ready to insert.  
**Acceptable (7–8):** Minor placeholders that are easy to resolve.  
**Poor (≤6):** “[add example here]”, “[write X]”, or descriptive instructions instead of actual prose.

### P3 — Traceability
**Question:** Does every edit plan item clearly link back to a selected hypothesis (H1, H2, …)?

**Good (9–10):** Explicit “Hypothesis: H2 — …” line for every item.  
**Acceptable (7–8):** Implicit but recoverable from context.  
**Poor (≤6):** No clear mapping from edits to hypotheses.

### P4 — Constraint Adherence
**Question:** Does the plan respect the “no placeholders / ready-to-insert” constraint stated in the skill prompt?

**Good (9–10):** Zero violations.  
**Acceptable (7–8):** 1–2 minor violations that do not break executability.  
**Poor (≤6):** Multiple placeholder violations or instructions instead of prose.

---

## Composite Scoring

When using LLM-as-a-Verifier, we recommend the following criteria decomposition:

```python
criteria = {
    "Triage Prioritization": "Does the triage select the highest-impact hypotheses?",
    "Triage Risk Awareness": "Does the triage surface risks and dependencies?",
    "Edit Plan Specificity": "Is every edit plan item precise and unambiguous?",
    "Edit Plan Executability": "Is the New Text ready-to-paste with no placeholders?",
    "Traceability": "Does every edit clearly map back to a selected hypothesis?",
}
```

**Overall score** = average of the five criteria (or weighted average if desired).

---

## Usage in SkillOpt

When running the optimizer, pass the decomposed criteria to the verifier:

```python
evaluator = LLMVerifierEvaluator(repeats=3)
result = evaluator.evaluate(
    article=generated_edit_plan,
    article_id=run_id,
    criteria=load_criteria("criteria/edit_planning_criteria.md")
)
```

This enables the three scaling axes from LLM-as-a-Verifier:
- Score granularity (token-level expectation)
- Repeated evaluation (variance reduction)
- Criteria decomposition (bias/complexity reduction)