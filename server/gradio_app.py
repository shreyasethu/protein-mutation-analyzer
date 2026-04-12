# import gradio as gr
# import requests
# import os

# BASE = os.getenv("ENV_BASE_URL", "http://127.0.0.1:7860")


# def post(path, payload):
#     try:
#         r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
#         r.raise_for_status()
#         return r.json()
#     except requests.HTTPError as e:
#         detail = ""
#         try:
#             detail = e.response.text
#         except Exception:
#             pass
#         return {"error": f"{e} | body={detail}"}
#     except Exception as e:
#         return {"error": str(e)}


# # ---------- helpers ---------- #
# def extract_obs(res):
#     return res.get("observation", {})


# def format_summary(obs):
#     if not obs:
#         return ["-", "-", "-", "-", "-", "-"]

#     return [
#         obs.get("mutation_id"),
#         obs.get("gene"),
#         f"{obs.get('ref_aa')} → {obs.get('mut_aa')}",
#         obs.get("position"),
#         f"{obs.get('steps_taken')} / {obs.get('step_budget')}",
#         obs.get("budget_remaining"),
#     ]


# def append_log(log, text):
#     return log + "\n" + text if log else text


# def extract_reward(res):
#     return res.get("reward") or res.get("observation", {}).get("reward")


# # ------------------ Dashboard ------------------ #
# def dashboard_tab():
#     state = gr.State({"mutation_id": None})

#     with gr.Row():
#         with gr.Column(scale=2):
#             mutation_id = gr.Textbox(label="Mutation ID", interactive=False)
#             gene = gr.Textbox(label="Gene", interactive=False)
#             change = gr.Textbox(label="Change", interactive=False)

#         with gr.Column(scale=2):
#             position = gr.Textbox(label="Position", interactive=False)
#             steps = gr.Textbox(label="Steps", interactive=False)
#             budget = gr.Textbox(label="Budget Remaining", interactive=False)

#     log = gr.Textbox(label="Step Log", lines=12)

#     def reset():
#         res = post("/reset", {})
#         obs = extract_obs(res)
#         mid = obs.get("mutation_id")

#         return {"mutation_id": mid}, *format_summary(obs), "Initialized\n"

#     def step(state, log_text):
#         mid = state["mutation_id"]

#         if not mid:
#             return state, "-", "-", "-", "-", "-", "-", "❌ Reset first"

#         tools = [
#             "get_conservation_score",
#             "get_ddg_estimate",
#             "get_domain_annotation"
#         ]

#         current_steps = log_text.count("→") if log_text else 0
#         tool = tools[current_steps % len(tools)]

#         payload = {
#             "action": {
#                 "tool_name": tool,
#                 "tool_input": {"mutation_id": mid}
#             }
#         }

#         res = post("/step", payload)

#         if "error" in res:
#             return state, *format_summary({}), append_log(log_text, f"❌ {res['error']}")

#         obs = extract_obs(res)
#         reward = extract_reward(res)

#         return state, *format_summary(obs), append_log(log_text, f"{tool} → reward {reward}")

#     with gr.Row():
#         reset_btn = gr.Button("Reset", variant="primary")
#         step_btn = gr.Button("Run Step")

#     reset_btn.click(reset, outputs=[state, mutation_id, gene, change, position, steps, budget, log])
#     step_btn.click(step, inputs=[state, log], outputs=[state, mutation_id, gene, change, position, steps, budget, log])


# # ------------------ Control ------------------ #
# def control_tab():
#     state = gr.State({"mutation_id": None})

#     with gr.Row():
#         tool = gr.Dropdown(
#             ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation", "submit_verdict"],
#             value="get_conservation_score",
#             label="Tool"
#         )

#         verdict = gr.Dropdown(
#             ["Pathogenic", "Benign", "Uncertain"],
#             value="Pathogenic",
#             label="Verdict"
#         )

#     log = gr.Textbox(label="Execution Log", lines=12)

#     def reset():
#         res = post("/reset", {})
#         return {"mutation_id": extract_obs(res).get("mutation_id")}, "Initialized\n"

#     def step(tool, verdict, state, log_text):
#         mid = state["mutation_id"]

