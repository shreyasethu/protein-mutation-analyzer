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
    """Create an interactive protein mutation card with visual styling"""
    if not obs:
        return """
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
            <h2 style="margin: 0; font-size: 24px;">🧬 No Mutation Loaded</h2>
            <p style="margin-top: 10px; opacity: 0.9;">Click "Reset" to load a mutation</p>
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
    
    # Progress bar
    progress_pct = (steps_taken / step_budget * 100) if step_budget > 0 else 0
    progress_color = "#4ade80" if progress_pct < 50 else "#fbbf24" if progress_pct < 80 else "#f87171"
    
    return f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div>
                <h2 style="margin: 0; font-size: 28px;">🧬 {gene}</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">ID: {mutation_id}</p>
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 15px 25px; border-radius: 10px; backdrop-filter: blur(10px);">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">Budget Remaining</div>
                <div style="font-size: 32px; font-weight: bold;">{budget_remaining}</div>
            </div>
        </div>
        
        <div style="background: rgba(255,255,255,0.15); padding: 25px; border-radius: 12px; backdrop-filter: blur(10px); margin-bottom: 20px;">
            <div style="text-align: center; margin-bottom: 15px;">
                <span style="font-size: 48px; font-weight: bold; font-family: monospace;">{ref_aa}</span>
                <span style="font-size: 36px; margin: 0 20px; opacity: 0.8;">→</span>
                <span style="font-size: 48px; font-weight: bold; font-family: monospace;">{mut_aa}</span>
            </div>
            <div style="text-align: center; font-size: 18px; opacity: 0.9;">
                Position <span style="font-weight: bold; font-family: monospace;">{position}</span>
            </div>
        </div>
        
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
                <span>Analysis Progress</span>
                <span>{steps_taken} / {step_budget} steps</span>
            </div>
            <div style="background: rgba(255,255,255,0.2); height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="background: {progress_color}; height: 100%; width: {progress_pct}%; transition: width 0.3s ease;"></div>
            </div>
        </div>
    </div>
    """


def create_tool_info_card():
    """Create an informative card explaining the tools"""
    return """
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 25px; border-radius: 15px; color: white; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
        <h3 style="margin-top: 0; font-size: 22px;">🔬 Analysis Tools</h3>
        
        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; margin-bottom: 12px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">📊 Conservation Score</div>
            <div style="font-size: 14px; opacity: 0.95;">Measures how conserved the amino acid is across species. Higher conservation often means the position is functionally important.</div>
        </div>
        
        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; margin-bottom: 12px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">⚡ ΔΔG Estimate</div>
            <div style="font-size: 14px; opacity: 0.95;">Predicts the change in protein stability. Large positive values suggest destabilizing mutations that may disrupt protein function.</div>
        </div>
        
        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">🎯 Domain Annotation</div>
            <div style="font-size: 14px; opacity: 0.95;">Identifies which protein domain contains the mutation. Mutations in critical domains (e.g., binding sites) are more likely to be pathogenic.</div>
        </div>
    </div>
    """


