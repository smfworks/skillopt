#!/usr/bin/env python3
"""
Capability Diagnostic Module for SkillOpt

Inspired by TRACE (arXiv:2604.05336): Uses contrastive analysis of
successful vs. failed trajectories to identify missing capabilities.

This module is designed to be a lightweight diagnostic layer that can
be run on top of existing SkillOpt runs to surface targeted improvement areas.
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from llm_verifier_evaluator import LLMVerifierEvaluator


@dataclass
class CapabilityGap:
    name: str
    description: str
    failure_coverage: float  # % of failures this capability explains
    evidence: List[str]      # example failure snippets
    suggested_criterion: str # how to turn this into an evaluation criterion


class CapabilityDiagnostic:
    """
    Identifies missing capabilities by contrasting successful and failed trajectories.
    """

    def __init__(
        self,
        model: str = "unsloth/Qwen3.6-35B-A3B-NVFP4",
        base_url: str = "http://spark-56bc:8888/v1",
        max_capabilities: int = 8,
        debug: bool = False
    ):
        self.model = model
        self.base_url = base_url
        self.max_capabilities = max_capabilities
        self.debug = debug

        self.evaluator = LLMVerifierEvaluator(
            model=model,
            base_url=base_url,
            debug=debug
        )

    def diagnose(
        self,
        successful_trajectories: List[Dict],
        failed_trajectories: List[Dict],
        domain: str = "article_editing"
    ) -> List[CapabilityGap]:
        """
        Run contrastive capability discovery.

        Args:
            successful_trajectories: List of successful edit-plan runs
            failed_trajectories: List of failed edit-plan runs
            domain: Domain name for context (e.g., "article_editing")

        Returns:
            Ranked list of CapabilityGap objects
        """
        if not failed_trajectories:
            return []

        # Build contrastive prompt
        prompt = self._build_contrastive_prompt(
            successful_trajectories, failed_trajectories, domain
        )

        system = """You are an expert capability analyst for agent systems.
Your job is to identify the specific, actionable capabilities that explain
why some trajectories succeed while others fail.

Focus on concrete, trainable capabilities rather than vague concepts.
Rank them by how many failures they explain."""

        # Call the model
        response = self.evaluator._call_with_logprobs(prompt, system)
        if "error" in response:
            if self.debug:
                print(f"[CapabilityDiagnostic] Error: {response['error']}")
            return []

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._parse_capabilities(content)

    def _build_contrastive_prompt(
        self,
        successful: List[Dict],
        failed: List[Dict],
        domain: str
    ) -> str:
        """Build the contrastive analysis prompt."""

        success_examples = "\n\n".join([
            f"--- Success {i+1} ---\n{self._format_trajectory(t)}"
            for i, t in enumerate(successful[:3])
        ])

        failure_examples = "\n\n".join([
            f"--- Failure {i+1} ---\n{self._format_trajectory(t)}"
            for i, t in enumerate(failed[:5])
        ])

        prompt = f"""Domain: {domain}

You are given examples of successful and failed agent trajectories in this domain.

=== SUCCESSFUL TRAJECTORIES ===
{success_examples}

=== FAILED TRAJECTORIES ===
{failure_examples}

Task:
1. Identify 5–8 specific capabilities whose absence best explains the failures.
2. For each capability, estimate what percentage of failures it accounts for.
3. Provide 1–2 short evidence snippets from the failed trajectories.
4. Suggest how this capability could be turned into an evaluation criterion.

Output format (JSON):
[
  {{
    "name": "Clear Hypothesis Prioritization",
    "description": "Ability to select the 2-3 highest-impact hypotheses rather than trying too many at once.",
    "failure_coverage": 0.35,
    "evidence": ["Selected 5 hypotheses when only 2 were needed", "Included low-impact formatting changes alongside core argument issues"],
    "suggested_criterion": "Does the triage select at most 3 hypotheses, ranked by expected impact?"
  }},
  ...
]

Only output the JSON array. Be specific and actionable."""

        return prompt

    def _format_trajectory(self, trajectory: Dict) -> str:
        """Format a trajectory for the prompt."""
        if isinstance(trajectory, dict):
            # Assume it has 'content' or similar
            content = trajectory.get("content", str(trajectory))
            return str(content)[:800]
        return str(trajectory)[:800]

    def _parse_capabilities(self, content: str) -> List[CapabilityGap]:
        """Parse the JSON output into CapabilityGap objects."""
        try:
            # Try to extract JSON array
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                data = json.loads(content)

            gaps = []
            for item in data[:self.max_capabilities]:
                gap = CapabilityGap(
                    name=item.get("name", "Unknown Capability"),
                    description=item.get("description", ""),
                    failure_coverage=float(item.get("failure_coverage", 0.0)),
                    evidence=item.get("evidence", []),
                    suggested_criterion=item.get("suggested_criterion", "")
                )
                gaps.append(gap)

            # Sort by failure coverage
            gaps.sort(key=lambda x: x.failure_coverage, reverse=True)
            return gaps

        except Exception as e:
            if self.debug:
                print(f"[CapabilityDiagnostic] Parse error: {e}")
                print(f"Raw content: {content[:500]}")
            return []

    def to_criteria(self, gaps: List[CapabilityGap]) -> Dict[str, str]:
        """Convert diagnosed gaps into evaluation criteria format."""
        criteria = {}
        for gap in gaps:
            if gap.suggested_criterion:
                key = gap.name.replace(" ", "_").lower()
                criteria[key] = gap.suggested_criterion
        return criteria


# Convenience function
def run_capability_diagnostic(
    successful: List[Dict],
    failed: List[Dict],
    domain: str = "article_editing",
    **kwargs
) -> List[CapabilityGap]:
    """Quick helper function."""
    diagnostic = CapabilityDiagnostic(**kwargs)
    return diagnostic.diagnose(successful, failed, domain)