
"""
adversary.py — Adversarial mutation designer.




After every 5 episodes:
1. Aggregate the mistake log into a weakness profile.
2. If there is a clear top weakness, call the LLM to generate 2–3 new
 mutation records that specifically target that weakness.
3. Append valid records to the environment's task pools.




The adversary never crashes the environment — all errors are logged and
execution continues silently.
"""




from __future__ import annotations




import json
import logging
import os
import re
import uuid
from typing import Any




import requests




logger = logging.getLogger(__name__)




# ── Mutation record JSON schema (as a string for the prompt) ──────────────────
MUTATION_SCHEMA = """
{
"id": "<string — unique, e.g. 'ADV_001'>",
"gene": "<string — gene symbol, e.g. 'BRCA2'>",
"position": <integer — amino acid position>,
"ref_aa": "<single-letter amino acid, e.g. 'R'>",
"mut_aa": "<single-letter amino acid or '*' for stop, e.g. 'C'>",
"sequence_context": "<string — 21-char window centred on the mutation, e.g. 'ACDEFGHIKLMNPQRSTVWY'>",
"phylop_score": <float — conservation score, positive=conserved, negative=variable>,
"ddg_estimate": <float — kcal/mol, negative=destabilizing>,
"domain_name": "<string — functional domain name or 'intergenic'>",
"domain_critical": <boolean>,
"clinvar_label": "<'Pathogenic' | 'Benign' | 'Uncertain'>",
"clinvar_confidence": "<'high' | 'medium' | 'low'>",
"deciding_factor": "<'conservation' | 'structure' | 'domain' | 'combined'>",
"task_tier": <1 | 2 | 3>
}
"""




# Few-shot examples baked in to the prompt (hard-coded representative records)
FEW_SHOT_EXAMPLES = """
Example 1 (structure is the deciding factor — highly destabilizing ΔΔG, ambiguous conservation):
{
"id": "MUT_EX1",
"gene": "TP53",
"position": 175,
"ref_aa": "R",
"mut_aa": "H",
"sequence_context": "VVRCPHHERCSDSDGLAPPQH",
"phylop_score": 0.8,
"ddg_estimate": -3.5,
"domain_name": "DNA-binding domain",
"domain_critical": true,
"clinvar_label": "Pathogenic",
"clinvar_confidence": "high",
"deciding_factor": "structure",
"task_tier": 2
}




Example 2 (conservation is the deciding factor — mild ΔΔG, strongly conserved):
{
"id": "MUT_EX2",
"gene": "BRCA1",
"position": 1700,
"ref_aa": "M",
"mut_aa": "V",
"sequence_context": "KQNMAVPALMQEEEARELKD",
"phylop_score": -4.2,
"ddg_estimate": -0.3,
"domain_name": "BRCT domain",
"domain_critical": true,
"clinvar_label": "Pathogenic",
"clinvar_confidence": "medium",
"deciding_factor": "conservation",
"task_tier": 2
}




Example 3 (benign — low conservation, neutral ΔΔG):
{
"id": "MUT_EX3",
"gene": "TTN",
"position": 12500,
"ref_aa": "A",
"mut_aa": "S",
"sequence_context": "LAEKASGDTQPVREMATLQP",
"phylop_score": 3.1,
"ddg_estimate": 0.1,
"domain_name": "I-band",
"domain_critical": false,
"clinvar_label": "Benign",
"clinvar_confidence": "high",
"deciding_factor": "conservation",
"task_tier": 1
}
"""








# ──────────────────────────────────────────────────────────────────────────────
# Weakness Profiler
# ──────────────────────────────────────────────────────────────────────────────




