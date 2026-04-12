# inference.py

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import websockets
from openai import OpenAI


# ── Config ─────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

HF_TOKEN = os.getenv("HF_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
API_KEY = HF_TOKEN or OPENAI_API_KEY

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
WS_BASE_URL  = ENV_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")

ENV_NAME  = "protein-mutation-analyzer"
MAX_STEPS = 6
MAX_TOTAL_REWARD = 1.0

VALID_TOOLS = {
    "get_conservation_score",
    "get_ddg_estimate",
    "get_domain_annotation",
    "submit_verdict",
}

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


# ── Prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a computational biology agent.
Decide next tool step.
Return ONLY JSON:
{"tool": "...", "input": {...}}
"""


# ── LLM ────────────────────────────────────────────
def call_llm(messages):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=200,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


# ── Parse ──────────────────────────────────────────
def parse_action(raw, mutation_id):
    try:
        parsed = json.loads(raw)
        tool = parsed.get("tool", "")
        inp = parsed.get("input", {})

        if tool not in VALID_TOOLS:
            return None

        inp.setdefault("mutation_id", mutation_id)
        return {"tool_name": tool, "tool_input": inp}

    except Exception:
        return None


# ── Smart fallback ─────────────────────────────────
def choose_verdict(obs):
    try:
        if obs.get("structure_result"):
            if obs["structure_result"]["ddg_estimate"] < -2:
                return "Pathogenic"

        if obs.get("conservation_result"):
            if abs(obs["conservation_result"]["phylop_score"]) < 1:
                return "Benign"

        return "Uncertain"
    except Exception:
        return "Uncertain"


def fallback_policy(step, mutation_id, obs):
    if step == 1:
        return {"tool_name": "get_conservation_score", "tool_input": {"mutation_id": mutation_id}}
    elif step == 2:
        return {"tool_name": "get_ddg_estimate", "tool_input": {"mutation_id": mutation_id}}
    elif step == 3:
        return {"tool_name": "get_domain_annotation", "tool_input": {"mutation_id": mutation_id}}
    else:
        return {
            "tool_name": "submit_verdict",
            "tool_input": {
                "mutation_id": mutation_id,
                "verdict": choose_verdict(obs),
            },
        }


# ── Obs → text ─────────────────────────────────────
def obs_to_message(obs):
    return f"""
Mutation: {obs.get('mutation_id')}
Gene: {obs.get('gene')}
Steps: {obs.get('steps_taken')}
Budget: {obs.get('budget_remaining')}
Conservation: {obs.get('conservation_result')}
Structure: {obs.get('structure_result')}
Domain: {obs.get('domain_result')}
"""


# ── WS helpers ─────────────────────────────────────
async def ws_send_recv(ws, payload):
    await ws.send(json.dumps(payload))
    raw = await ws.recv()
    return json.loads(raw)


def parse_ws(msg):
    data = msg.get("data", {})
    obs = data.get("observation", {})
    reward = float(data.get("reward") or 0.0)
    done = bool(data.get("done") or obs.get("episode_done"))
    return obs, reward, done


# ── END logger ─────────────────────────────────────
def log_end(success, step, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={step} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Run task ───────────────────────────────────────
async def run_task(task_id, task_name):
    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}", flush=True)

    step = 0
    rewards = []
    success = False

    try:
        async with websockets.connect(f"{WS_BASE_URL}/ws") as ws:

            # RESET
            msg = await ws_send_recv(ws, {"type": "reset", "data": {"task_id": task_id}})
            obs, _, _ = parse_ws(msg)

            mutation_id = obs.get("mutation_id", "unknown")
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            while step < MAX_STEPS:
                step += 1

                messages.append({"role": "user", "content": obs_to_message(obs)})

                # Try LLM
                action = None
                raw = call_llm(messages)

                if raw:
                    parsed = parse_action(raw, mutation_id)
                    if parsed:
                        action = parsed

                # Fallback if LLM fails
                if action is None:
                    action = fallback_policy(step, mutation_id, obs)

                action_str = json.dumps(action)

                # STEP
                msg = await ws_send_recv(ws, {"type": "step", "data": action})
                obs, reward, done = parse_ws(msg)

                rewards.append(reward)

                print(
                    f"[STEP] step={step} action={action_str} "
                    f"reward={reward:.2f} done={str(done).lower()} error=null",
                    flush=True,
                )

                if done:
                    success = reward > 0
                    break

    except Exception as e:
        logger.error("WS error: %s", e)
        log_end(False, step, 0.0, [])
        return

    # ── SCORE (FIXED) ──────────────────────────────
    score = sum(rewards) / MAX_TOTAL_REWARD
    score = min(max(score, 0.0), 1.0)

    log_end(success, step, score, rewards)


# ── Main ──────────────────────────────────────────
TASKS = [
    (1, "task_tier_1_easy"),
    (2, "task_tier_2_medium"),
    (3, "task_tier_3_hard"),
]


async def main():
    print(f"Running inference against {ENV_BASE_URL}", file=sys.stderr)
    for t in TASKS:
        await run_task(*t)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())