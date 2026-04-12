# environment.py

import json
import random
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

from models import (
    State,
    ProteinMutationAnalyzerObservation,
    ConservationToolOutput,
    StructureToolOutput,
    DomainToolOutput,
)

from server.tools.conservation import get_conservation_score as local_conservation
from server.tools.structure import get_ddg_estimate as local_structure
from server.tools.domain import get_domain_annotation as local_domain
from server.tools.verdict import submit_verdict

from openenv.core.env_server.interfaces import Environment as OpenEnvEnvironment


GLOBAL_STATE = {}

API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
HF_TOKEN = os.getenv("HF_TOKEN")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN) if API_BASE_URL and HF_TOKEN else None

DATA_PATH = Path(__file__).parent / "data" / "mutations.json"

TOOL_COSTS = {
    "get_conservation_score": 1.0,
    "get_ddg_estimate": 2.0,
    "get_domain_annotation": 1.0,
    "submit_verdict": 0.0,
}

STEP_BUDGET = 6.0


def call_model(prompt: str):
    if client is None or MODEL_NAME is None:
        return None
    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # deterministic per spec
            max_tokens=60,
        )
        return res.choices[0].message.content
    except Exception:
        return None


class ProteinMutationAnalyzerEnvironment(OpenEnvEnvironment):
    def __init__(self):
        with open(DATA_PATH) as f:
            all_mutations = json.load(f)

        self._mutations = {m["id"]: m for m in all_mutations}

        self.task_pools = {
            1: [m for m in all_mutations if m["task_tier"] == 1],
            2: [m for m in all_mutations if m["task_tier"] == 2],
            3: [m for m in all_mutations if m["task_tier"] == 3],
        }

        self._state: Optional[State] = None

    # ───────── RESET ─────────
    def reset(self, seed=None, episode_id=None, **kwargs):
        task_id = kwargs.get("task_id", random.choice([1, 2, 3]))
        pool = self.task_pools.get(task_id, self.task_pools[1])
        record = random.choice(pool)

        self._state = State(
            mutation_id=record["id"],
            gene=record["gene"],
            position=record["position"],
            ref_aa=record["ref_aa"],
            mut_aa=record["mut_aa"],
            sequence_context=record["sequence_context"],
            conservation_result=None,
            structure_result=None,
            domain_result=None,
            steps_taken=0,
            step_budget=int(STEP_BUDGET),
            budget_spent=0.0,
            budget_remaining=STEP_BUDGET,
            tools_called=[],
            episode_done=False,
            ground_truth_label=record["clinvar_label"],
            deciding_factor=record["deciding_factor"],
            clinvar_confidence=record["clinvar_confidence"],
            task_tier=task_id,
            mistake_log=[],
            adversary_weakness_profile={},
        )

        GLOBAL_STATE[self._state.mutation_id] = self._state
        return self._to_observation()

    # ───────── STEP ─────────
    def step(self, action, timeout_s=None, **kwargs):
        tool_input = action.tool_input or {}
        mutation_id = tool_input.get("mutation_id")

        if not mutation_id or mutation_id not in GLOBAL_STATE:
            raise RuntimeError("Call reset() before step()")

        self._state = GLOBAL_STATE[mutation_id]

        if self._state.episode_done:
            return self._to_observation()

        tool_name = action.tool_name or ""
        already_called = tool_name in self._state.tools_called

        try:
            # ✅ REAL DATA + LLM INTERPRETATION

            if tool_name == "get_conservation_score":
                data = local_conservation(mutation_id)

                explanation = call_model(
                    f"Explain conservation impact briefly. Score: {data.phylop_score}"
                )

                self._state.conservation_result = ConservationToolOutput(
                    phylop_score=data.phylop_score,
                    conservation_level=data.conservation_level,
                    interpretation=explanation or data.interpretation,
                )

            elif tool_name == "get_ddg_estimate":
                data = local_structure(mutation_id)

                explanation = call_model(
                    f"Explain protein stability impact for ddg {data.ddg_estimate}"
                )

                self._state.structure_result = StructureToolOutput(
                    ddg_estimate=data.ddg_estimate,
                    stability_impact=data.stability_impact,
                    confidence=data.confidence,
                )

            elif tool_name == "get_domain_annotation":
                data = local_domain(mutation_id)

                explanation = call_model(
                    f"Explain functional importance of domain {data.domain_name}"
                )

                self._state.domain_result = DomainToolOutput(
                    domain_name=data.domain_name,
                    is_critical=data.is_critical,
                    function_description=explanation or data.function_description,
                )

            elif tool_name == "submit_verdict":
                verdict = tool_input.get("verdict", "")
                
                submit_verdict(mutation_id, verdict)

                self._state.episode_done = True
                self._state.steps_taken += 1

                from server.grader.grader import compute_reward
                final = compute_reward(self._state, verdict)

                return self._to_observation(reward=final.total_reward)

        except Exception:
            return self._to_observation()

        # ───────── bookkeeping ─────────
        cost = TOOL_COSTS[tool_name]
        self._state.budget_spent += cost
        self._state.budget_remaining -= cost
        self._state.steps_taken += 1

        if not already_called:
            self._state.tools_called.append(tool_name)
        

        deciding = self._state.deciding_factor

        # ───────── reward ─────────
        if already_called:
            step_reward = 0.0
        elif tool_name == "get_conservation_score":
            score = self._state.conservation_result.phylop_score
            step_reward = 0.08 if abs(score) > 2 else 0.02
            if deciding in ("conservation", "combined"):
                step_reward += 0.05
        elif tool_name == "get_ddg_estimate":
            ddg = self._state.structure_result.ddg_estimate
            step_reward = 0.08 if ddg < -2.0 else 0.06 if ddg > -0.5 else 0.02
            if deciding in ("structure", "combined"):
                step_reward += 0.05
        elif tool_name == "get_domain_annotation":
            step_reward = 0.07 if self._state.domain_result.is_critical else 0.02
            if deciding in ("domain", "combined"):
                step_reward += 0.05
        else:
            step_reward = 0.01

        GLOBAL_STATE[self._state.mutation_id] = self._state

        return self._to_observation(reward=round(step_reward, 4))

    # ───────── STATE ─────────
    def state(self):
        if self._state is None:
            return {"episode_id": None, "step_count": 0}
        print("STATE BEFORE GRADER:", self._state)
        

        return {
            "episode_id": self._state.mutation_id,
            "step_count": self._state.steps_taken,
        }

    # ───────── OBS ─────────
    def _to_observation(self, reward=None):
        s = self._state
        print("STATE BEFORE GRADER:", self._state)

        if reward is not None:
            reward = max(0.0, min(1.0, float(reward)))

        return ProteinMutationAnalyzerObservation(
            mutation_id=s.mutation_id,
            gene=s.gene,
            position=s.position,
            ref_aa=s.ref_aa,
            mut_aa=s.mut_aa,
            sequence_context=s.sequence_context,
            conservation_result=s.conservation_result,
            structure_result=s.structure_result,
            domain_result=s.domain_result,
            steps_taken=s.steps_taken,
            step_budget=s.step_budget,
            budget_spent=s.budget_spent,
            budget_remaining=s.budget_remaining,
            tools_called=list(s.tools_called),
            episode_done=s.episode_done,
            done=s.episode_done,
            reward=reward,
        )