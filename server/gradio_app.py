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


# ---------- helpers ---------- #
def extract_obs(res):
    return res.get("observation", {})


def format_summary(obs):
    if not obs:
        return ["-", "-", "-", "-", "-", "-"]

    return [
        obs.get("mutation_id"),
        obs.get("gene"),
        f"{obs.get('ref_aa')} → {obs.get('mut_aa')}",
        obs.get("position"),
        f"{obs.get('steps_taken')} / {obs.get('step_budget')}",
        obs.get("budget_remaining"),
    ]


def append_log(log, text):
    return log + "\n" + text if log else text


def extract_reward(res):
    return res.get("reward") or res.get("observation", {}).get("reward")


def create_protein_card(obs):
    if not obs:
        return """
        <div class="protein-card empty-state">
            <div class="empty-icon">⬡</div>
            <h2 class="empty-title">No Mutation Loaded</h2>
            <p class="empty-sub">Initialize environment to begin analysis</p>
        </div>
        """

    mutation_id = obs.get("mutation_id", "Unknown")
    gene = obs.get("gene", "Unknown")
    ref_aa = obs.get("ref_aa", "?")
    mut_aa = obs.get("mut_aa", "?")
    position = obs.get("position", "?")
    steps_taken = obs.get("steps_taken", 0)
    step_budget = obs.get("step_budget", 10)
    budget_remaining = obs.get("budget_remaining", 0)

    progress_pct = (steps_taken / step_budget * 100) if step_budget > 0 else 0
    if progress_pct < 40:
        bar_color = "var(--accent-green)"
        status_dot = "status-green"
    elif progress_pct < 75:
        bar_color = "var(--accent-amber)"
        status_dot = "status-amber"
    else:
        bar_color = "var(--accent-red)"
        status_dot = "status-red"

    return f"""
    <div class="protein-card loaded">
        <div class="card-header">
            <div class="gene-info">
                <div class="gene-label">GENE TARGET</div>
                <div class="gene-name">{gene}</div>
                <div class="mutation-id-badge">{mutation_id}</div>
            </div>
            <div class="budget-display">
                <div class="budget-label">BUDGET</div>
                <div class="budget-value">{budget_remaining}</div>
                <div class="budget-sub">remaining</div>
            </div>
        </div>

        <div class="mutation-display">
            <div class="aa-block ref-block">
                <div class="aa-label">REF</div>
                <div class="aa-code">{ref_aa}</div>
            </div>
            <div class="mutation-arrow">
                <div class="arrow-line"></div>
                <div class="arrow-head">▶</div>
            </div>
            <div class="aa-block mut-block">
                <div class="aa-label">MUT</div>
                <div class="aa-code">{mut_aa}</div>
            </div>
            <div class="position-badge">
                <span class="pos-label">POS</span>
                <span class="pos-value">{position}</span>
            </div>
        </div>

        <div class="progress-section">
            <div class="progress-header">
                <span class="progress-label">ANALYSIS PROGRESS</span>
                <span class="progress-count">{steps_taken} <span class="progress-total">/ {step_budget}</span></span>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="width: {progress_pct}%; background: {bar_color};"></div>
            </div>
            <div class="step-dots">
                {"".join([f'<div class="step-dot {"filled" if i < steps_taken else ""} {status_dot if i < steps_taken else ""}"></div>' for i in range(step_budget)])}
            </div>
        </div>
    </div>
    """


def create_tool_info_card():
    return """
    <div class="info-panel">
        <div class="panel-header">
            <span class="panel-icon">◈</span>
            <span class="panel-title">ANALYSIS TOOLKIT</span>
        </div>

        <div class="tool-item">
            <div class="tool-icon conservation">CSv</div>
            <div class="tool-details">
                <div class="tool-name">Conservation Score</div>
                <div class="tool-desc">Cross-species amino acid conservation. High conservation = functionally critical site.</div>
            </div>
        </div>

        <div class="tool-item">
            <div class="tool-icon ddg">ΔΔG</div>
            <div class="tool-details">
                <div class="tool-name">Stability Estimate</div>
                <div class="tool-desc">Folding free energy change. Large positive values indicate destabilizing mutations.</div>
            </div>
        </div>

        <div class="tool-item">
            <div class="tool-icon domain">DOM</div>
            <div class="tool-details">
                <div class="tool-name">Domain Annotation</div>
                <div class="tool-desc">Structural domain mapping. Mutations in active/binding sites carry higher pathogenic risk.</div>
            </div>
        </div>
    </div>
    """