#         if not mid:
#             return state, "❌ Reset first"

#         payload = {
#             "action": {
#                 "tool_name": tool,
#                 "tool_input": {"mutation_id": mid}
#             }
#         }

#         if tool == "submit_verdict":
#             payload["action"]["tool_input"]["verdict"] = verdict  # ✅ correct casing

#         res = post("/step", payload)

#         if "error" in res:
#             return state, append_log(log_text, f"❌ {res['error']}")

#         reward = extract_reward(res)

#         return state, append_log(log_text, f"{tool} → reward {reward}")

#     with gr.Row():
#         gr.Button("Reset").click(reset, outputs=[state, log])
#         gr.Button("Run Action", variant="primary").click(step, inputs=[tool, verdict, state, log], outputs=[state, log])


# # ------------------ Demo ------------------ #
# def demo_tab():
#     output = gr.Textbox(label="Pipeline Output", lines=15)

#     def run():
#         res = post("/reset", {})
#         mid = extract_obs(res).get("mutation_id")

#         text = f"Start: {mid}\n\n"

#         for tool in [
#             "get_conservation_score",
#             "get_ddg_estimate",
#             "get_domain_annotation",
#             "submit_verdict",
#         ]:
#             payload = {
#                 "action": {
#                     "tool_name": tool,
#                     "tool_input": {"mutation_id": mid}
#                 }
#             }

#             if tool == "submit_verdict":
#                 payload["action"]["tool_input"]["verdict"] = "Pathogenic"

#             res = post("/step", payload)

#             if "error" in res:
#                 return text + f"❌ {res['error']}\n"

#             reward = extract_reward(res)
#             text += f"{tool} → reward {reward}\n"

#             if res.get("done"):
#                 break

#         return text

#     gr.Button("Run Full Pipeline", variant="primary").click(run, outputs=output)


# # ------------------ App ------------------ #
# def create_app():
#     with gr.Blocks(title="MutantBench") as app:
#         gr.Markdown("# 🧬 MutantBench")

#         with gr.Tabs():
#             with gr.Tab("Dashboard"):
#                 dashboard_tab()
#             with gr.Tab("Control"):
#                 control_tab()
#             with gr.Tab("Demo"):
#                 demo_tab()

#     return app


# if __name__ == "__main__":
#     create_app().launch(server_name="0.0.0.0", server_port=7860)

import gradio as gr
import requests
import os

BASE = os.getenv("ENV_BASE_URL", "http://127.0.0.1:7860")

# ── palette (used in inline styles) ──────────────────────────────────────
BG_BASE    = "#080d14"
BG_SURFACE = "#0d1520"
BG_RAISED  = "#111c2b"
BORDER     = "#1e2f45"
BORDER_HI  = "#2a4060"
TXT_PRI    = "#d4e8ff"
TXT_SEC    = "#6a8daf"
TXT_MUT    = "#3d5570"
CYAN       = "#00d4ff"
GREEN      = "#00e5a0"
AMBER      = "#f5a623"
RED        = "#ff4f6a"
MONO       = "JetBrains Mono, Fira Code, Cascadia Code, monospace"
UI         = "DM Sans, Outfit, system-ui, sans-serif"


def post(path, payload):
    try:
        r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text
        except Exception:
            pass
        return {"error": f"{e} | body={detail}"}
    except Exception as e:
        return {"error": str(e)}


def extract_obs(res):
    return res.get("observation", {})


def append_log(log, text):
    return log + "\n" + text if log else text


def extract_reward(res):
    return res.get("reward") or res.get("observation", {}).get("reward")


# ── HTML components (fully inline styles) ────────────────────────────────

