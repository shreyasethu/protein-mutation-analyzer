import gradio as gr
import requests
import os

BASE = os.getenv("ENV_BASE_URL", "http://127.0.0.1:7860")


def post(path, payload):
    try:
        r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
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


# ------------------ Dashboard ------------------ #
def dashboard_tab():
    state = gr.State({"mutation_id": None})

    with gr.Row():
        with gr.Column(scale=2):
            mutation_id = gr.Textbox(label="Mutation ID", interactive=False)
            gene = gr.Textbox(label="Gene", interactive=False)
            change = gr.Textbox(label="Change", interactive=False)

        with gr.Column(scale=2):
            position = gr.Textbox(label="Position", interactive=False)
            steps = gr.Textbox(label="Steps", interactive=False)
            budget = gr.Textbox(label="Budget Remaining", interactive=False)

    log = gr.Textbox(label="Step Log", lines=12)

    def reset():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")

        summary = format_summary(obs)

        return (
            {"mutation_id": mid},
            *summary,
            "Initialized\n"
        )

    def step(state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, "-", "-", "-", "-", "-", "-", "❌ Reset first"

        tools = [
            "get_conservation_score",
            "get_ddg_estimate",
            "get_domain_annotation"
        ]

        current_steps = log_text.count("→") if log_text else 0
        tool = tools[current_steps % len(tools)]

        # ✅ FIXED PAYLOAD
        res = post("/step", {
            "tool_name": tool,
            "tool_input": {"mutation_id": mid}
        })

        if "error" in res:
            log_text = append_log(log_text, f"❌ {res['error']}")
            return state, *format_summary({}), log_text

        obs = extract_obs(res)
        reward = res.get("reward") or res.get("observation", {}).get("reward")

        summary = format_summary(obs)
        log_text = append_log(log_text, f"{tool} → reward {reward}")

        return state, *summary, log_text

    with gr.Row():
        reset_btn = gr.Button("Reset", variant="primary")
        step_btn = gr.Button("Run Step")

    reset_btn.click(
        reset,
        outputs=[state, mutation_id, gene, change, position, steps, budget, log]
    )

    step_btn.click(
        step,
        inputs=[state, log],
        outputs=[state, mutation_id, gene, change, position, steps, budget, log]
    )


# ------------------ Control ------------------ #
def control_tab():
    state = gr.State({"mutation_id": None})

    with gr.Row():
        tool = gr.Dropdown(
            ["get_conservation_score", "get_ddg_estimate", "get_domain_annotation", "submit_verdict"],
            value="get_conservation_score",
            label="Tool"
        )

        verdict = gr.Dropdown(
            ["Pathogenic", "Benign", "Uncertain"],
            value="Pathogenic",
            label="Verdict"
        )

    log = gr.Textbox(label="Execution Log", lines=12)

    def reset():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")

        return {"mutation_id": mid}, "Initialized\n"

    def step(tool, verdict, state, log_text):
        mid = state["mutation_id"]

        if not mid:
            return state, "❌ Reset first"

        # ✅ FIXED PAYLOAD
        payload = {
            "tool_name": tool,
            "tool_input": {"mutation_id": mid}
        }

        if tool == "submit_verdict":
            payload["tool_input"]["verdict"] = verdict

        res = post("/step", payload)

        if "error" in res:
            log_text = append_log(log_text, f"❌ {res['error']}")
            return state, log_text
        
        reward = res.get("reward") or res.get("observation", {}).get("reward")

        log_text = append_log(
            log_text,
            f"{tool} → reward {reward}"
        )

        return state, log_text

    with gr.Row():
        reset_btn = gr.Button("Reset")
        run_btn = gr.Button("Run Action", variant="primary")

    reset_btn.click(reset, outputs=[state, log])
    run_btn.click(step, inputs=[tool, verdict, state, log], outputs=[state, log])


# ------------------ Demo ------------------ #
def demo_tab():
    output = gr.Textbox(label="Pipeline Output", lines=15)

    def run():
        res = post("/reset", {})
        obs = extract_obs(res)
        mid = obs.get("mutation_id")

        text = f"Start: {mid}\n\n"

        for tool in [
            "get_conservation_score",
            "get_ddg_estimate",
            "get_domain_annotation",
            "submit_verdict",
        ]:
            # ✅ FIXED PAYLOAD
            payload = {
                "tool_name": tool,
                "tool_input": {"mutation_id": mid}
            }

            if tool == "submit_verdict":
                payload["tool_input"]["verdict"] = "Pathogenic"

            res = post("/step", payload)

            if "error" in res:
                text += f"❌ {res['error']}\n"
                break

            reward = res.get("reward") or res.get("observation", {}).get("reward")
            text += f"{tool} → reward {reward}\n"

            if res.get("done"):
                break

        return text

    gr.Button("Run Full Pipeline", variant="primary").click(run, outputs=output)


# ------------------ App ------------------ #
def create_app():
    with gr.Blocks(title="MutantBench") as app:
        gr.Markdown("# 🧬 MutantBench")

        with gr.Tabs():
            with gr.Tab("Dashboard"):
                dashboard_tab()

            with gr.Tab("Control"):
                control_tab()

            with gr.Tab("Demo"):
                demo_tab()

    return app


if __name__ == "__main__":
    create_app().launch(server_name="0.0.0.0", server_port=7860)