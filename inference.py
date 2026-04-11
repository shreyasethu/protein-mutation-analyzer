
"""
inference.py — Agent inference script for the Protein Mutation Analyzer environment.


Uses OpenEnv WebSocket protocol (state persists across reset→step).


WS message format (confirmed from openenv source):
 Reset:    {"type": "reset", "data": {"task_id": <int>}}
 Step:     {"type": "step",  "data": {"tool_name": "...", "tool_input": {...}}}
 Response: {"type": "observation", "data": {"observation": {...}, "reward": ..., "done": bool}}


Produces mandatory log lines:
 [START] task=<task_name> env=protein-mutation-analyzer model=<model_name>
 [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
 [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>


Usage:
 python inference.py


Environment variables:
 API_BASE_URL   — LLM endpoint base (default: Groq)
 MODEL_NAME     — model identifier
 HF_TOKEN       — bearer token / API key
 ENV_BASE_URL   — server base URL (default: http://localhost:7860)
"""


from __future__ import annotations


import asyncio
import json
import logging
import os
import sys


import websockets
from openai import OpenAI


# ── Configuration ──────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
API_KEY = HF_TOKEN or OPENAI_API_KEY
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
WS_BASE_URL  = ENV_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")


ENV_NAME  = "protein-mutation-analyzer"
MAX_STEPS = 6


VALID_TOOLS = {
   "get_conservation_score",
   "get_ddg_estimate",
   "get_domain_annotation",
   "submit_verdict",
}


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ── OpenAI client (works with Groq, HF, or any OpenAI-compatible endpoint) ────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a computational biology agent tasked with classifying protein mutations as Pathogenic, Benign, or Uncertain.


You have four tools available:
1. get_conservation_score — queries evolutionary conservation (PhyloP score). Negative PhyloP = highly conserved = stronger pathogenic signal.
2. get_ddg_estimate — queries structural stability impact (ΔΔG in kcal/mol). More negative ΔΔG = more destabilizing = stronger pathogenic signal.
3. get_domain_annotation — queries functional domain annotation. Critical domain mutations are more likely pathogenic.
4. submit_verdict — submits your final classification. Must provide verdict: "Pathogenic", "Benign", or "Uncertain".


Rules:
- You MUST call at least one query tool before submitting a verdict.
- Redundant tool calls (calling the same tool twice) are penalized.
- You have a step budget of 6. Exceeding budget results in a penalty.
- Gather enough evidence, then submit. Do not be redundant.