def create_reward_explainer():
    """Create a card explaining the reward system"""
    return """
    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 25px; border-radius: 15px; color: #2d3748; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
        <h3 style="margin-top: 0; font-size: 22px;">🎯 Reward System</h3>
        
        <div style="background: rgba(255,255,255,0.5); padding: 15px; border-radius: 10px; margin-bottom: 12px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">✅ Positive Rewards</div>
            <div style="font-size: 14px;">Earned when you correctly identify a pathogenic mutation or use tools efficiently. Higher rewards indicate better diagnostic accuracy!</div>
        </div>
        
        <div style="background: rgba(255,255,255,0.5); padding: 15px; border-radius: 10px; margin-bottom: 12px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">❌ Negative Rewards</div>
            <div style="font-size: 14px;">Applied when you make incorrect predictions or waste budget on unnecessary tools. Learn to balance thoroughness with efficiency!</div>
        </div>
        
        <div style="background: rgba(255,255,255,0.5); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
            <div style="font-weight: bold; margin-bottom: 8px; font-size: 16px;">💰 Budget Management</div>
            <div style="font-size: 14px;">Each tool use costs budget points. The goal is to make accurate predictions while conserving resources for future analyses.</div>
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
                label="📋 Step-by-Step Analysis Log",
                lines=14,
                show_label=True,
                placeholder="Analysis steps will appear here...",
                elem_classes="log-box"
            )

    def reset():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")

        return (
            {"mutation_id": mid},
            create_protein_card(obs),
            "🔄 Environment initialized\n✨ New mutation loaded and ready for analysis!\n"
        )

    def step(state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, create_protein_card(None), "❌ Please reset first to load a mutation"

        tools = [
            "get_conservation_score",
            "get_ddg_estimate",
            "get_domain_annotation"
        ]

        current_steps = log_text.count("→") if log_text else 0
        tool = tools[current_steps % len(tools)]
        
        # Tool emojis for better visualization
        tool_emoji = {
            "get_conservation_score": "📊",
            "get_ddg_estimate": "⚡",
            "get_domain_annotation": "🎯"
        }

        payload = {
            "action": {
                "tool_name": tool,
                "tool_input": {"mutation_id": mid}
            }
        }

        res = post("/step", payload)

        if "error" in res:
            return state, create_protein_card({}), append_log(log_text, f"❌ Error: {res['error']}")

        obs = extract_obs(res)
        reward = extract_reward(res)
        
        emoji = tool_emoji.get(tool, "🔧")
        reward_emoji = "🎉" if reward and reward > 0 else "⚠️" if reward and reward < 0 else "➡️"
        
        new_log = append_log(
            log_text,
            f"{emoji} {tool.replace('_', ' ').title()}\n   {reward_emoji} Reward: {reward}\n"
        )

        return state, create_protein_card(obs), new_log

    with gr.Row():
        reset_btn = gr.Button("🔄 Reset & Load New Mutation", variant="primary", size="lg")
        step_btn = gr.Button("▶️ Run Next Analysis Step", variant="secondary", size="lg")

    reset_btn.click(
        reset,
        outputs=[state, protein_card, log]
    )
    step_btn.click(
        step,
        inputs=[state, log],
        outputs=[state, protein_card, log]
    )


# ------------------ Control ------------------ #
def control_tab():
    state = gr.State({"mutation_id": None})
    
    gr.Markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
        <h2 style="margin: 0 0 10px 0;">🎮 Manual Control Panel</h2>
        <p style="margin: 0; opacity: 0.9;">Take full control of the analysis pipeline. Choose which tools to run and submit your verdict.</p>
    </div>
    """)

    with gr.Row():
        with gr.Column():
            tool = gr.Dropdown(
                ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation", "submit_verdict"],
                value="get_conservation_score",
                label="🔧 Select Analysis Tool",
                info="Choose which tool to execute on the current mutation"
            )

        with gr.Column():
            verdict = gr.Dropdown(
                ["Pathogenic", "Benign", "Uncertain"],
                value="Pathogenic",
                label="⚖️ Pathogenicity Verdict",
                info="Your classification for this mutation"
            )

    log = gr.Textbox(
        label="📊 Execution Log",
        lines=12,
        placeholder="Execution results will appear here...",
        show_label=True
    )

    def reset():
        res = post("/reset", {})
        return (
            {"mutation_id": extract_obs(res).get("mutation_id")},
            "🔄 Environment reset complete\n✨ New mutation loaded!\n"
        )

    def step(tool, verdict, state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, "❌ Please reset first to load a mutation\n"

        tool_emoji = {
            "get_conservation_score": "📊",
            "get_ddg_estimate": "⚡",
            "get_domain_annotation": "🎯",
            "submit_verdict": "⚖️"
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
            return state, append_log(log_text, f"❌ Error: {res['error']}\n")

        reward = extract_reward(res)
        emoji = tool_emoji.get(tool, "🔧")
        reward_emoji = "🎉" if reward and reward > 0 else "⚠️" if reward and reward < 0 else "➡️"
        
        new_log = append_log(
            log_text,
            f"{emoji} {tool.replace('_', ' ').title()}\n   {reward_emoji} Reward: {reward}\n"
        )

        return state, new_log

    with gr.Row():
        gr.Button("🔄 Reset Environment", variant="secondary", size="lg").click(
            reset,
            outputs=[state, log]
        )
        gr.Button("▶️ Execute Action", variant="primary", size="lg").click(
            step,
            inputs=[tool, verdict, state, log],
            outputs=[state, log]
        )


# ------------------ Demo ------------------ #
def demo_tab():
    gr.Markdown("""
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;">
        <h2 style="margin: 0 0 10px 0;">🚀 Automated Pipeline Demo</h2>
        <p style="margin: 0; opacity: 0.9;">Watch the complete analysis pipeline run automatically from start to finish!</p>
    </div>
    """)
    
    output = gr.Textbox(
        label="🔬 Pipeline Execution Log",
        lines=15,
        placeholder="Click 'Run Full Pipeline' to start the automated analysis...",
        show_label=True
    )

    def run():
        res = post("/reset", {})
        mid = extract_obs(res).get("mutation_id")

        text = f"🧬 Starting automated analysis pipeline\n📋 Mutation ID: {mid}\n\n"

        tools = [
            ("get_conservation_score", "📊 Conservation Analysis"),
            ("get_ddg_estimate", "⚡ Stability Prediction"),
            ("get_domain_annotation", "🎯 Domain Mapping"),
            ("submit_verdict", "⚖️ Final Verdict"),
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
                return text + f"❌ Pipeline failed: {res['error']}\n"

            reward = extract_reward(res)
            reward_emoji = "🎉" if reward and reward > 0 else "⚠️" if reward and reward < 0 else "➡️"
            
            text += f"{display_name}\n   {reward_emoji} Reward: {reward}\n\n"

            if res.get("done"):
                text += "✅ Analysis complete!\n"
                break

        return text

    gr.Button("🚀 Run Full Pipeline", variant="primary", size="lg").click(
        run,
        outputs=output
    )


# ------------------ App ------------------ #
def create_app():
    # Custom CSS for beautiful styling
    custom_css = """
    .gradio-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }
    
    .log-box textarea {
        font-family: 'Monaco', 'Menlo', 'Courier New', monospace !important;
        font-size: 13px !important;
        line-height: 1.6 !important;
    }
    
    button {
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    .primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
    }
    
    .secondary {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        border: none !important;
    }
    
    .tabs {
        border-radius: 12px !important;
    }
    
    .tab-nav button {
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
    }
    """

    with gr.Blocks(title="MutantBench 🧬", css=custom_css, theme=gr.themes.Soft(
        primary_hue="purple",
        secondary_hue="pink",
        neutral_hue="slate",
        font=["Inter", "system-ui", "sans-serif"]
    )) as app:
        gr.Markdown("""
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px; color: white;">
            <h1 style="margin: 0; font-size: 48px; font-weight: 800;">🧬 MutantBench</h1>
            <p style="margin: 10px 0 0 0; font-size: 20px; opacity: 0.95;">AI-Powered Protein Mutation Analysis Platform</p>
            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.8;">Analyze pathogenic mutations using conservation scores, stability predictions, and domain annotations</p>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("📊 Dashboard", id="dashboard"):
                dashboard_tab()
            
            with gr.Tab("🎮 Manual Control", id="control"):
                control_tab()
            
            with gr.Tab("🚀 Auto Demo", id="demo"):
                demo_tab()

        gr.Markdown("""
        <div style="text-align: center; padding: 20px; margin-top: 30px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
            <p style="margin: 0;">Built with ❤️ for protein mutation analysis | Powered by MutantBench</p>
        </div>
        """)

    return app


if __name__ == "__main__":
    create_app().launch(server_name="0.0.0.0", server_port=7860)