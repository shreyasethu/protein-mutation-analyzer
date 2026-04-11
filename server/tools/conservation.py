import json
from pathlib import Path

from models import ConservationToolOutput

DATA_PATH = Path(__file__).parent.parent / "data" / "mutations.json"


def _load_mutations():
    with open(DATA_PATH) as f:
        return {m["id"]: m for m in json.load(f)}


def get_conservation_score(mutation_id: str) -> ConservationToolOutput:
    mutations = _load_mutations()

    if mutation_id not in mutations:
        raise ValueError(f"Unknown mutation_id: {mutation_id}")

    mutation_record = mutations[mutation_id]
    score = mutation_record["phylop_score"]

    if score < -2.0:
        level = "high"
        interp = f"PhyloP of {score:.3f} indicates high evolutionary conservation — changes at this position are likely damaging."
    elif score < -0.5:
        level = "medium"
        interp = f"PhyloP of {score:.3f} indicates moderate conservation — interpret alongside structural and domain data."
    else:
        level = "low"
        interp = f"PhyloP of {score:.3f} indicates low conservation — this position tolerates variation across species."

    return ConservationToolOutput(
        phylop_score=score,
        conservation_level=level,
        interpretation=interp
    )