def create_protein_card(obs):
    card_base = (
        f"background:{BG_SURFACE};border:1px solid {BORDER_HI};border-radius:14px;"
        f"padding:28px;position:relative;overflow:hidden;font-family:{UI};"
        f"color:{TXT_PRI};min-height:260px;"
    )

    if not obs:
        return f"""
        <div style="{card_base}display:flex;flex-direction:column;align-items:center;
                    justify-content:center;text-align:center;border-color:{BORDER};">
            <div style="font-size:48px;color:{TXT_MUT};margin-bottom:14px;">⬡</div>
            <div style="font-family:{MONO};font-size:14px;letter-spacing:2px;
                        color:{TXT_SEC};margin-bottom:6px;">NO MUTATION LOADED</div>
            <div style="font-size:13px;color:{TXT_MUT};">Initialize environment to begin analysis</div>
        </div>"""

    mutation_id = obs.get("mutation_id", "—")
    gene        = obs.get("gene", "—")
    ref_aa      = obs.get("ref_aa", "?")
    mut_aa      = obs.get("mut_aa", "?")
    position    = obs.get("position", "?")
    steps_taken = obs.get("steps_taken", 0)
    step_budget = obs.get("step_budget", 10)
    budget_rem  = obs.get("budget_remaining", 0)

    pct     = (steps_taken / step_budget * 100) if step_budget else 0
    bar_col = GREEN if pct < 40 else AMBER if pct < 75 else RED

    dots = "".join([
        f'<div style="width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px;'
        f'background:{"transparent" if i >= steps_taken else bar_col};'
        f'border:1px solid {"" if i < steps_taken else BORDER};'
        f'box-shadow:{"0 0 6px " + bar_col if i < steps_taken else "none"};"></div>'
        for i in range(step_budget)
    ])

    return f"""
    <div style="{card_base}">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;
                  background:linear-gradient(90deg,{CYAN},{GREEN});"></div>

      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:22px;">
        <div>
          <div style="font-family:{MONO};font-size:9px;letter-spacing:3px;
                      color:{TXT_MUT};margin-bottom:6px;">GENE TARGET</div>
          <div style="font-size:34px;font-weight:700;color:{CYAN};
                      letter-spacing:-1px;line-height:1;margin-bottom:8px;">{gene}</div>
          <div style="display:inline-block;font-family:{MONO};font-size:11px;color:{TXT_MUT};
                      background:{BG_RAISED};border:1px solid {BORDER};
                      padding:3px 10px;border-radius:4px;">{mutation_id}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-family:{MONO};font-size:9px;letter-spacing:3px;
                      color:{TXT_MUT};margin-bottom:4px;">BUDGET</div>
          <div style="font-family:{MONO};font-size:44px;font-weight:700;
                      color:{GREEN};line-height:1;">{budget_rem}</div>
          <div style="font-size:11px;color:{TXT_MUT};">remaining</div>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:12px;
                  background:{BG_RAISED};border:1px solid {BORDER};
                  border-radius:10px;padding:18px 22px;margin-bottom:20px;">
        <div style="text-align:center;">
          <div style="font-family:{MONO};font-size:9px;letter-spacing:2px;
                      color:{TXT_MUT};margin-bottom:4px;">REF</div>
          <div style="font-family:{MONO};font-size:38px;font-weight:700;
                      color:{TXT_SEC};line-height:1;">{ref_aa}</div>
        </div>
        <div style="flex:1;display:flex;align-items:center;padding:0 8px;">
          <div style="flex:1;height:1px;background:linear-gradient(90deg,{BORDER_HI},{AMBER});"></div>
          <div style="color:{AMBER};font-size:12px;margin-left:4px;">&#9654;</div>
        </div>
        <div style="text-align:center;">
          <div style="font-family:{MONO};font-size:9px;letter-spacing:2px;
                      color:{TXT_MUT};margin-bottom:4px;">MUT</div>
          <div style="font-family:{MONO};font-size:38px;font-weight:700;
                      color:{AMBER};line-height:1;">{mut_aa}</div>
        </div>
        <div style="margin-left:auto;background:{BG_BASE};border:1px solid {BORDER};
                    border-radius:6px;padding:10px 16px;text-align:center;">
          <div style="font-family:{MONO};font-size:9px;letter-spacing:2px;
                      color:{TXT_MUT};margin-bottom:2px;">POS</div>
          <div style="font-family:{MONO};font-size:22px;font-weight:700;color:{TXT_PRI};">{position}</div>
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="font-family:{MONO};font-size:9px;letter-spacing:2px;color:{TXT_MUT};">ANALYSIS PROGRESS</span>
        <span style="font-family:{MONO};font-size:13px;font-weight:600;color:{TXT_PRI};">
          {steps_taken} <span style="color:{TXT_MUT};">/ {step_budget}</span>
        </span>
      </div>
      <div style="height:3px;background:{BG_RAISED};border-radius:2px;overflow:hidden;margin-bottom:10px;">
        <div style="height:100%;width:{pct}%;background:{bar_col};border-radius:2px;
                    box-shadow:0 0 8px {bar_col};"></div>
      </div>
      <div style="display:flex;">{dots}</div>
    </div>"""


