---
title: Protein Mutation Analyzer Environment Server
emoji: 🎬
colorFrom: green
colorTo: yellow
sdk: docker
pinned: false
app_port: 7860
base_path: /
tags:
  - openenv
---

# Protein Mutation Analyzer Environment

A clinical reinforcement learning environment for analyzing protein mutations and predicting pathogenicity. It implements a biomedical workflow where an agent learns to classify protein mutations as **Pathogenic**, **Benign**, or **Uncertain**. The environment requires agents to synthesize biological signals—such as evolutionary conservation, structural stability, and domain context—to reach a final clinical decision.

## 🏗️ OpenEnv Architecture
The environment follows a standardized API contract for seamless agent–environment interaction:

* **`reset()`**: Initializes a new episode and mutation case.
* **`step(action)`**: Executes a tool call and returns `(observation, reward, done)`.
* **`state()`**: Returns the internal hidden state for debugging and logging.

## 🛠️ Environment Components

### 1. Action Space (Tools)
The agent interacts using structured tool calls. Each action incurs a cost and consumes a portion of the **6-step budget**.

| Tool Name | Description |
| :--- | :--- |
| `get_conservation_score` | Returns evolutionary signal (PhyloP). |
| `get_ddg_estimate` | Returns structural stability changes ($\Delta\Delta G$). |
| `get_domain_annotation` | Provides functional domain context. |
| `submit_verdict` | Final clinical classification. |


---
## 2. Observation Space
The observation progressively reveals information as the agent explores:
* **Mutation Metadata:** Gene name, position, and amino acids.
* **Tool Outputs:** Results from previously called tools.
* **Trajectory Tracking:** Current budget, steps taken, and tool history.

---

## 📊 Data & Curriculum
The environment is built on a curated dataset of mutation records including `phylop_score`, `ddg_estimate`, and `clinvar_label` (ground truth).

### Task Levels
A curriculum scheduler gradually increases difficulty:
* **Task 1 (Easy):** Single dominant signal (e.g., strong conservation).
* **Task 2 (Medium):** Multiple signals; requires combining evidence.
* **Task 3 (Hard):** Conflicting signals; requires identifying the "true" deciding factor.


### Reward system
When the agent calls a query tool, it gets immediate reward based on signal quality and relevance to the case’s `deciding_factor`.

- **Repeated tool call:** `0.0` (no gain)
- **`get_conservation_score`:**
  - `+0.08` if `|phylop_score| > 2`, else `+0.02`
  - `+0.05` bonus if deciding factor is `conservation` or `combined`
- **`get_ddg_estimate`:**
  - `+0.08` if `ddg < -2.0`
  - `+0.06` if `ddg > -0.5`
  - `+0.02` otherwise
  - `+0.05` bonus if deciding factor is `structure` or `combined`
- **`get_domain_annotation`:**
  - `+0.07` if domain is critical, else `+0.02`
  - `+0.05` bonus if deciding factor is `domain` or `combined`

### Final Reward (after verdict submission)
On `submit_verdict`, the environment computes a final reward from three persona scorers:

- **Clinical Geneticist:** `40%`
- **Structural Biologist:** `25%`
- **Lab Technician:** `35%`

\[
R_{\text{weighted}} = 0.40 \cdot G + 0.25 \cdot B + 0.35 \cdot T
\]

Then reward is capped by ClinVar confidence:

- **high:** cap `1.00`
- **medium:** cap `0.85`
- **low:** cap `0.70`

\[
R_{\text{final}} = \min(R_{\text{weighted}}, \text{confidence\_cap})
\]


## Quick Start

```python
from protein_mutation_analyzer import ProteinMutationAnalyzerEnv

env = ProteinMutationAnalyzerEnv(base_url="http://localhost:7860")

result = env.reset()
result = env.step(...)
