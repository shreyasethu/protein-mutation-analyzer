# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.




"""
FastAPI application for the Protein Mutation Analyzer Environment.


This module creates an HTTP server that exposes the ProteinMutationAnalyzerEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.


Additionally, mounts a Gradio UI at /web.


Endpoints:
  - POST /reset: Reset the environment
  - POST /step: Execute an action
  - GET /state: Get current environment state
  - GET /schema: Get action/observation schemas
  - WS /ws: WebSocket endpoint for persistent sessions
  - /web: Gradio UI


Usage:
  # Development (with auto-reload):
  uvicorn server.app:app --reload --host 0.0.0.0 --port 7860


  # Production:
  uvicorn server.app:app --host 0.0.0.0 --port 7860 --workers 4


  # Or run directly:
  python -m server.app
"""


# ── Imports ───────────────────────────────────────────────────────────────


try:
   from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
   raise ImportError(
       "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
   ) from e


try:
   from ..models import ProteinMutationAnalyzerAction, ProteinMutationAnalyzerObservation
   from .environment import ProteinMutationAnalyzerEnvironment
except ImportError:
   from models import ProteinMutationAnalyzerAction, ProteinMutationAnalyzerObservation
   from server.environment import ProteinMutationAnalyzerEnvironment


import gradio as gr




# ── Create OpenEnv FastAPI app ─────────────────────────────────────────────


app = create_app(
   ProteinMutationAnalyzerEnvironment,
   ProteinMutationAnalyzerAction,
   ProteinMutationAnalyzerObservation,
   env_name="protein_mutation_analyzer",
   max_concurrent_envs=1,
)

@app.get("/health")
def health():
    return {"status": "ok"}




# ── Mount Gradio UI at /web ───────────────────────────────────────────────


try:
   from server.gradio_app import create_app
except ImportError:
   from server.gradio_app import create_app


try:
   gradio_demo = create_app()
   app = gr.mount_gradio_app(app, gradio_demo, path="/")
except Exception as e:
   import logging
   logging.getLogger(__name__).warning(
       "Gradio UI failed to mount (non-fatal): %s", e
   )




# ── Entry point ──────────────────────────────────────────────────────────


def main(host: str = "0.0.0.0", port: int = 8000):
   """
   Entry point for direct execution via uv run or python -m.
   """
   import argparse
   import uvicorn


   parser = argparse.ArgumentParser()
   parser.add_argument("--port", type=int, default=port)
   args = parser.parse_args()


   uvicorn.run(app, host=host, port=args.port)




if __name__ == "__main__":
   main()
