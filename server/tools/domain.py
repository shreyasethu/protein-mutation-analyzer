import json
from pathlib import Path
from models import DomainToolOutput


DATA_PATH = Path(__file__).parent.parent / "data" / "mutations.json"


DOMAIN_DESCRIPTIONS = {
   "BRCT domain": "Mediates protein-protein interactions in DNA damage response; required for BRCA1 tumor suppressor function.",
   "OB fold domain": "Binds single-stranded DNA; essential for BRCA2-mediated homologous recombination repair.",
   "DNA-binding domain": "Directly contacts DNA to activate or repress transcription; most TP53 cancer mutations cluster here.",
   "NBD1 domain": "Nucleotide-binding domain 1; essential for CFTR chloride channel folding and gating.",
   "Cysteine-rich repeat": "Structural motif stabilized by disulfide bonds; critical for LDL receptor ligand binding.",
   "ATPase domain": "Hydrolyzes ATP to drive conformational changes required for MLH1 mismatch repair activity.",
   "Clamp domain": "Encircles DNA during mismatch scanning; loss disrupts MSH2 repair complex formation.",
   "Phosphatase domain": "Catalytic core of PTEN; dephosphorylates PIP3 to suppress PI3K/AKT oncogenic signaling.",
   "Armadillo repeat domain": "Mediates protein-protein interactions in APC; loss disrupts beta-catenin degradation complex.",
   "Beta domain": "Binds elongin C in VHL complex; mutations prevent HIF-1alpha ubiquitination and degradation.",
   "Pocket domain A": "Part of RB1 pocket domain; binds E2F transcription factors to suppress cell cycle entry.",
   "FAT domain": "FRAP-ATM-TRRAP regulatory domain; controls ATM kinase activation at DNA double-strand breaks.",
   "Receptor-binding domain": "Mediates APOE binding to LDL receptor family; isoform determines cardiovascular risk.",
}


def _load_mutations():
   with open(DATA_PATH) as f:
       return {m["id"]: m for m in json.load(f)}


def get_domain_annotation(mutation_id: str) -> DomainToolOutput:
   mutations = _load_mutations()


   if mutation_id not in mutations:
       raise ValueError(f"Unknown mutation_id: {mutation_id}")


   record = mutations[mutation_id]
   domain = record["domain"]
   description = DOMAIN_DESCRIPTIONS.get(
       domain,
       f"{domain}: functional domain with established role in protein activity and disease."
   )


   return DomainToolOutput(
       domain_name=domain,
       is_critical=record["domain_critical"],
       function_description=description
   )
