from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
   from models import State




# ──────────────────────────────────────────────────────────────────────────────
# 1. Clinical Geneticist
# ──────────────────────────────────────────────────────────────────────────────


def score_geneticist(state: "State", submitted_verdict: str) -> float:
   tools_called = state.tools_called or []


   if "get_conservation_score" not in tools_called:
       return 0.0


   conservation = state.conservation_result
   if conservation is None:
       return 0.1


   phylop = conservation.phylop_score
   ground_truth = state.ground_truth_label


   strong_pathogenic_signal = phylop < -2.0
   strong_benign_signal = phylop > 2.0
   ambiguous = not strong_pathogenic_signal and not strong_benign_signal


   if strong_pathogenic_signal:
       if submitted_verdict == "Pathogenic":
           return 1.0
       elif submitted_verdict == "Uncertain":
           return 0.5
       else:
           return 0.1


   elif strong_benign_signal:
       if submitted_verdict == "Benign":
           return 1.0
       elif submitted_verdict == "Uncertain":
           return 0.5
       else:
           return 0.1


   else:
       if submitted_verdict == "Uncertain":
           return 0.7
       elif submitted_verdict == ground_truth:
           return 0.6
       else:
           return 0.3




# ──────────────────────────────────────────────────────────────────────────────
# 2. Structural Biologist
# ──────────────────────────────────────────────────────────────────────────────


def score_biologist(state: "State", submitted_verdict: str) -> float:
   tools_called = state.tools_called or []
   deciding_factor = state.deciding_factor
   ground_truth = state.ground_truth_label


   called_structure = "get_ddg_estimate" in tools_called
   structure = state.structure_result


   if deciding_factor == "structure" and not called_structure:
       return 0.0


   if not called_structure:
       if submitted_verdict == ground_truth:
           return 0.8
       elif submitted_verdict == "Uncertain":
           return 0.5
       else:
           return 0.4


   if structure is None:
       return 0.2


   ddg = structure.ddg_estimate


   if ddg < -2.0:
       if submitted_verdict == "Pathogenic":
           return 1.0
       elif submitted_verdict == "Uncertain":
           return 0.5
       else:
           return 0.1


   elif ddg > -0.5:
       if deciding_factor == "conservation":
           if submitted_verdict == ground_truth:
               return 0.9
           else:
               return 0.3
       else:
           if submitted_verdict in ("Benign", "Uncertain"):
               return 0.8
           else:
               return 0.4


   else:
       if submitted_verdict == ground_truth:
           return 0.75
       elif submitted_verdict == "Uncertain":
           return 0.6
       else:
           return 0.35




# ──────────────────────────────────────────────────────────────────────────────
# 3. Lab Technician (FIXED — stronger efficiency signal)
# ──────────────────────────────────────────────────────────────────────────────


def score_technician(state: "State", submitted_verdict: str) -> float:
   tools_called = state.tools_called or []
   steps_taken = state.steps_taken
   budget_remaining = state.budget_remaining


   if budget_remaining < 0:
       return 0.0


   unique_queries = [t for t in tools_called if t != "submit_verdict"]
   if len(unique_queries) == 0:
       return 0.1


   non_submit_steps = steps_taken - 1
   redundant_calls = max(0, non_submit_steps - len(unique_queries))


   # 🔥 KEY CHANGE: much sharper efficiency gradients
   if len(unique_queries) == 1:
       base_score = 1.0
   elif len(unique_queries) == 2:
       base_score = 0.75
   elif len(unique_queries) == 3:
       base_score = 0.40   # was 0.75 → now heavily penalized
   else:
       base_score = 0.15


   # stronger redundancy penalty
   redundancy_penalty = redundant_calls * 0.20


   score = base_score - redundancy_penalty
   return max(0.0, min(1.0, score))