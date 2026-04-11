---
title: Protein Mutation Analyzer Environment Server
emoji: 🧬
colorFrom: green
colorTo: yellow
sdk: docker
pinned: false
app_port: 7860
base_path: /web
tags:
  - openenv
---

# Protein Mutation Analyzer Environment

An OpenEnv environment for evaluating AI agents on clinical protein mutation pathogenicity classification. Given a protein mutation, an agent must query bioinformatics tools and submit a verdict of **Pathogenic**, **Benign**, or **Uncertain**.

## Quick Start

```python
from protein_mutation_analyzer import ProteinMutationAnalyzerAction, ProteinMutationAnalyzerEnv

try:
    env = ProteinMutationAnalyzerEnv.from_docker_image("protein-mutation-analyzer-env:latest")

    # Reset with a specific task tier (1=easy, 2=medium, 3=hard)
    obs = env.reset(task_id=1)
    print(f"Mutation: {obs.observation.gene} {obs.observation.ref_aa}{obs.observation.position}{obs.observation.mut_aa}")

    # Query a tool
    result = env.step(ProteinMutationAnalyzerAction(
        tool_name="get_conservation_score",
        tool_input={"mutation_id": obs.observation.mutation_id},
    ))
    print(f"Conservation result: {result.observation.conservation_result}")
    print(f"Reward: {result.reward}")

    # Submit final verdict
    final = env.step(ProteinMutationAnalyzerAction(
        tool_name="submit_verdict",
        tool_input={"mutation_id": obs.observation.mutation_id, "verdict": "Pathogenic"},
    ))
    print(f"Final reward: {final.reward}  done={final.observation.done}")

finally:
    env.close()
```

## Building the Docker Image

```bash
docker build -t protein-mutation-analyzer-env:latest .
```

## Deploying to Hugging Face Spaces

```bash
openenv push
```

## Environment Details

### Actions

**ProteinMutationAnalyzerAction**
| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | One of `get_conservation_score`, `get_ddg_estimate`, `get_domain_annotation`, `submit_verdict` |
| `tool_input` | `dict` | Arguments for the tool (always includes `mutation_id`; verdict tools also include `verdict`) |

### Observations

**ProteinMutationAnalyzerObservation**
| Field | Type | Description |
|-------|------|-------------|
| `mutation_id` | `str` | Unique mutation identifier |
| `gene` | `str` | Gene name (e.g. BRCA1) |
| `position` | `int` | Amino-acid position |
| `ref_aa` / `mut_aa` | `str` | Reference and mutant amino acids |
| `sequence_context` | `str` | 10-residue window around the mutation |
| `conservation_result` | `ConservationToolOutput \| None` | PhyloP score + level + interpretation |
| `structure_result` | `StructureToolOutput \| None` | ΔΔG estimate + stability impact + confidence |
| `domain_result` | `DomainToolOutput \| None` | Domain name + criticality + function description |
| `steps_taken` | `int` | Steps used so far |
| `budget_remaining` | `float` | Remaining step budget (starts at 6.0) |
| `tools_called` | `list[str]` | Tools called this episode |
| `episode_done` | `bool` | Whether the episode has ended |
| `reward` | `float \| None` | Step reward (in **[0.0, 1.0]**) |

### Reward

Rewards are always in **[0.0, 1.0]**.

- **Step rewards**: small positive rewards for informative tool calls; penalty (−0.15) for redundant calls.
- **Final reward** (on `submit_verdict`): weighted blend of three persona scores:
  - Clinical Geneticist (0.40) — assesses conservation signal vs. verdict
  - Structural Biologist (0.25) — assesses structural stability signal vs. verdict
  - Lab Technician (0.35) — assesses tool-call efficiency
  - Scaled by ClinVar confidence: high ×1.00, medium ×0.85, low ×0.70

### Tasks

| Task ID | Difficulty | Description |
|---------|-----------|-------------|
| 1 | **Easy** | Single-signal mutations — one tool gives a clear answer |
| 2 | **Medium** | Multi-signal mutations — two tools needed |
| 3 | **Hard** | Combined/ambiguous — all three tools needed; verdict may be Uncertain |

## Running Locally

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

The server exposes:
- **POST `/reset`** — reset the environment
- **POST `/step`** — execute a tool action
- **GET `/state`** — current environment state
- **GET `/schema`** — action/observation JSON schemas
- **WS `/ws`** — persistent WebSocket session
- **`/web`** — Gradio interactive UI

## Running the Inference Agent

```bash
API_BASE_URL=https://api.groq.com/openai/v1 \
MODEL_NAME=llama-3.3-70b-versatile \
HF_TOKEN=<your_key> \
ENV_BASE_URL=http://localhost:7860 \
python inference.py
```

Expected log format:
```
[START] task=task_tier_1_easy env=protein-mutation-analyzer model=llama-3.3-70b-versatile
[STEP]  step=1 action={"tool_name":"get_conservation_score",...} reward=0.13 done=false error=null
[END]   success=true steps=2 rewards=0.13,0.72
```

## Project Structure

```
protein-mutation-analyzer/
├── openenv.yaml           # OpenEnv manifest (tasks, runtime, metadata)
├── inference.py           # Agent inference script
├── Dockerfile             # Container image definition
├── README.md              # This file
├── requirements.txt       # Pinned dependencies
├── pyproject.toml         # Project metadata
├── uv.lock                # Locked dependency graph
├── client.py              # ProteinMutationAnalyzerEnv client
├── models.py              # Action / Observation / State / Reward models
└── server/
    ├── app.py             # FastAPI application (HTTP + WebSocket + Gradio)
    ├── environment.py     # Core environment logic (step / reset / state)
    ├── grader/
    │   ├── grader.py      # Reward aggregation
    │   └── personas.py    # Persona scorers (geneticist / biologist / technician)
    ├── tools/
    │   ├── conservation.py
    │   ├── structure.py
    │   ├── domain.py
    │   └── verdict.py
    └── data/
        └── mutations.json # ClinVar-derived mutation dataset
```