def create_tool_info_card():
    panel = (f"background:{BG_SURFACE};border:1px solid {BORDER};border-radius:14px;"
             f"padding:24px;font-family:{UI};color:{TXT_PRI};")
    hdr   = (f"display:flex;align-items:center;gap:10px;margin-bottom:18px;"
              f"padding-bottom:14px;border-bottom:1px solid {BORDER};")
    row   = f"display:flex;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid {BORDER};"
    rowl  = f"display:flex;align-items:flex-start;gap:14px;padding:14px 0;"

    def chip(label, color):
        return (f"<div style='font-family:{MONO};font-size:10px;font-weight:600;"
                f"padding:6px 8px;border-radius:6px;flex-shrink:0;min-width:44px;"
                f"text-align:center;background:{color}22;color:{color};"
                f"border:1px solid {color}33;'>{label}</div>")

    def desc(name, text):
        return (f"<div><div style='font-size:13px;font-weight:500;color:{TXT_PRI};"
                f"margin-bottom:4px;'>{name}</div>"
                f"<div style='font-size:12px;color:{TXT_MUT};line-height:1.5;'>{text}</div></div>")

    return f"""
    <div style="{panel}">
      <div style="{hdr}">
        <span style="color:{CYAN};font-size:18px;">&#9672;</span>
        <span style="font-family:{MONO};font-size:11px;letter-spacing:3px;color:{TXT_SEC};">ANALYSIS TOOLKIT</span>
      </div>
      <div style="{row}">
        {chip("CSv", CYAN)}
        {desc("Conservation Score", "Cross-species amino acid conservation. High conservation = functionally critical site.")}
      </div>
      <div style="{row}">
        {chip("&#916;&#916;G", GREEN)}
        {desc("Stability Estimate", "Folding free energy change. Large positive values indicate destabilizing mutations.")}
      </div>
      <div style="{rowl}">
        {chip("DOM", AMBER)}
        {desc("Domain Annotation", "Structural domain mapping. Mutations in active/binding sites carry higher pathogenic risk.")}
      </div>
    </div>"""


def create_reward_explainer():
    panel = (f"background:{BG_SURFACE};border:1px solid {BORDER};border-radius:14px;"
             f"padding:24px;font-family:{UI};color:{TXT_PRI};")
    hdr   = (f"display:flex;align-items:center;gap:10px;margin-bottom:18px;"
              f"padding-bottom:14px;border-bottom:1px solid {BORDER};")
    row   = f"display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid {BORDER};"
    rowl  = f"display:flex;align-items:center;gap:14px;padding:14px 0;"

    def indicator(sym, color):
        return (f"<div style='width:32px;height:32px;border-radius:50%;flex-shrink:0;"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-size:16px;font-weight:700;background:{color}18;"
                f"color:{color};border:1px solid {color}30;'>{sym}</div>")

    def desc(name, text):
        return (f"<div><div style='font-size:13px;font-weight:500;color:{TXT_PRI};"
                f"margin-bottom:3px;'>{name}</div>"
                f"<div style='font-size:12px;color:{TXT_MUT};line-height:1.5;'>{text}</div></div>")

    return f"""
    <div style="{panel}">
      <div style="{hdr}">
        <span style="color:{CYAN};font-size:18px;">&#9671;</span>
        <span style="font-family:{MONO};font-size:11px;letter-spacing:3px;color:{TXT_SEC};">SCORING SYSTEM</span>
      </div>
      <div style="{row}">
        {indicator("+", GREEN)}
        {desc("Positive Reward", "Correct pathogenicity call or efficient tool usage.")}
      </div>
      <div style="{row}">
        {indicator("&#8722;", RED)}
        {desc("Zero Reward", "Incorrect verdict or redundant tool execution.")}
      </div>
      <div style="{rowl}">
        {indicator("&#9673;", CYAN)}
        {desc("Budget Cost", "Each tool use consumes budget. Maximize accuracy per step.")}
      </div>
    </div>"""


