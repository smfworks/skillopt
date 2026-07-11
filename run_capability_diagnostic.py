#!/usr/bin/env python3
"""
Example script: Run the TRACE-inspired capability diagnostic on SkillOpt trajectories.

This demonstrates how to use capability_diagnostic.py with real (or mock) data.
"""

from capability_diagnostic import run_capability_diagnostic

# Example trajectories (in practice these would come from skillopt_loop.py output)
mock_successful = [
    {"content": "Selected 2 high-impact hypotheses. Clear risk assessment. Executable edit plan."},
    {"content": "Prioritized argument structure over formatting. Good dependency analysis."},
]

mock_failed = [
    {"content": "Selected 6 hypotheses including minor formatting. No risk analysis."},
    {"content": "Tried to fix everything at once. Plan was vague and non-executable."},
    {"content": "Included low-impact changes while missing core argument weaknesses."},
]

print("Running Capability Diagnostic...\n")

gaps = run_capability_diagnostic(
    successful_trajectories=mock_successful,
    failed_trajectories=mock_failed,
    domain="article_editing",
    debug=True
)

print("\n=== Diagnosed Capability Gaps ===\n")
for i, gap in enumerate(gaps, 1):
    print(f"{i}. {gap.name}")
    print(f"   Coverage: {gap.failure_coverage:.0%}")
    print(f"   Description: {gap.description}")
    print(f"   Suggested Criterion: {gap.suggested_criterion}")
    print()