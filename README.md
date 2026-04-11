---
title: Protein Mutation Analyzer Environment Server
emoji: 🎬
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

A clinical environment for analyzing protein mutations and predicting pathogenicity.

## Quick Start

```python
from protein_mutation_analyzer import ProteinMutationAnalyzerEnv

env = ProteinMutationAnalyzerEnv(base_url="http://localhost:7860")

result = env.reset()
result = env.step(...)