def create_reward_explainer():
    return """
    <div class="reward-panel">
        <div class="panel-header">
            <span class="panel-icon">◇</span>
            <span class="panel-title">SCORING SYSTEM</span>
        </div>

        <div class="reward-item positive">
            <div class="reward-indicator">+</div>
            <div class="reward-details">
                <div class="reward-name">Positive Reward</div>
                <div class="reward-desc">Correct pathogenicity call or efficient tool usage.</div>
            </div>
        </div>

        <div class="reward-item negative">
            <div class="reward-indicator">−</div>
            <div class="reward-details">
                <div class="reward-name">Negative Reward</div>
                <div class="reward-desc">Incorrect verdict or redundant tool execution.</div>
            </div>
        </div>

        <div class="reward-item neutral">
            <div class="reward-indicator">◉</div>
            <div class="reward-details">
                <div class="reward-name">Budget Cost</div>
                <div class="reward-desc">Each tool use consumes budget. Maximize accuracy per step.</div>
            </div>
        </div>
    </div>
    """


# ------------------ Dashboard ------------------ #
def dashboard_tab():
    state = gr.State({"mutation_id": None})

    with gr.Row():
        with gr.Column(scale=3):
            protein_card = gr.HTML(value=create_protein_card(None), label=None)

        with gr.Column(scale=2):
            tool_info = gr.HTML(value=create_tool_info_card(), label=None)

    with gr.Row():
        with gr.Column(scale=1):
            reward_info = gr.HTML(value=create_reward_explainer(), label=None)

        with gr.Column(scale=1):
            log = gr.Textbox(
                label="EXECUTION LOG",
                lines=14,
                show_label=True,
                placeholder="— awaiting initialization —",
                elem_classes="log-box"
            )

    def reset():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")

        return (
            {"mutation_id": mid},
            create_protein_card(obs),
            "▶ ENV INITIALIZED\n✓ Mutation loaded — ready for analysis\n"
        )

    def step(state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, create_protein_card(None), "✗ Reset required before stepping"

        tools = [
            "get_conservation_score",
            "get_ddg_estimate",
            "get_domain_annotation"
        ]

        current_steps = log_text.count("→") if log_text else 0
        tool = tools[current_steps % len(tools)]

        tool_labels = {
            "get_conservation_score": "CSv  Conservation Score",
            "get_ddg_estimate":       "ΔΔG  Stability Estimate",
            "get_domain_annotation":  "DOM  Domain Annotation",
        }

        payload = {
            "action": {
                "tool_name": tool,
                "tool_input": {"mutation_id": mid}
            }
        }

        res = post("/step", payload)

        if "error" in res:
            return state, create_protein_card({}), append_log(log_text, f"✗ Error: {res['error']}")

        obs = extract_obs(res)
        reward = extract_reward(res)

        reward_str = f"+{reward}" if reward and reward > 0 else str(reward)
        sign = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"

        new_log = append_log(
            log_text,
            f"→ {tool_labels.get(tool, tool)}\n  {sign} reward: {reward_str}\n"
        )

        return state, create_protein_card(obs), new_log

    with gr.Row(elem_classes="action-row"):
        reset_btn = gr.Button("⟳  INITIALIZE", variant="primary", size="lg", elem_classes="btn-primary-custom")
        step_btn = gr.Button("▶  RUN STEP", variant="secondary", size="lg", elem_classes="btn-secondary-custom")

    reset_btn.click(reset, outputs=[state, protein_card, log])
    step_btn.click(step, inputs=[state, log], outputs=[state, protein_card, log])


# ------------------ Control ------------------ #
def control_tab():
    state = gr.State({"mutation_id": None})

    gr.HTML("""
    <div class="tab-header">
        <span class="tab-header-icon">⌖</span>
        <div>
            <div class="tab-header-title">MANUAL CONTROL</div>
            <div class="tab-header-sub">Direct tool execution and verdict submission</div>
        </div>
    </div>
    """)

    with gr.Row():
        with gr.Column():
            tool = gr.Dropdown(
                ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation", "submit_verdict"],
                value="get_conservation_score",
                label="SELECT TOOL",
                info="Tool to execute on the active mutation"
            )

        with gr.Column():
            verdict = gr.Dropdown(
                ["Pathogenic", "Benign", "Uncertain"],
                value="Pathogenic",
                label="PATHOGENICITY VERDICT",
                info="Classification for submit_verdict action"
            )

    log = gr.Textbox(
        label="EXECUTION LOG",
        lines=12,
        placeholder="— awaiting initialization —",
        show_label=True,
        elem_classes="log-box"
    )

    def reset():
        res = post("/reset", {})
        return (
            {"mutation_id": extract_obs(res).get("mutation_id")},
            "▶ ENV INITIALIZED\n✓ New mutation loaded\n"
        )

    def step(tool, verdict, state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, "✗ Reset required before stepping\n"

        tool_labels = {
            "get_conservation_score": "CSv  Conservation Score",
            "get_ddg_estimate":       "ΔΔG  Stability Estimate",
            "get_domain_annotation":  "DOM  Domain Annotation",
            "submit_verdict":         "⚖   Submit Verdict",
        }

        payload = {
            "action": {
                "tool_name": tool,
                "tool_input": {"mutation_id": mid}
            }
        }

        if tool == "submit_verdict":
            payload["action"]["tool_input"]["verdict"] = verdict

        res = post("/step", payload)

        if "error" in res:
            return state, append_log(log_text, f"✗ Error: {res['error']}\n")

        reward = extract_reward(res)
        reward_str = f"+{reward}" if reward and reward > 0 else str(reward)
        sign = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"

        new_log = append_log(
            log_text,
            f"→ {tool_labels.get(tool, tool)}\n  {sign} reward: {reward_str}\n"
        )

        return state, new_log

    with gr.Row(elem_classes="action-row"):
        gr.Button("⟳  INITIALIZE", variant="secondary", size="lg", elem_classes="btn-secondary-custom").click(
            reset, outputs=[state, log]
        )
        gr.Button("▶  EXECUTE", variant="primary", size="lg", elem_classes="btn-primary-custom").click(
            step, inputs=[tool, verdict, state, log], outputs=[state, log]
        )


# ------------------ Demo ------------------ #
def demo_tab():
    gr.HTML("""
    <div class="tab-header">
        <span class="tab-header-icon">⟡</span>
        <div>
            <div class="tab-header-title">AUTOMATED PIPELINE</div>
            <div class="tab-header-sub">Full end-to-end analysis from initialization to verdict</div>
        </div>
    </div>
    """)

    output = gr.Textbox(
        label="PIPELINE LOG",
        lines=15,
        placeholder="— click RUN PIPELINE to begin —",
        show_label=True,
        elem_classes="log-box"
    )

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

        for tool, display_name in tools:
            payload = {
                "action": {
                    "tool_name": tool,
                    "tool_input": {"mutation_id": mid}
                }
            }

            if tool == "submit_verdict":
                payload["action"]["tool_input"]["verdict"] = "Pathogenic"

            res = post("/step", payload)

            if "error" in res:
                return text + f"✗ Pipeline error: {res['error']}\n"

            reward = extract_reward(res)
            reward_str = f"+{reward}" if reward and reward > 0 else str(reward)
            sign = "▲" if reward and reward > 0 else "▼" if reward and reward < 0 else "→"

            text += f"→ {display_name}\n  {sign} reward: {reward_str}\n\n"

            if res.get("done"):
                text += "✓ PIPELINE COMPLETE\n"
                break

        return text

    gr.Button("⟡  RUN PIPELINE", variant="primary", size="lg", elem_classes="btn-primary-custom").click(
        run, outputs=output
    )


# ------------------ App ------------------ #
def create_app():
    custom_css = """
    /* ── Design tokens ──────────────────────────────────────── */
    :root {
        --bg-base:        #080d14;
        --bg-surface:     #0d1520;
        --bg-raised:      #111c2b;
        --bg-hover:       #162030;
        --border:         #1e2f45;
        --border-bright:  #2a4060;
        --text-primary:   #d4e8ff;
        --text-secondary: #6a8daf;
        --text-muted:     #3d5570;
        --accent-cyan:    #00d4ff;
        --accent-green:   #00e5a0;
        --accent-amber:   #f5a623;
        --accent-red:     #ff4f6a;
        --accent-violet:  #8b5cf6;
        --font-mono:      'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
        --font-ui:        'DM Sans', 'Outfit', 'Manrope', sans-serif;
    }

    /* ── Google Fonts import ──────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Global resets ───────────────────────────────────── */
    .gradio-container, .gradio-container * {
        font-family: var(--font-ui) !important;
        box-sizing: border-box;
    }

    body, .gradio-container {
        background: var(--bg-base) !important;
        color: var(--text-primary) !important;
    }

    /* ── Scrollbar ───────────────────────────────────────── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg-surface); }
    ::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 2px; }

    /* ── Main header ─────────────────────────────────────── */
    .app-header {
        text-align: center;
        padding: 48px 32px 40px;
        position: relative;
        overflow: hidden;
    }
    .app-header::before {
        content: '';
        position: absolute;
        top: -60px; left: 50%; transform: translateX(-50%);
        width: 600px; height: 200px;
        background: radial-gradient(ellipse at center, rgba(0,212,255,0.12) 0%, transparent 70%);
        pointer-events: none;
    }
    .header-eyebrow {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 4px;
        color: var(--accent-cyan);
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .header-title {
        font-size: 52px;
        font-weight: 600;
        letter-spacing: -1.5px;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 12px;
    }
    .header-title .accent { color: var(--accent-cyan); }
    .header-sub {
        font-size: 15px;
        color: var(--text-secondary);
        font-weight: 300;
        letter-spacing: 0.3px;
    }
    .header-rule {
        width: 60px; height: 1px;
        background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
        margin: 20px auto 0;
    }

    /* ── Tabs ───────────────────────────────────────────── */
    .tabs { background: transparent !important; border: none !important; }
    .tab-nav {
        background: var(--bg-surface) !important;
        border-bottom: 1px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 0 24px !important;
        gap: 0 !important;
    }
    .tab-nav button {
        font-family: var(--font-mono) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: var(--text-muted) !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        padding: 16px 24px !important;
        border-radius: 0 !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }
    .tab-nav button:hover {
        color: var(--text-secondary) !important;
        background: rgba(0,212,255,0.03) !important;
        transform: none !important;
        box-shadow: none !important;
    }
    .tab-nav button.selected {
        color: var(--accent-cyan) !important;
        border-bottom-color: var(--accent-cyan) !important;
    }
    .tabitem { padding: 28px !important; }

    /* ── Tab section headers ─────────────────────────────── */
    .tab-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px 24px;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        margin-bottom: 24px;
    }
    .tab-header-icon {
        font-size: 28px;
        color: var(--accent-cyan);
        line-height: 1;
    }
    .tab-header-title {
        font-family: var(--font-mono) !important;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 3px;
        color: var(--text-primary);
    }
    .tab-header-sub {
        font-size: 13px;
        color: var(--text-secondary);
        margin-top: 2px;
    }

    /* ── Protein card ────────────────────────────────────── */
    .protein-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 28px;
        position: relative;
        overflow: hidden;
        min-height: 240px;
        transition: border-color 0.3s ease;
    }
    .protein-card.loaded {
        border-color: var(--border-bright);
    }
    .protein-card.loaded::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
    }
    .protein-card.empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .empty-icon {
        font-size: 48px;
        color: var(--text-muted);
        margin-bottom: 12px;
        animation: pulse 3s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 0.4; }
        50% { opacity: 0.8; }
    }
    .empty-title {
        font-family: var(--font-mono) !important;
        font-size: 16px;
        color: var(--text-secondary);
        margin: 0 0 6px 0;
        letter-spacing: 1px;
    }
    .empty-sub { font-size: 13px; color: var(--text-muted); margin: 0; }

    /* card internals */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 24px;
    }
    .gene-label {
        font-family: var(--font-mono) !important;
        font-size: 10px;
        letter-spacing: 3px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .gene-name {
        font-size: 32px;
        font-weight: 600;
        color: var(--accent-cyan);
        letter-spacing: -1px;
        line-height: 1;
        margin-bottom: 8px;
    }
    .mutation-id-badge {
        display: inline-block;
        font-family: var(--font-mono) !important;
        font-size: 11px;
        color: var(--text-muted);
        background: var(--bg-raised);
        border: 1px solid var(--border);
        padding: 3px 10px;
        border-radius: 4px;
    }
    .budget-display {
        text-align: right;
    }
    .budget-label {
        font-family: var(--font-mono) !important;
        font-size: 10px;
        letter-spacing: 3px;
        color: var(--text-muted);
        margin-bottom: 2px;
    }
    .budget-value {
        font-family: var(--font-mono) !important;
        font-size: 40px;
        font-weight: 600;
        color: var(--accent-green);
        line-height: 1;
    }
    .budget-sub {
        font-size: 11px;
        color: var(--text-muted);
    }

    /* mutation display */
    .mutation-display {
        display: flex;
        align-items: center;
        gap: 12px;
        background: var(--bg-raised);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }
    .aa-block {
        text-align: center;
    }
    .aa-label {
        font-family: var(--font-mono) !important;
        font-size: 9px;
        letter-spacing: 2px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .aa-code {
        font-family: var(--font-mono) !important;
        font-size: 36px;
        font-weight: 600;
        line-height: 1;
    }
    .ref-block .aa-code { color: var(--text-secondary); }
    .mut-block .aa-code { color: var(--accent-amber); }
    .mutation-arrow {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 0 8px;
    }
    .arrow-line {
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, var(--border-bright), var(--accent-amber));
    }
    .arrow-head {
        color: var(--accent-amber);
        font-size: 12px;
    }
    .position-badge {
        margin-left: auto;
        background: var(--bg-base);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 8px 14px;
        text-align: center;
    }
    .pos-label {
        font-family: var(--font-mono) !important;
        font-size: 9px;
        letter-spacing: 2px;
        color: var(--text-muted);
        display: block;
        margin-bottom: 2px;
    }
    .pos-value {
        font-family: var(--font-mono) !important;
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
    }

    /* progress */
    .progress-section {}
    .progress-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .progress-label {
        font-family: var(--font-mono) !important;
        font-size: 10px;
        letter-spacing: 2px;
        color: var(--text-muted);
    }
    .progress-count {
        font-family: var(--font-mono) !important;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .progress-total { color: var(--text-muted); }
    .progress-track {
        height: 3px;
        background: var(--bg-raised);
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .progress-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.5s ease;
        box-shadow: 0 0 8px currentColor;
    }
    .step-dots {
        display: flex;
        gap: 5px;
    }
    .step-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--bg-raised);
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }
    .step-dot.filled { border-color: transparent; }
    .step-dot.filled.status-green { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
    .step-dot.filled.status-amber { background: var(--accent-amber); box-shadow: 0 0 6px var(--accent-amber); }
    .step-dot.filled.status-red   { background: var(--accent-red);   box-shadow: 0 0 6px var(--accent-red); }

    /* ── Info panels ─────────────────────────────────────── */
    .info-panel, .reward-panel {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 24px;
    }
    .panel-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border);
    }
    .panel-icon {
        color: var(--accent-cyan);
        font-size: 18px;
    }
    .panel-title {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 3px;
        color: var(--text-secondary);
        font-weight: 500;
    }

    /* tool items */
    .tool-item {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding: 14px 0;
        border-bottom: 1px solid var(--border);
    }
    .tool-item:last-child { border-bottom: none; }
    .tool-icon {
        font-family: var(--font-mono) !important;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
        padding: 6px 8px;
        border-radius: 6px;
        flex-shrink: 0;
        min-width: 44px;
        text-align: center;
    }
    .tool-icon.conservation { background: rgba(0,212,255,0.1);  color: var(--accent-cyan);   border: 1px solid rgba(0,212,255,0.2); }
    .tool-icon.ddg          { background: rgba(0,229,160,0.1);  color: var(--accent-green);  border: 1px solid rgba(0,229,160,0.2); }
    .tool-icon.domain       { background: rgba(245,166,35,0.1); color: var(--accent-amber);  border: 1px solid rgba(245,166,35,0.2); }
    .tool-name {
        font-size: 13px;
        font-weight: 500;
        color: var(--text-primary);
        margin-bottom: 4px;
    }
    .tool-desc {
        font-size: 12px;
        color: var(--text-muted);
        line-height: 1.5;
    }

    /* reward items */
    .reward-item {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 14px 0;
        border-bottom: 1px solid var(--border);
    }
    .reward-item:last-child { border-bottom: none; }
    .reward-indicator {
        width: 32px; height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        flex-shrink: 0;
    }
    .reward-item.positive .reward-indicator { background: rgba(0,229,160,0.12); color: var(--accent-green); border: 1px solid rgba(0,229,160,0.25); }
    .reward-item.negative .reward-indicator { background: rgba(255,79,106,0.12); color: var(--accent-red);   border: 1px solid rgba(255,79,106,0.25); }
    .reward-item.neutral  .reward-indicator { background: rgba(0,212,255,0.08); color: var(--accent-cyan);  border: 1px solid rgba(0,212,255,0.2); }
    .reward-name { font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 3px; }
    .reward-desc { font-size: 12px; color: var(--text-muted); line-height: 1.5; }

    /* ── Log box ─────────────────────────────────────────── */
    .log-box textarea, .log-box .gr-textbox textarea {
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
        line-height: 1.8 !important;
        background: var(--bg-base) !important;
        color: var(--accent-green) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        padding: 16px !important;
        caret-color: var(--accent-cyan);
    }

    /* ── Form controls ─────────────────────────────────── */
    .gr-textbox, .gr-dropdown {
        border-radius: 8px !important;
    }
    label.svelte-1b6s6wi,
    .block > label > span {
        font-family: var(--font-mono) !important;
        font-size: 10px !important;
        letter-spacing: 2px !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
    }
    input, textarea, select, .wrap {
        background: var(--bg-surface) !important;
        border-color: var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }
    input:focus, textarea:focus {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 0 2px rgba(0,212,255,0.08) !important;
        outline: none !important;
    }
    .svelte-phx28p, [data-testid="dropdown"] {
        background: var(--bg-surface) !important;
        border-color: var(--border) !important;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    button {
        font-family: var(--font-mono) !important;
        font-size: 11px !important;
        letter-spacing: 2px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        border-radius: 8px !important;
        border: none !important;
        cursor: pointer;
        transition: all 0.2s ease !important;
        position: relative;
        overflow: hidden;
    }
    button::after {
        content: '';
        position: absolute;
        inset: 0;
        background: rgba(255,255,255,0);
        transition: background 0.15s ease;
    }
    button:hover::after { background: rgba(255,255,255,0.06); }
    button:active { transform: scale(0.98) !important; }
    button:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important; }

    .btn-primary-custom, button.primary, button[variant="primary"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #00d4ff 100%) !important;
        color: #080d14 !important;
    }
    .btn-secondary-custom, button.secondary, button[variant="secondary"] {
        background: var(--bg-raised) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border) !important;
    }
    .action-row {
        margin-top: 20px !important;
        gap: 12px !important;
    }

    /* ── Footer ──────────────────────────────────────────── */
    .app-footer {
        text-align: center;
        padding: 24px;
        margin-top: 20px;
        border-top: 1px solid var(--border);
    }
    .app-footer p {
        font-family: var(--font-mono) !important;
        font-size: 11px;
        letter-spacing: 1px;
        color: var(--text-muted);
        margin: 0;
    }
    .app-footer .accent { color: var(--accent-cyan); }
    """

    with gr.Blocks(
        title="MutantBench",
        css=custom_css,
        theme=gr.themes.Base(
            primary_hue="sky",
            secondary_hue="slate",
            neutral_hue="slate",
            font=["DM Sans", "system-ui", "sans-serif"],
        )
    ) as app:

        gr.HTML("""
        <div class="app-header">
            <div class="header-eyebrow">PROTEIN MUTATION ANALYSIS PLATFORM</div>
            <div class="header-title">Mutant<span class="accent">Bench</span></div>
            <div class="header-sub">Conservation · Stability · Domain Annotation · Pathogenicity</div>
            <div class="header-rule"></div>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("Dashboard", id="dashboard"):
                dashboard_tab()

            with gr.Tab("Manual Control", id="control"):
                control_tab()

            with gr.Tab("Auto Demo", id="demo"):
                demo_tab()

        gr.HTML("""
        <div class="app-footer">
            <p>MutantBench · AI-Powered Variant Classification · <span class="accent">v1.0</span></p>
        </div>
        """)

    return app


if __name__ == "__main__":
    create_app().launch(server_name="0.0.0.0", server_port=7860)