def build_weakness_profile(mistake_log: list[dict]) -> dict[str, float]:
  """
  Aggregate the mistake log into a weakness profile dictionary.




  Keys:
    skips_structure        — fraction of episodes where structure was deciding but agent skipped it
    skips_domain           — same for domain
    over_predicts_pathogenic — fraction of benign mutations labeled Pathogenic
    over_predicts_benign   — fraction of pathogenic mutations labeled Benign
    inefficient            — fraction of episodes where technician_score < 0.5
  """
  if not mistake_log:
      return {}




  n = len(mistake_log)
  skips_structure = 0
  skips_domain = 0
  over_pathogenic = 0
  over_benign = 0
  inefficient = 0




  for entry in mistake_log:
      tools = entry.get("tools_called", [])
      deciding = entry.get("deciding_factor", "")
      verdict = entry.get("submitted_verdict", "")
      truth = entry.get("ground_truth", "")
      tech_score = entry.get("technician_score", 1.0) or 1.0




      if deciding == "structure" and "get_ddg_estimate" not in tools:
          skips_structure += 1
      if deciding == "domain" and "get_domain_annotation" not in tools:
          skips_domain += 1
      if truth == "Benign" and verdict == "Pathogenic":
          over_pathogenic += 1
      if truth == "Pathogenic" and verdict == "Benign":
          over_benign += 1
      if tech_score < 0.5:
          inefficient += 1




  return {
      "skips_structure":         skips_structure / n,
      "skips_domain":            skips_domain / n,
      "over_predicts_pathogenic": over_pathogenic / n,
      "over_predicts_benign":    over_benign / n,
      "inefficient":             inefficient / n,
  }








def get_top_weakness(profile: dict[str, float]) -> tuple[str, float] | None:
  """Return (weakness_name, fraction) for the highest-fraction weakness, or None."""
  if not profile:
      return None
  top = max(profile.items(), key=lambda kv: kv[1])
  if top[1] < 0.2:  # Only act if at least 20 % of episodes show the weakness
      return None
  return top








# ──────────────────────────────────────────────────────────────────────────────
# Adversary LLM call
# ──────────────────────────────────────────────────────────────────────────────




WEAKNESS_DESCRIPTIONS = {
  "skips_structure": (
      "The agent frequently ignores structural stability data (ΔΔG) even when it is the "
      "decisive factor. Generate mutations where ΔΔG is highly destabilizing (< -2.0 kcal/mol) "
      "and conservation signal alone is ambiguous (phylop_score between -1.5 and 1.5), forcing "
      "the agent to call get_ddg_estimate to get the right answer. Set deciding_factor='structure'."
  ),
  "skips_domain": (
      "The agent frequently ignores domain annotation even when it is decisive. Generate "
      "mutations in critical functional domains where ΔΔG and conservation are both ambiguous, "
      "but domain_critical=true is what tips the balance. Set deciding_factor='domain'."
  ),
  "over_predicts_pathogenic": (
      "The agent labels too many benign mutations as Pathogenic. Generate clearly benign "
      "mutations: high phylop_score (> 2.5, poorly conserved), mild or neutral ΔΔG (> -0.5), "
      "non-critical domain, clinvar_label='Benign'. Make sure the benign signal is unambiguous."
  ),
  "over_predicts_benign": (
      "The agent labels too many pathogenic mutations as Benign. Generate clearly pathogenic "
      "mutations where at least two signals agree: low phylop_score (< -2.0) AND high ΔΔG "
      "destabilization (< -2.0), clinvar_label='Pathogenic'."
  ),
  "inefficient": (
      "The agent uses too many steps and wastes budget on redundant tool calls. Generate "
      "mutations where a single tool (conservation OR structure) provides a completely "
      "unambiguous signal, so the optimal strategy is 1 query + submit (2 steps total). "
      "Task_tier=1 or 2."
  ),
}








def _build_adversary_prompt(weakness_name: str, weakness_fraction: float) -> str:
  description = WEAKNESS_DESCRIPTIONS.get(
      weakness_name,
      f"The agent has a weakness called '{weakness_name}' (fraction={weakness_fraction:.2f})."
  )




  return f"""You are an adversarial mutation designer for a reinforcement learning benchmark.




## Task
Generate exactly 3 new protein mutation records in JSON format that specifically target the following weakness in the agent being tested:




## Weakness Description
{description}




Weakness frequency: {weakness_fraction:.0%} of recent episodes.




## JSON Schema for each record
{MUTATION_SCHEMA}




## Few-shot examples of well-formed records
{FEW_SHOT_EXAMPLES}




## Instructions
- Output ONLY a JSON array containing exactly 3 mutation records. No prose, no markdown, no code fences.
- Each record must have a unique id starting with "ADV_" followed by a UUID fragment.
- Each record must strictly match the schema above.
- The weakness described above must be the decisive factor in each record.
- Vary the gene, position, and amino acid changes across the 3 records.




Output the JSON array now:"""








