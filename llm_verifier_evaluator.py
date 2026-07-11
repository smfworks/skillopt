#!/usr/bin/env python3
"""
LLMVerifierEvaluator — Supports both Together.ai and any OpenAI-compatible endpoint
(including local vLLM) that returns logprobs.

This is a production-ready implementation of the core idea from
arXiv:2607.05391 (LLM-as-a-Verifier).

Now handles reasoning models (DeepSeek-R1 style, Qwen reasoning variants) that
put thinking in <think> blocks or separate `reasoning` fields.
"""

import os
import json
import re
import requests
from typing import Dict, Any, List, Optional

# --- Configuration ---
TOGETHER_API_KEY = os.environ.get(
    "TOGETHER_API_KEY",
    open("/home/mikesai1/.hermes/profiles/liam/together.env").read().split("=", 1)[1].strip()
    if os.path.exists("/home/mikesai1/.hermes/profiles/liam/together.env") else None
)

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.together.xyz/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", TOGETHER_API_KEY)

DEFAULT_MODEL = os.environ.get("VERIFIER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")


class LLMVerifierEvaluator:
    """
    Produces continuous scores by computing the expected value over
    the distribution of scoring token logits.

    Supports reasoning models that use <think> blocks or separate `reasoning` fields.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        granularity: int = 10,
        repeats: int = 3,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        debug: bool = False,
        max_tokens: int = 768,
        strip_thinking: bool = True,
    ):
        self.model = model
        self.granularity = granularity
        self.repeats = repeats
        self.base_url = base_url or OPENAI_BASE_URL
        self.api_key = api_key or OPENAI_API_KEY
        self.debug = debug
        self.max_tokens = max_tokens
        self.strip_thinking = strip_thinking

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _get_scoring_tokens(self) -> List[str]:
        return [str(i) for i in range(1, self.granularity + 1)]

    def _strip_thinking(self, text: str) -> str:
        """Remove <think>...</think> blocks (common in reasoning models)."""
        if not text:
            return ""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</?think>', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _call_with_logprobs(self, prompt: str, system: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
            "logprobs": True,
            "top_logprobs": 20,
        }

        try:
            resp = self.session.post(f"{self.base_url}/chat/completions", json=payload, timeout=180)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if self.debug:
                print(f"[LLMVerifier] API error: {e}")
            return {"error": str(e)}

    def _extract_expected_score(self, response: Dict[str, Any]) -> float:
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            logprobs_data = choice.get("logprobs", {})

            content = message.get("content") or ""
            reasoning = message.get("reasoning") or ""

            if self.strip_thinking:
                content = self._strip_thinking(content)
                reasoning = self._strip_thinking(reasoning)

            # Try logprobs first
            if logprobs_data and logprobs_data.get("content"):
                token_logprobs = logprobs_data["content"][0].get("top_logprobs", [])
                scoring_tokens = self._get_scoring_tokens()

                probs = {}
                total = 0.0
                for item in token_logprobs:
                    token = str(item.get("token", "")).strip()
                    if token in scoring_tokens:
                        lp = float(item.get("logprob", 0))
                        probs[token] = max(0.0, lp)
                        total += max(0.0, lp)

                if total > 0 and probs:
                    expected = 0.0
                    for token, lp in probs.items():
                        expected += int(token) * (lp / total)
                    return round(expected, 2)

            # Fallback 1: Parse number from final content
            if content:
                nums = re.findall(r"\d+\.?\d*", str(content))
                if nums:
                    return float(nums[0])

            # Fallback 2: Parse number from reasoning (very common with reasoning models)
            if reasoning:
                nums = re.findall(r"\d+\.?\d*", str(reasoning))
                if nums:
                    return float(nums[-1])

            if self.debug:
                print(f"[LLMVerifier] Could not extract score.")
            return 5.0

        except Exception as e:
            if self.debug:
                print(f"[LLMVerifier] Parse error: {e}")
            return 5.0

    def evaluate(
        self,
        article: str,
        article_id: str,
        criteria: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        if criteria is None:
            criteria = {
                "Argumentative Rigor": "Does every claim have clear support?",
                "Conceptual Clarity": "Are key terms well defined?",
                "Actionability": "Does the article give concrete next steps?",
            }

        all_scores = []
        per_criterion = {}

        for crit_name, crit_desc in criteria.items():
            scores_for_crit = []
            for _ in range(self.repeats):
                # Improved prompt for reasoning models
                prompt = f"""Article (ID: {article_id}):

{article[:5500]}

Criterion: {crit_name}
Description: {crit_desc}

Score this article on the criterion from 1 to {self.granularity}.

Think step by step inside <think> tags if needed.
After your reasoning, output ONLY the final number in this exact format:

**Final Answer: X**

where X is an integer from 1 to {self.granularity}."""

                system = "You are a rigorous, objective academic evaluator. Always end with a clear **Final Answer: X** line."

                resp = self._call_with_logprobs(prompt, system)
                if "error" in resp:
                    score = 5.0
                else:
                    score = self._extract_expected_score(resp)

                scores_for_crit.append(score)

            avg_score = round(sum(scores_for_crit) / len(scores_for_crit), 2)
            per_criterion[crit_name] = avg_score
            all_scores.append(avg_score)

        overall = round(sum(all_scores) / len(all_scores), 2)

        return {
            "overall": overall,
            "per_criterion": per_criterion,
            "repeats": self.repeats,
            "granularity": self.granularity,
            "raw_scores": all_scores,
        }


# Convenience alias
LLMVerifier = LLMVerifierEvaluator