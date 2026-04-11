# models.py

from pydantic import BaseModel
from typing import Optional, List, Literal, Dict, Any
from openenv.core.env_server.types import Action, Observation as OpenEnvObservation


# ─── Tool Input Schemas ───────────────────────────────────────────────────────

class ConservationToolInput(BaseModel):
    mutation_id: str


class StructureToolInput(BaseModel):
    mutation_id: str


class DomainToolInput(BaseModel):
    mutation_id: str


class VerdictToolInput(BaseModel):
    mutation_id: str
    verdict: Literal["Pathogenic", "Benign", "Uncertain"]


# ─── Tool Output Schemas ──────────────────────────────────────────────────────

class ConservationToolOutput(BaseModel):
    phylop_score: float
    conservation_level: Literal["high", "medium", "low"]
    interpretation: str


class StructureToolOutput(BaseModel):
    ddg_estimate: float
    stability_impact: Literal["destabilizing", "neutral", "stabilizing"]
    confidence: Literal["high", "medium", "low"]


class DomainToolOutput(BaseModel):
    domain_name: str
    is_critical: bool
    function_description: str


class VerdictToolOutput(BaseModel):
    accepted: bool
    episode_done: bool


# ─── Observation Schema (what the agent sees) ────────────────────────────────

class Observation(BaseModel):
    mutation_id: str
    gene: str
    position: int
    ref_aa: str
    mut_aa: str
    sequence_context: str

    conservation_result: Optional[ConservationToolOutput] = None
    structure_result: Optional[StructureToolOutput] = None
    domain_result: Optional[DomainToolOutput] = None

    steps_taken: int = 0
    step_budget: int = 6

    budget_spent: float = 0.0
    budget_remaining: float = 6.0

    tools_called: List[str] = []
    episode_done: bool = False


# ─── State Schema (internal, includes ground truth) ──────────────────────────

class State(BaseModel):
    # Observation fields
    mutation_id: str
    gene: str
    position: int
    ref_aa: str
    mut_aa: str
    sequence_context: str

    conservation_result: Optional[ConservationToolOutput] = None
    structure_result: Optional[StructureToolOutput] = None
    domain_result: Optional[DomainToolOutput] = None

    steps_taken: int = 0
    step_budget: int = 6

    budget_spent: float = 0.0
    budget_remaining: float = 6.0

    tools_called: List[str] = []
    episode_done: bool = False

    # Ground truth (hidden from agent)
    ground_truth_label: str = ""
    deciding_factor: str = ""
    clinvar_confidence: str = ""
    task_tier: int = 1
    mistake_log: List[Dict[str, Any]] = []
    adversary_weakness_profile: Dict[str, Any] = {}


# ─── Reward Schema ────────────────────────────────────────────────────────────

class RewardBreakdown(BaseModel):
    step_reward: float = 0.0
    final_reward: Optional[float] = None

    geneticist_score: Optional[float] = None
    biologist_score: Optional[float] = None
    technician_score: Optional[float] = None

    redundancy_penalty: float = 0.0
    budget_penalty: float = 0.0

    total_reward: float = 0.0


# ─── Raw Mutation Record ─────────────────────────────────────────────────────

class MutationRecord(BaseModel):
    id: str
    gene: str
    position: int
    ref_aa: str
    mut_aa: str
    sequence_context: str

    phylop_score: float
    ddg_estimate: float

    domain: str
    domain_critical: bool

    clinvar_label: Literal["Pathogenic", "Benign", "Uncertain"]
    clinvar_confidence: Literal["high", "medium", "low"]

    task_tier: int
    deciding_factor: str

    chrom: Optional[str] = None
    genomic_pos: Optional[int] = None


# ─── OpenEnv Action / Observation Wrappers ───────────────────────────────────

class ProteinMutationAnalyzerAction(Action):
    tool_name: str = ""
    tool_input: Dict[str, Any] = {}


class ProteinMutationAnalyzerObservation(OpenEnvObservation):
    mutation_id: str = ""
    gene: str = ""
    position: int = 0
    ref_aa: str = ""
    mut_aa: str = ""
    sequence_context: str = ""

    conservation_result: Optional[ConservationToolOutput] = None
    structure_result: Optional[StructureToolOutput] = None
    domain_result: Optional[DomainToolOutput] = None

    steps_taken: int = 0
    step_budget: int = 6

    budget_spent: float = 0.0
    budget_remaining: float = 6.0

    tools_called: List[str] = []
    episode_done: bool = False