Response format — ONLY a JSON object, no prose, no markdown:
{"tool": "<tool_name>", "input": {"mutation_id": "<id>"}}
or for verdict:
{"tool": "submit_verdict", "input": {"mutation_id": "<id>", "verdict": "<Pathogenic|Benign|Uncertain>"}}"""




# ── LLM call (uses OpenAI client) ─────────────────────────────────────────────
def call_llm(messages: list[dict]) -> str:
   response = client.chat.completions.create(
       model=MODEL_NAME,
       messages=messages,
       max_tokens=256,
       temperature=0.0,
   )
   return response.choices[0].message.content.strip()




# ── Action parsing ─────────────────────────────────────────────────────────────
def parse_action(raw: str, mutation_id: str) -> dict | None:
   text = raw.strip()
   if text.startswith("```"):
       text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()


   try:
       parsed = json.loads(text)
   except json.JSONDecodeError:
       logger.warning("LLM non-JSON: %s", raw[:200])
       return None


   tool = parsed.get("tool", "")
   inp  = parsed.get("input", {})


   if tool not in VALID_TOOLS:
       logger.warning("Invalid tool: %s", tool)
       return None


   if "mutation_id" not in inp:
       inp["mutation_id"] = mutation_id


   if tool == "submit_verdict" and inp.get("verdict") not in ("Pathogenic", "Benign", "Uncertain"):
       logger.warning("Bad verdict: %s", inp.get("verdict"))
       return None


   return {"tool_name": tool, "tool_input": inp}




# ── Observation → prompt ───────────────────────────────────────────────────────
def obs_to_message(obs: dict) -> str:
   lines = [
       f"Mutation ID: {obs.get('mutation_id')}",
       f"Gene: {obs.get('gene')}  Position: {obs.get('position')}",
       f"Ref AA → Mut AA: {obs.get('ref_aa')} → {obs.get('mut_aa')}",
       f"Sequence context: {obs.get('sequence_context')}",
       f"Budget remaining: {obs.get('budget_remaining')}  Steps taken: {obs.get('steps_taken')}",
       f"Tools called so far: {obs.get('tools_called', [])}",
   ]
   if obs.get("conservation_result"):
       lines.append(f"Conservation (PhyloP): {obs['conservation_result']}")
   if obs.get("structure_result"):
       lines.append(f"Structure (ΔΔG): {obs['structure_result']}")
   if obs.get("domain_result"):
       lines.append(f"Domain annotation: {obs['domain_result']}")
   return "\n".join(lines)




# ── WebSocket helpers ──────────────────────────────────────────────────────────
async def ws_send_recv(ws, payload: dict) -> dict:
   """Send a message and wait for the observation response."""
   await ws.send(json.dumps(payload))
   for _ in range(5):
       raw = await asyncio.wait_for(ws.recv(), timeout=30)
       msg = json.loads(raw)
       if msg.get("type") == "observation":
           return msg
       if msg.get("type") == "error":
           raise RuntimeError(f"WS error: {msg.get('data', {}).get('message', msg)}")
   raise RuntimeError("No observation received after 5 messages")




def parse_ws_response(msg: dict) -> tuple[dict, float, bool]:
   """Extract (observation, reward, done) from a WS observation message."""
   data = msg.get("data", {})
   obs  = data.get("observation", {})
   done = bool(data.get("done", False) or obs.get("done", False) or obs.get("episode_done", False))


   reward_raw = data.get("reward")
   if isinstance(reward_raw, dict):
       total_reward = float(reward_raw.get("total_reward", 0.0) or 0.0)
   elif isinstance(reward_raw, (int, float)) and reward_raw is not None:
       total_reward = float(reward_raw)
   else:
       total_reward = 0.0


   return obs, total_reward, done




# ── Single task runner ─────────────────────────────────────────────────────────
async def run_task(task_id: int, task_name: str) -> None:
   print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}", flush=True)


   step = 0
   rewards: list[float] = []
   success = False


   try:
       async with websockets.connect(
           f"{WS_BASE_URL}/ws",
           ping_interval=20,
           ping_timeout=20,
           open_timeout=10,
       ) as ws:


           # ── Reset ──────────────────────────────────────────────────────
           try:
               reset_msg = await ws_send_recv(ws, {
                   "type": "reset",
                   "data": {"task_id": task_id},
               })
               obs, _, _ = parse_ws_response(reset_msg)
           except Exception as exc:
               logger.error("WS reset failed: %s", exc)
               print(f"[END] success=false steps={step} score=0.00 rewards=", flush=True)
               return


           mutation_id = obs.get("mutation_id", "unknown")
           messages = [{"role": "system", "content": SYSTEM_PROMPT}]
           no_op = {
               "tool_name": "get_conservation_score",
               "tool_input": {"mutation_id": mutation_id},
           }


           # ── Step loop ──────────────────────────────────────────────────
           while step < MAX_STEPS:
               step += 1
               error_msg = "null"
               action = None


               messages.append({"role": "user", "content": obs_to_message(obs)})


               # LLM call
               try:
                   raw = call_llm(messages)
                   messages.append({"role": "assistant", "content": raw})
                   action = parse_action(raw, mutation_id)
               except Exception as exc:
                   error_msg = str(exc).replace("\n", " ")[:120]


               if action is None:
                   error_msg = "parse_error" if error_msg == "null" else error_msg
                   action = no_op


               action_str = json.dumps(action, separators=(",", ":"))


               # Step the environment
               try:
                   step_msg = await ws_send_recv(ws, {
                       "type": "step",
                       "data": action,
                   })
                   obs, total_reward, done = parse_ws_response(step_msg)
               except Exception as exc:
                   error_msg = str(exc).replace("\n", " ")[:120]
                   total_reward = 0.0
                   done = False


               rewards.append(total_reward)
               print(
                   f"[STEP] step={step} action={action_str} "
                   f"reward={total_reward:.2f} done={str(done).lower()} error={error_msg}",
                   flush=True,
               )


               if done:
                   success = total_reward > 0.0
                   break


               await asyncio.sleep(0.3)


   except Exception as exc:
       logger.error("WebSocket connection error for %s: %s", task_name, exc)
       if not rewards:
           print(f"[END] success=false steps={step} score=0.00 rewards=", flush=True)
           return

   score = sum(rewards)
   score = max(0.0, min(1.0, score))

   rewards_str = ",".join(f"{r:.2f}" for r in rewards)
   print(
    f"[END] success={str(success).lower()} steps={step} "
    f"score={score:.2f} rewards={rewards_str}",
    flush=True,
)



# ── Main ───────────────────────────────────────────────────────────────────────
TASKS = [
   (1, "task_tier_1_easy"),
   (2, "task_tier_2_medium"),
   (3, "task_tier_3_hard"),
]




async def main_async() -> None:
   print(f"Running inference against {ENV_BASE_URL}", file=sys.stderr)
   for task_id, task_name in TASKS:
       await run_task(task_id, task_name)
       await asyncio.sleep(1)




if __name__ == "__main__":
   asyncio.run(main_async())
