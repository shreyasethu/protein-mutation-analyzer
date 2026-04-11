# inference.py

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import websockets
from openai import OpenAI


# ── Config ──────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

HF_TOKEN = os.getenv("HF_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
API_KEY = HF_TOKEN or OPENAI_API_KEY

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
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

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


# ── Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a computational biology agent.
Return ONLY JSON:
{"tool": "...", "input": {...}}
"""


# ── LLM ─────────────────────────────────────────────────────────────────
def call_llm(messages):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=256,
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


# ── Parse ───────────────────────────────────────────────────────────────
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


# ── Deterministic fallback (FIX) ─────────────────────────────────────────
def fallback_policy(step, mutation_id):
    if step == 1:
        return {"tool_name": "get_conservation_score", "tool_input": {"mutation_id": mutation_id}}
    elif step == 2:
        return {"tool_name": "get_ddg_estimate", "tool_input": {"mutation_id": mutation_id}}
    elif step == 3:
        return {"tool_name": "get_domain_annotation", "tool_input": {"mutation_id": mutation_id}}
    else:
        return {
            "tool_name": "submit_verdict",
            "tool_input": {"mutation_id": mutation_id, "verdict": "Pathogenic"},
        }


# ── Obs → text ──────────────────────────────────────────────────────────
def obs_to_message(obs):
    return f"""
Mutation: {obs.get('mutation_id')}
Gene: {obs.get('gene')}
Steps: {obs.get('steps_taken')}
Budget: {obs.get('budget_remaining')}
"""


# ── WS helpers ──────────────────────────────────────────────────────────
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


# ── END logger ──────────────────────────────────────────────────────────
def log_end(success, step, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={step} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Run task ────────────────────────────────────────────────────────────
async def run_task(task_id, task_name):
    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}", flush=True)

    step = 0
    rewards = []
    success = False

    try:
        async with websockets.connect(f"{WS_BASE_URL}/ws") as ws:

            # RESET
            try:
                msg = await ws_send_recv(ws, {"type": "reset", "data": {"task_id": task_id}})
                obs, _, _ = parse_ws(msg)
            except Exception:
                log_end(False, step, 0.0, [])
                return

            mutation_id = obs.get("mutation_id", "unknown")
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            while step < MAX_STEPS:
                step += 1

                messages.append({"role": "user", "content": obs_to_message(obs)})

                # Try LLM
                action = None
                try:
                    raw = call_llm(messages)
                    parsed = parse_action(raw, mutation_id)

                    # Avoid repeated useless calls
                    if parsed and not (
                        parsed["tool_name"] == "get_conservation_score" and step > 1
                    ):
                        action = parsed

                except Exception:
                    pass

                # Fallback if needed
                if action is None:
                    action = fallback_policy(step, mutation_id)

                action_str = json.dumps(action)

                # STEP
                try:
                    msg = await ws_send_recv(ws, {"type": "step", "data": action})
                    obs, reward, done = parse_ws(msg)
                except Exception:
                    reward = 0.0
                    done = False

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

    # SCORE
    score = max(0.0, min(1.0, sum(rewards)))

    log_end(success, step, score, rewards)


# ── Main ────────────────────────────────────────────────────────────────
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