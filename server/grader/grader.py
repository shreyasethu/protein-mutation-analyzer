"""
grader.py — Aggregates three persona scores into a final RewardBreakdown.


Weights:
Clinical Geneticist  → 0.40
Structural Biologist → 0.25
Lab Technician       → 0.35


ClinVar confidence scaling:
high   → full score (×1.00)
medium → capped at 0.85
low    → capped at 0.70
"""


from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
   from models import State, RewardBreakdown




GENETICIST_WEIGHT = 0.40
BIOLOGIST_WEIGHT  = 0.25   # ↓ reduced
TECHNICIAN_WEIGHT = 0.35   # ↑ increased




CONFIDENCE_SCALE = {
   "high":   1.00,
   "medium": 0.85,
   "low":    0.70,
}




def _weighted_and_scaled(
   geneticist_score: float,
   biologist_score: float,
   technician_score: float,
   clinvar_confidence: str,
) -> float:
   weighted = (
       GENETICIST_WEIGHT * geneticist_score
       + BIOLOGIST_WEIGHT  * biologist_score
       + TECHNICIAN_WEIGHT * technician_score
   )
   cap = CONFIDENCE_SCALE.get(clinvar_confidence.lower(), 1.00)
   return round(min(weighted, cap), 4)




def compute_reward(state: "State", submitted_verdict: str) -> "RewardBreakdown":
   """
   Deterministic reward computation using persona scorers only.
   """
   from models import RewardBreakdown
   from server.grader.personas import (
       score_geneticist, score_biologist, score_technician
   )


   clinvar_confidence = getattr(state, "clinvar_confidence", "high") or "high"


   geneticist_score = score_geneticist(state, submitted_verdict)
   biologist_score  = score_biologist(state, submitted_verdict)
   technician_score = score_technician(state, submitted_verdict)


   final_reward = _weighted_and_scaled(
       geneticist_score,
       biologist_score,
       technician_score,
       clinvar_confidence,
   )


   return RewardBreakdown(
       geneticist_score=round(geneticist_score, 4),
       biologist_score=round(biologist_score, 4),
       technician_score=round(technician_score, 4),
       total_reward=final_reward,
       step_reward=0.0,
       redundancy_penalty=0.0,
       budget_penalty=0.0,
   )