def tab_header(icon, title, subtitle):
    return (
        f"<div style='display:flex;align-items:center;gap:16px;"
        f"padding:20px 24px;background:{BG_SURFACE};border:1px solid {BORDER};"
        f"border-radius:10px;margin-bottom:24px;font-family:{UI};'>"
        f"<span style='font-size:28px;color:{CYAN};line-height:1;'>{icon}</span>"
        f"<div>"
        f"<div style='font-family:{MONO};font-size:13px;font-weight:600;"
        f"letter-spacing:3px;color:{TXT_PRI};'>{title}</div>"
        f"<div style='font-size:13px;color:{TXT_SEC};margin-top:3px;'>{subtitle}</div>"
        f"</div></div>"
    )


# ── Tabs ──────────────────────────────────────────────────────────────────

def dashboard_tab():
    state = gr.State({"mutation_id": None})

    with gr.Row():
        with gr.Column(scale=3):
            protein_card = gr.HTML(value=create_protein_card(None))
        with gr.Column(scale=2):
            tool_info = gr.HTML(value=create_tool_info_card())

    with gr.Row():
        with gr.Column(scale=1):
            reward_info = gr.HTML(value=create_reward_explainer())
        with gr.Column(scale=1):
            log = gr.Textbox(
                label="EXECUTION LOG",
                lines=14,
                show_label=True,
                placeholder="— awaiting initialization —",
            )

    def reset():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")
        return (
            {"mutation_id": mid},
            create_protein_card(obs),
            "▶ ENV INITIALIZED\n✓ Mutation loaded — ready for analysis\n",
        )

    def step(state, log_text):
        mid = state["mutation_id"]
        if not mid:
            return state, create_protein_card(None), "✗ Reset required before stepping"

        tools = ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation"]
        current_steps = log_text.count("→") if log_text else 0
        tool = tools[current_steps % len(tools)]

        tool_labels = {
            "get_conservation_score": "CSv  Conservation Score",
            "get_ddg_estimate":       "ΔΔG  Stability Estimate",
            "get_domain_annotation":  "DOM  Domain Annotation",
        }

        res = post("/step", {"action": {"tool_name": tool, "tool_input": {"mutation_id": mid}}})

        if "error" in res:
            return state, create_protein_card({}), append_log(log_text, f"✗ Error: {res['error']}")

        obs    = extract_obs(res)
        reward = extract_reward(res)
        sign   = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"
        rstr   = (f"+{reward}" if reward and reward > 0 else ("None (redundant tool call, zero reward)" if reward is None else str(reward)))
        new_log = append_log(log_text, f"→ {tool_labels.get(tool, tool)}\n  {sign} reward: {rstr}\n")
        return state, create_protein_card(obs), new_log

    with gr.Row():
        reset_btn = gr.Button("⟳  INITIALIZE", variant="primary",   size="lg")
        step_btn  = gr.Button("▶  RUN STEP",   variant="secondary", size="lg")

    reset_btn.click(reset, outputs=[state, protein_card, log])
    step_btn.click(step,   inputs=[state, log], outputs=[state, protein_card, log])


