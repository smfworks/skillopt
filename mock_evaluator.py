#!/usr/bin/env python3
"""
MockEvaluator — deterministic, realistic rubric scorer for SkillOpt prototyping.

Higher base scores so the optimization loop can demonstrate accept/reject behavior.
"""

import hashlib
from typing import Dict, Any


class MockEvaluator:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def _hash_to_scores(self, text: str, version_bonus: float = 0.0) -> Dict[str, float]:
        h = hashlib.sha256((text + str(self.seed)).encode()).hexdigest()
        scores = {}
        dims = ["A", "B", "C", "D", "E"]
        for i, dim in enumerate(dims):
            val = int(h[i*2:i*2+2], 16)
            score = 6.8 + (val / 255.0) * 2.2   # 6.8 – 9.0 range
            scores[dim] = round(score + version_bonus, 1)
        return scores

    def evaluate(self, article: str, article_id: str, skill_version: str = "v0", skill_text: str | None = None) -> Dict[str, Any]:
        bonus = 0.5 if skill_version == "v1" else 0.0
        scores = self._hash_to_scores(article, bonus)
        overall = round(sum(scores.values()) / 5, 1)

        if overall < 6.5:
            verdict = "weak"
        elif overall < 8.0:
            verdict = "pass"
        else:
            verdict = "strong"

        feedback = {
            dim: {
                "score": scores[dim],
                "strength": "Solid" if scores[dim] >= 7.5 else "Needs work",
                "weakness": "Minor gaps" if scores[dim] >= 7 else "Significant issues",
                "quote": ""
            }
            for dim in scores
        }

        below = [d for d, s in scores.items() if (d in "ABC" and s < 8) or (d in "DE" and s < 7)]

        return {
            "scores": scores,
            "overall": overall,
            "verdict": verdict,
            "feedback": feedback,
            "below_threshold": below,
            "summary": f"Mock evaluation of {article_id} ({skill_version}): {overall}/10.",
        }