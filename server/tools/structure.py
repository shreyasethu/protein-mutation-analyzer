import json
from pathlib import Path
from models import StructureToolOutput


DATA_PATH = Path(__file__).parent.parent / "data" / "mutations.json"


def _load_mutations():
   with open(DATA_PATH) as f:
       return {m["id"]: m for m in json.load(f)}


def get_ddg_estimate(mutation_id: str) -> StructureToolOutput:
   mutations = _load_mutations()


   if mutation_id not in mutations:
       raise ValueError(f"Unknown mutation_id: {mutation_id}")


   record = mutations[mutation_id]
   ddg = record["ddg_estimate"]
   mut_aa = record["mut_aa"]


   # Stop codons are always maximally destabilizing
   if mut_aa == "*":
       return StructureToolOutput(
           ddg_estimate=ddg,
           stability_impact="destabilizing",
           confidence="high"
       )


   if ddg < -2.0:
       impact = "destabilizing"
       confidence = "high"
   elif ddg < -0.5:
       impact = "destabilizing"
       confidence = "medium"
   elif ddg <= 0.5:
       impact = "neutral"
       confidence = "medium"
   else:
       impact = "stabilizing"
       confidence = "low"


   return StructureToolOutput(
       ddg_estimate=ddg,
       stability_impact=impact,
       confidence=confidence
   )