def control_tab():
    state = gr.State({"mutation_id": None})

    gr.HTML(tab_header("&#8982;", "MANUAL CONTROL", "Direct tool execution and verdict submission"))

    with gr.Row():
        with gr.Column():
            tool = gr.Dropdown(
                ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation", "submit_verdict"],
                value="get_conservation_score",
                label="SELECT TOOL",
            )
        with gr.Column():
            verdict = gr.Dropdown(
                ["Pathogenic", "Benign", "Uncertain"],
                value="Pathogenic",
                label="PATHOGENICITY VERDICT",
            )

    log = gr.Textbox(label="EXECUTION LOG", lines=12, placeholder="— awaiting initialization —")

    def reset():
        res = post("/reset", {})
        return (
            {"mutation_id": extract_obs(res).get("mutation_id")},
            "▶ ENV INITIALIZED\n✓ New mutation loaded\n",
        )

    def step(tool, verdict, state, log_text):
        mid = state["mutation_id"]
        if not mid:
            return state, "✗ Reset required before stepping\n"

        tool_labels = {
            "get_conservation_score": "CSv  Conservation Score",
            "get_ddg_estimate":       "ΔΔG  Stability Estimate",
            "get_domain_annotation":  "DOM  Domain Annotation",
            "submit_verdict":         "     Submit Verdict",
        }

        payload = {"action": {"tool_name": tool, "tool_input": {"mutation_id": mid}}}
        if tool == "submit_verdict":
            payload["action"]["tool_input"]["verdict"] = verdict

        res = post("/step", payload)
        if "error" in res:
            return state, append_log(log_text, f"✗ Error: {res['error']}\n")

        reward  = extract_reward(res)
        sign    = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"
        rstr    = (f"+{reward}" if reward and reward > 0 else str(reward))
        new_log = append_log(log_text, f"→ {tool_labels.get(tool, tool)}\n  {sign} reward: {rstr}\n")
        return state, new_log

    with gr.Row():
        gr.Button("⟳  INITIALIZE", variant="secondary", size="lg").click(reset, outputs=[state, log])
        gr.Button("▶  EXECUTE",    variant="primary",   size="lg").click(
            step, inputs=[tool, verdict, state, log], outputs=[state, log]
        )


def demo_tab():
    gr.HTML(tab_header("&#10033;", "AUTOMATED PIPELINE", "Full end-to-end analysis from initialization to verdict"))

    output = gr.Textbox(label="PIPELINE LOG", lines=15, placeholder="— click RUN PIPELINE to begin —")

    def run():
        res = post("/reset", {})
        mid = extract_obs(res).get("mutation_id")
        text = f"▶ PIPELINE START\n  mutation: {mid}\n\n"

        tools = [
            ("get_conservation_score", "CSv  Conservation Score"),
            ("get_ddg_estimate",       "ΔΔG  Stability Estimate"),
            ("get_domain_annotation",  "DOM  Domain Annotation"),
            ("submit_verdict",         "⚖   Submit Verdict"),
        ]

        for tool, label in tools:
            payload = {"action": {"tool_name": tool, "tool_input": {"mutation_id": mid}}}
            if tool == "submit_verdict":
                payload["action"]["tool_input"]["verdict"] = "Pathogenic"

            res    = post("/step", payload)
            if "error" in res:
                return text + f"✗ Pipeline error: {res['error']}\n"

            reward = extract_reward(res)
            sign   = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"
            rstr   = (f"+{reward}" if reward and reward > 0 else ("None (redundant tool call, zero reward)" if reward is None else str(reward)))
            text  += f"→ {label}\n  {sign} reward: {rstr}\n\n"

            if res.get("done"):
                text += "✓ PIPELINE COMPLETE\n"
                break

        return text

    gr.Button("*  RUN PIPELINE", variant="primary", size="lg").click(run, outputs=output)


# ── App ───────────────────────────────────────────────────────────────────