def _validate_record(record: Any) -> bool:
  """Basic validation that a record has all required fields with correct types."""
  required = {
      "id": str,
      "gene": str,
      "position": int,
      "ref_aa": str,
      "mut_aa": str,
      "sequence_context": str,
      "phylop_score": (int, float),
      "ddg_estimate": (int, float),
      "domain_name": str,
      "domain_critical": bool,
      "clinvar_label": str,
      "clinvar_confidence": str,
      "deciding_factor": str,
      "task_tier": int,
  }
  VALID_LABELS = {"Pathogenic", "Benign", "Uncertain"}
  VALID_CONFIDENCE = {"high", "medium", "low"}
  VALID_FACTORS = {"conservation", "structure", "domain", "combined"}




  if not isinstance(record, dict):
      return False




  for field, expected_type in required.items():
      if field not in record:
          logger.debug("Adversary record missing field: %s", field)
          return False
      if not isinstance(record[field], expected_type):
          logger.debug("Adversary record field %s has wrong type", field)
          return False




  if record["clinvar_label"] not in VALID_LABELS:
      return False
  if record["clinvar_confidence"] not in VALID_CONFIDENCE:
      return False
  if record["deciding_factor"] not in VALID_FACTORS:
      return False
  if record["task_tier"] not in (1, 2, 3):
      return False




  return True








def call_adversary_llm(weakness_name: str, weakness_fraction: float) -> list[dict]:
  """
  Call the LLM (via HF router or Anthropic endpoint) to generate adversarial mutations.




  Returns a list of validated mutation records (may be empty if the call fails).
  """
  prompt = _build_adversary_prompt(weakness_name, weakness_fraction)




  api_base = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1")
  model    = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
  token    = os.getenv("HF_TOKEN", "")




  headers = {
      "Authorization": f"Bearer {token}",
      "Content-Type": "application/json",
  }
  payload = {
      "model": model,
      "messages": [{"role": "user", "content": prompt}],
      "max_tokens": 1500,
      "temperature": 0.7,
  }




  try:
      resp = requests.post(
          f"{api_base}/chat/completions",
          headers=headers,
          json=payload,
          timeout=60,
      )
      resp.raise_for_status()
      content = resp.json()["choices"][0]["message"]["content"].strip()
  except Exception as exc:
      logger.warning("Adversary LLM call failed: %s", exc)
      return []




  # Strip any accidental markdown fences
  content = re.sub(r"```(?:json)?", "", content).strip().rstrip("`")




  try:
      records = json.loads(content)
      if not isinstance(records, list):
          raise ValueError("Expected a JSON array")
  except Exception as exc:
      logger.warning("Adversary JSON parse failed: %s | raw=%s", exc, content[:300])
      return []




  # Validate each record; assign fresh IDs to avoid collisions
  valid = []
  for rec in records:
      if _validate_record(rec):
          rec["id"] = f"ADV_{uuid.uuid4().hex[:8].upper()}"
          valid.append(rec)
      else:
          logger.debug("Adversary record failed validation: %s", rec)




  logger.info("Adversary generated %d valid records for weakness '%s'", len(valid), weakness_name)
  return valid








# ──────────────────────────────────────────────────────────────────────────────
# Main entry point called by the environment
# ──────────────────────────────────────────────────────────────────────────────




def maybe_run_adversary(
  mistake_log: list[dict],
  task_pools: dict[int, list[dict]],
) -> dict:
  """
  Called by the environment after every episode.




  - Every 5 episodes: build weakness profile, identify top weakness,
    call LLM, append valid records to task_pools.
  - Returns the current weakness profile (for display / state tracking).
  - Never raises — all errors are caught and logged.
  """
  profile: dict[str, float] = {}




  if len(mistake_log) == 0 or len(mistake_log) % 5 != 0:
      return profile




  try:
      profile = build_weakness_profile(mistake_log)
      top = get_top_weakness(profile)
      if top is None:
          logger.info("Adversary: no significant weakness detected.")
          return profile




      weakness_name, weakness_fraction = top
      logger.info(
          "Adversary triggered: weakness='%s' fraction=%.2f",
          weakness_name, weakness_fraction,
      )




      new_records = call_adversary_llm(weakness_name, weakness_fraction)
      for rec in new_records:
          tier = rec.get("task_tier", 1)
          if tier in task_pools:
              task_pools[tier].append(rec)
              logger.info("Adversary appended record %s to tier %d pool", rec["id"], tier)




  except Exception as exc:
      logger.warning("Adversary encountered an unexpected error: %s", exc)




  return profile