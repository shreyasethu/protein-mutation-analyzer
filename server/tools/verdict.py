from models import VerdictToolOutput


VALID_VERDICTS = {"Pathogenic", "Benign", "Uncertain"}


def submit_verdict(mutation_id: str, verdict: str) -> VerdictToolOutput:
   if verdict not in VALID_VERDICTS:
       raise ValueError(
           f"Invalid verdict '{verdict}'. Must be one of: {sorted(VALID_VERDICTS)}"
       )


   return VerdictToolOutput(
       accepted=True,
       episode_done=True
   )
