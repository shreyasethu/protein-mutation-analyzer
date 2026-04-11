"""
train.py — FIXED version aligned with your inference + environment.


Fully compatible with:
- inference.py logic
- WebSocket protocol
- action format
- reward parsing


This ensures training ≈ inference behavior.
"""


from __future__ import annotations


import asyncio
import json
import logging
import os
from typing import List


import requests
import websockets


from training.curriculum import get_task_id




# ── CONFIG ─────────────────────────────────────────────────────────────


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN", "")


ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
WS_BASE_URL  = ENV_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")


MAX_STEPS = 6
TOTAL_EPISODES = 100


VALID_TOOLS = {
   "get_conservation_score",
   "get_ddg_estimate",
   "get_domain_annotation",
   "submit_verdict",
}


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)




# ── SAME SYSTEM PROMPT AS inference.py ─────────────────────────────────


SYSTEM_PROMPT = """You are a computational biology agent tasked with classifying protein mutations as Pathogenic, Benign, or Uncertain.


You have four tools available:
1. get_conservation_score
2. get_ddg_estimate
3. get_domain_annotation
4. submit_verdict


Rules:
- You MUST call at least one query tool before submitting a verdict.
- Redundant tool calls are penalized.
- You have a step budget of 6.


Response format — ONLY JSON:
{"tool": "<tool_name>", "input": {...}}
"""




# ── SAME LLM CALL ──────────────────────────────────────────────────────


def call_llm(messages: List[dict]) -> str:
   headers = {
       "Authorization": f"Bearer {HF_TOKEN}",
       "Content-Type": "application/json",
   }


   payload = {
       "model": MODEL_NAME,
       "messages": messages,
       "max_tokens": 256,
       "temperature": 0.0,  # deterministic for training
   }


   resp = requests.post(
       f"{API_BASE_URL}/chat/completions",
       headers=headers,
       json=payload,
       timeout=60,
   )
   resp.raise_for_status()


   return resp.json()["choices"][0]["message"]["content"].strip()




# ── SAME ACTION PARSER AS inference.py ─────────────────────────────────


def parse_action(raw: str, mutation_id: str):
   text = raw.strip()


   if text.startswith("```"):
       text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()


   try:
       parsed = json.loads(text)
   except json.JSONDecodeError:
       return None


   tool = parsed.get("tool", "")
   inp  = parsed.get("input", {})


   if tool not in VALID_TOOLS:
       return None


   if "mutation_id" not in inp:
       inp["mutation_id"] = mutation_id


   return {"tool_name": tool, "tool_input": inp}




# ── SAME OBS FORMATTER AS inference.py ─────────────────────────────────


def obs_to_message(obs: dict) -> str:
   lines = [
       f"Mutation ID: {obs.get('mutation_id')}",
       f"Gene: {obs.get('gene')}  Position: {obs.get('position')}",
       f"Ref AA → Mut AA: {obs.get('ref_aa')} → {obs.get('mut_aa')}",
       f"Sequence context: {obs.get('sequence_context')}",
       f"Budget remaining: {obs.get('budget_remaining')}",
       f"Steps taken: {obs.get('steps_taken')}",
       f"Tools called: {obs.get('tools_called', [])}",
   ]


   if obs.get("conservation_result"):
       lines.append(f"Conservation: {obs['conservation_result']}")


   if obs.get("structure_result"):
       lines.append(f"Structure: {obs['structure_result']}")


   if obs.get("domain_result"):
       lines.append(f"Domain: {obs['domain_result']}")


   return "\n".join(lines)




# ── WS HELPERS (aligned) ───────────────────────────────────────────────


async def ws_send_recv(ws, payload):
   await ws.send(json.dumps(payload))


   for _ in range(5):
       msg = json.loads(await ws.recv())
       if msg.get("type") == "observation":
           return msg


   raise RuntimeError("No observation received")




def parse_response(msg):
   data = msg.get("data", {})
   obs  = data.get("observation", {})


   done = bool(
       data.get("done", False)
       or obs.get("done", False)
       or obs.get("episode_done", False)
   )


   reward_raw = data.get("reward")


   if isinstance(reward_raw, dict):
       reward = float(reward_raw.get("total_reward", 0.0) or 0.0)
   elif isinstance(reward_raw, (int, float)):
       reward = float(reward_raw)
   else:
       reward = 0.0


   return obs, reward, done




# ── EPISODE RUN ───────────────────────────────────────────────────────


async def run_episode(episode: int):
   task_id = get_task_id(episode)


   async with websockets.connect(f"{WS_BASE_URL}/ws") as ws:


       # Reset
       msg = await ws_send_recv(ws, {
           "type": "reset",
           "data": {"task_id": task_id},
       })


       obs, _, _ = parse_response(msg)
       mutation_id = obs.get("mutation_id", "unknown")


       messages = [{"role": "system", "content": SYSTEM_PROMPT}]


       total_reward = 0.0


       for step in range(1, MAX_STEPS + 1):


           messages.append({
               "role": "user",
               "content": obs_to_message(obs)
           })


           try:
               raw = call_llm(messages)
               messages.append({"role": "assistant", "content": raw})
               action = parse_action(raw, mutation_id)
           except Exception:
               action = None


           if action is None:
               action = {
                   "tool_name": "get_conservation_score",
                   "tool_input": {"mutation_id": mutation_id},
               }


           msg = await ws_send_recv(ws, {
               "type": "step",
               "data": action,
           })


           obs, reward, done = parse_response(msg)


           total_reward += reward


           print(f"[EP {episode} STEP {step}] reward={reward:.3f}")


           if done:
               break


       return task_id, total_reward




# ── TRAIN LOOP ────────────────────────────────────────────────────────


async def train():
   rewards_per_tier = {1: [], 2: [], 3: []}


   for episode in range(TOTAL_EPISODES):
       task_id, reward = await run_episode(episode)


       rewards_per_tier[task_id].append(reward)


       print(f"[EP {episode}] Task {task_id} → Total Reward: {reward:.3f}")


   print("\n=== FINAL RESULTS ===")


   for tier in [1, 2, 3]:
       if rewards_per_tier[tier]:
           avg = sum(rewards_per_tier[tier]) / len(rewards_per_tier[tier])
           print(f"Task {tier}: avg reward = {avg:.3f}")




if __name__ == "__main__":
   asyncio.run(train())
