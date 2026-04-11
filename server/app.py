# app.py

"""
Protein Mutation Analyzer - Combined UI + OpenEnv Server
"""

# ── Imports ───────────────────────────────────────────────────────────────

from fastapi import FastAPI

try:
    from openenv.core.env_server.http_server import create_app as create_openenv_app
except Exception as e:
    raise ImportError("openenv required. Run: uv sync") from e

try:
    from server.gradio_app import create_app as create_gradio_app
except Exception:
    create_gradio_app = None

try:
    from ..models import ProteinMutationAnalyzerAction, ProteinMutationAnalyzerObservation
    from .environment import ProteinMutationAnalyzerEnvironment
except ImportError:
    from models import ProteinMutationAnalyzerAction, ProteinMutationAnalyzerObservation
    from server.environment import ProteinMutationAnalyzerEnvironment

import gradio as gr


# ── Create OpenEnv FastAPI app ─────────────────────────────────────────────

fastapi_app = create_openenv_app(
    ProteinMutationAnalyzerEnvironment,
    ProteinMutationAnalyzerAction,
    ProteinMutationAnalyzerObservation,
    env_name="protein_mutation_analyzer",
    max_concurrent_envs=1,
)


# ── Health check ──────────────────────────────────────────────────────────

@fastapi_app.get("/health")
def health():
    return {"status": "ok"}


# ── Create Gradio UI ──────────────────────────────────────────────────────

if create_gradio_app is not None:
    try:
        gradio_demo = create_gradio_app()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to create Gradio app: %s", e
        )
        gradio_demo = None
else:
    gradio_demo = None


# ── Mount Gradio at ROOT (key fix) ─────────────────────────────────────────

if gradio_demo is not None:
    app = gr.mount_gradio_app(fastapi_app, gradio_demo, path="/")
else:
    app = fastapi_app


# ── Entry point ──────────────────────────────────────────────────────────

def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()