def create_app():
    css = f"""
    .gradio-container {{
        background: {BG_BASE} !important;
        font-family: {UI} !important;
    }}
    footer {{ display: none !important; }}

    /* tabs */
    .tab-nav {{
        background: {BG_SURFACE} !important;
        border-bottom: 1px solid {BORDER} !important;
        padding: 0 16px !important;
        gap: 0 !important;
    }}
    .tab-nav button {{
        font-family: {MONO} !important;
        font-size: 10px !important;
        letter-spacing: 2.5px !important;
        text-transform: uppercase !important;
        color: {TXT_MUT} !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        padding: 14px 20px !important;
        margin: 0 !important;
        transition: color 0.2s !important;
    }}
    .tab-nav button:hover {{
        color: {TXT_SEC} !important;
        transform: none !important;
        box-shadow: none !important;
        background: rgba(0,212,255,0.03) !important;
    }}
    .tab-nav button.selected {{
        color: {CYAN} !important;
        border-bottom-color: {CYAN} !important;
    }}

    /* inputs */
    label > span:first-child {{
        font-family: {MONO} !important;
        font-size: 10px !important;
        letter-spacing: 2px !important;
        color: {TXT_MUT} !important;
        text-transform: uppercase !important;
    }}
    textarea, input[type=text] {{
        background: {BG_RAISED} !important;
        border: 1px solid {BORDER} !important;
        color: {TXT_PRI} !important;
        font-family: {MONO} !important;
        font-size: 12px !important;
        border-radius: 8px !important;
        line-height: 1.7 !important;
    }}
    textarea:focus, input[type=text]:focus {{
        border-color: {CYAN} !important;
        box-shadow: 0 0 0 2px rgba(0,212,255,0.1) !important;
        outline: none !important;
    }}

    /* buttons */
    button.primary {{
        background: linear-gradient(135deg, #0891b2, {CYAN}) !important;
        color: {BG_BASE} !important;
        font-family: {MONO} !important;
        font-size: 10px !important;
        letter-spacing: 2px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    button.secondary {{
        background: {BG_RAISED} !important;
        color: {TXT_SEC} !important;
        font-family: {MONO} !important;
        font-size: 10px !important;
        letter-spacing: 2px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        border: 1px solid {BORDER_HI} !important;
        border-radius: 8px !important;
    }}
    button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.5) !important;
    }}
    button:active {{
        transform: scale(0.98) !important;
    }}

    /* dropdown */
    .wrap-inner, .multiselect {{
        background: {BG_RAISED} !important;
        border-color: {BORDER} !important;
    }}
    ul.options {{
        background: {BG_RAISED} !important;
        border: 1px solid {BORDER_HI} !important;
    }}
    ul.options > li {{
        color: {TXT_PRI} !important;
        font-family: {MONO} !important;
        font-size: 12px !important;
    }}
    ul.options > li:hover {{
        background: {BG_SURFACE} !important;
    }}

    /* strip default gradio card shadows / borders */
    .block, .gr-group {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    """

    with gr.Blocks(
        title="MutantBench",
        css=css,
        theme=gr.themes.Base(
            primary_hue="sky",
            secondary_hue="slate",
            neutral_hue="slate",
        ),
    ) as app:

        gr.HTML(f"""
        <div style="text-align:center;padding:48px 32px 36px;
                    background:{BG_BASE};border-bottom:1px solid {BORDER};">
          <div style="font-family:{MONO};font-size:11px;letter-spacing:4px;
                      color:{CYAN};margin-bottom:12px;">PROTEIN MUTATION ANALYSIS PLATFORM</div>
          <div style="font-size:52px;font-weight:700;letter-spacing:-2px;
                      color:{TXT_PRI};line-height:1;margin-bottom:12px;font-family:{UI};">
            Mutant<span style="color:{CYAN};">Bench</span>
          </div>
          <div style="font-size:15px;color:{TXT_SEC};font-weight:300;font-family:{UI};">
            Conservation &nbsp;&middot;&nbsp; Stability &nbsp;&middot;&nbsp;
            Domain Annotation &nbsp;&middot;&nbsp; Pathogenicity
          </div>
          <div style="width:60px;height:1px;
                      background:linear-gradient(90deg,transparent,{CYAN},transparent);
                      margin:20px auto 0;"></div>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("Dashboard"):
                dashboard_tab()
            with gr.Tab("Manual Control"):
                control_tab()
            with gr.Tab("Auto Demo"):
                demo_tab()

        gr.HTML(f"""
        <div style="text-align:center;padding:20px;border-top:1px solid {BORDER};
                    font-family:{MONO};font-size:11px;letter-spacing:1px;color:{TXT_MUT};">
          MutantBench &nbsp;&middot;&nbsp; AI-Powered Variant Classification &nbsp;&middot;&nbsp;
          <span style="color:{CYAN};">v1.0</span>
        </div>
        """)

    return app


if __name__ == "__main__":
    create_app().launch(server_name="0.0.0.0", server_port=7860)