#!/usr/bin/env python3
"""
SkillOpt prototype v0.13 — Integrated with TRACE-inspired Capability Diagnostic

- Real LLM-as-a-Verifier on DGX Spark
- Automatic discovery of missing capabilities from failed trajectories
- New criteria are generated and added dynamically
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

BILEVEL_ROOT = "/home/mikesai1/workspace/Bilevel-Autoresearch"
sys.path.insert(0, BILEVEL_ROOT)

from mock_evaluator import MockEvaluator
from llm_verifier_evaluator import LLMVerifierEvaluator
from capability_diagnostic import CapabilityDiagnostic, CapabilityGap

CONFIG = {
    "max_epochs": 5,
    "rollout_batch_size": 3,
    "textual_lr": 2,

    # Real Verifier Configuration (DGX Spark)
    "use_real_verifier": True,
    "verifier_repeats": 2,
    "verifier_granularity": 10,
    "verifier_base_url": "http://spark-56bc:8888/v1",
    "verifier_model": "unsloth/Qwen3.6-35B-A3B-NVFP4",

    # Capability Diagnostic (TRACE-inspired)
    "use_capability_diagnostic": True,
    "diagnostic_max_gaps": 3,
}


def load_skill(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def save_skill(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def load_articles(limit: int = 5) -> List[Dict]:
    articles_dir = os.path.join(BILEVEL_ROOT, "articles")
    files = [f for f in os.listdir(articles_dir) if f.endswith(".md") and not f.startswith("README")]
    files = sorted(files)[:limit]
    articles = []
    for fname in files:
        with open(os.path.join(articles_dir, fname), "r") as f:
            articles.append({
                "id": fname.replace(".md", ""),
                "content": f.read(),
            })
    return articles


def get_evaluator(base_criteria: Dict[str, str] = None):
    if CONFIG["use_real_verifier"]:
        print("[Verifier] Using REAL LLM-as-a-Verifier on DGX Spark")
        print(f"           Base URL: {CONFIG['verifier_base_url']}")
        print(f"           Model:    {CONFIG['verifier_model']}")
        return LLMVerifierEvaluator(
            model=CONFIG["verifier_model"],
            repeats=CONFIG["verifier_repeats"],
            granularity=CONFIG["verifier_granularity"],
            base_url=CONFIG["verifier_base_url"],
        )
    else:
        print("[Verifier] Using MockEvaluator (deterministic)")
        return MockEvaluator(seed=42)


def rollout(skill: str, articles: List[Dict], evaluator, skill_version: str) -> List[Dict]:
    trajectories = []
    for art in articles:
        result = evaluator.evaluate(art["content"], art["id"])
        trajectories.append({
            "article_id": art["id"],
            "skill_version": skill_version,
            "rubric_score": result.get("overall", 0.0),
            "raw_result": result,
            "success": result.get("overall", 0) >= 6.5,
        })
    return trajectories


def run_capability_diagnostic(trajectories: List[Dict]) -> List[CapabilityGap]:
    """Run diagnostic on collected trajectories."""
    successful = [t for t in trajectories if t.get("success", False)]
    failed = [t for t in trajectories if not t.get("success", False)]

    if not failed or len(successful) < 2:
        return []

    print(f"[Diagnostic] Running on {len(successful)} successful vs {len(failed)} failed trajectories...")

    diagnostic = CapabilityDiagnostic(
        model=CONFIG["verifier_model"],
        base_url=CONFIG["verifier_base_url"],
        max_capabilities=CONFIG["diagnostic_max_gaps"],
        debug=False
    )

    gaps = diagnostic.diagnose(successful, failed, domain="article_editing")
    return gaps


def reflect(trajectories: List[Dict], rejected_buffer: List[Dict], meta: str, new_criteria: List[str] = None) -> List[Dict]:
    """Propose edits, now informed by diagnosed capability gaps."""
    base_edits = [
        {"type": "replace", "target": "TRIAGE_SYSTEM", "new_text": "Be even more ruthless.", "utility": 0.12},
        {"type": "add", "target": "triage_prompt", "new_text": "Prefer depth over breadth.", "utility": 0.09},
    ]

    if new_criteria:
        for crit in new_criteria[:2]:  # Limit to top 2 new criteria
            base_edits.append({
                "type": "add",
                "target": "evaluation_criteria",
                "new_text": f"New criterion from diagnostic: {crit}",
                "utility": 0.15
            })

    return base_edits


def apply_bounded_edits(skill: str, edits: List[Dict], lr: int) -> str:
    return skill + "\n\n# Optimized v1 (with diagnostic)"


def validate(candidate_skill: str, selection_articles: List[Dict], evaluator, skill_version: str, criteria: Dict[str, str] = None) -> float:
    scores = []
    for art in selection_articles:
        result = evaluator.evaluate(art["content"], art["id"], criteria=criteria)
        scores.append(result.get("overall", 0.0))
    return sum(scores) / len(scores) if scores else 0.0


def run_skillopt(skill_path: str):
    print(f"[SkillOpt v0.13] Starting with integrated Capability Diagnostic at {datetime.now(timezone.utc).isoformat()}")
    print(f"[Config] {CONFIG}")

    evaluator = get_evaluator()

    # Base criteria (can be expanded by diagnostic)
    base_criteria = {
        "Argumentative Rigor": "Does every claim have clear support?",
        "Conceptual Clarity": "Are key terms well defined?",
        "Actionability": "Does the article give concrete next steps?",
    }

    all_articles = load_articles(limit=5)
    print(f"[Data] Loaded {len(all_articles)} real articles from Bilevel repo")

    train = all_articles[:3]
    selection = all_articles[3:5]

    current_skill = load_skill(skill_path)
    best_skill = current_skill
    best_score = 0.0
    rejected_buffer: List[Dict] = []
    meta_guidance = ""
    current_version = "v0"

    discovered_criteria: List[str] = []

    for epoch in range(CONFIG["max_epochs"]):
        print(f"\n=== Epoch {epoch+1}/{CONFIG['max_epochs']} ===")

        trajectories = rollout(current_skill, train, evaluator, current_version)
        scores = [t["rubric_score"] for t in trajectories]
        print(f"[Rollout] Scores: {scores}")

        # === New: Run Capability Diagnostic ===
        new_gaps = []
        if CONFIG["use_capability_diagnostic"]:
            new_gaps = run_capability_diagnostic(trajectories)
            if new_gaps:
                print(f"[Diagnostic] Discovered {len(new_gaps)} capability gaps:")
                for gap in new_gaps:
                    print(f"  - {gap.name} (coverage: {gap.failure_coverage:.0%})")
                    discovered_criteria.append(gap.suggested_criterion)

        # Merge new criteria
        current_criteria = base_criteria.copy()
        if discovered_criteria:
            for i, crit in enumerate(discovered_criteria[-3:]):  # Use last 3 discovered
                current_criteria[f"discovered_{i}"] = crit

        edits = reflect(trajectories, rejected_buffer, meta_guidance, discovered_criteria)
        candidate = apply_bounded_edits(current_skill, edits, CONFIG["textual_lr"])

        val_score = validate(candidate, selection, evaluator, "v1", criteria=current_criteria)
        current_val = validate(current_skill, selection, evaluator, current_version, criteria=current_criteria)

        print(f"[Validation] Current={current_val:.2f}  Candidate={val_score:.2f}")

        if val_score > current_val:
            current_skill = candidate
            current_version = "v1"
            if val_score > best_score:
                best_score = val_score
                best_skill = candidate
            print(f"[Accept] New best validation score: {val_score:.2f}")
        else:
            rejected_buffer.append({"edits": edits, "score_drop": current_val - val_score})
            print(f"[Reject] Score dropped by {current_val - val_score:.2f}")

    save_skill("best_edit_planning_skill.md", best_skill)
    print(f"\n[Done] Exported best_edit_planning_skill.md (best validation score: {best_score:.2f})")

    if discovered_criteria:
        print(f"\n[Summary] Total new criteria discovered during run: {len(discovered_criteria)}")


if __name__ == "__main__":
    run_skillopt(skill_path="edit_planning_skill.md")