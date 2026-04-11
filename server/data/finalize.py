import json
import requests

# -----------------------------
# LOAD INPUT
# -----------------------------
with open("clinvar_final.json") as f:
    records = json.load(f)

# -----------------------------
# CONFIG
# -----------------------------
UNIPROT_IDS = {
    "BRCA1": "P38398",
    "BRCA2": "P51587",
    "TP53":  "P04637",
    "CFTR":  "P13569",
    "MLH1":  "P40692",
    "MSH2":  "P43246",
    "PTEN":  "P60484",
    "APC":   "P25054",
    "VHL":   "P40337",
    "RB1":   "P06400",
    "ATM":   "Q13315",
    "LDLR":  "P01130",
    "APOE":  "P02649",
}

GENE_DOMAINS = {
    "BRCA1": ("BRCT domain", True),
    "BRCA2": ("OB fold domain", True),
    "TP53":  ("DNA-binding domain", True),
    "CFTR":  ("NBD1 domain", True),
    "MLH1":  ("ATPase domain", True),
    "MSH2":  ("Clamp domain", True),
    "PTEN":  ("Phosphatase domain", True),
    "APC":   ("Armadillo repeat domain", True),
    "VHL":   ("Beta domain", True),
    "RB1":   ("Pocket domain A", False),
    "ATM":   ("FAT domain", True),
    "LDLR":  ("Cysteine-rich repeat", True),
    "APOE":  ("Receptor-binding domain", False),
}

# -----------------------------
# FETCH ALL SEQUENCES (CACHED)
# -----------------------------
def fetch_all_sequences():
    print("🧬 Fetching UniProt sequences (once per gene)...")
    sequences = {}

    for gene, uniprot_id in UNIPROT_IDS.items():
        url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"

        try:
            r = requests.get(url, timeout=10)
            lines = r.text.strip().split("\n")
            seq = "".join(lines[1:])  # remove FASTA header
            sequences[gene] = seq
            print(f"   ✅ {gene} ({len(seq)} aa)")

        except Exception as e:
            print(f"   ❌ Failed {gene} — {e}")
            sequences[gene] = None

    return sequences


def get_sequence_context(sequence, position):
    if not sequence:
        return "XXXXXXXXXX"

    pos = position - 1  # 0-index
    start = max(0, pos - 5)
    end = min(len(sequence), pos + 5)

    return sequence[start:end]


# -----------------------------
# TIER LOGIC (FIXED + BALANCED)
# -----------------------------
def assign_tier(record):
    phylop = record["phylop_score"] or 0
    ddg = record["ddg_estimate"] or 0
    label = record["clinvar_label"]

    # Define signal strengths
    strong_conservation = phylop < -3
    moderate_conservation = phylop < -1.5

    strong_ddg = ddg < -2
    moderate_ddg = ddg < -1

    # -----------------------------
    # TIER 1: Strong agreement (high confidence)
    # -----------------------------
    if strong_conservation and strong_ddg and label == "Pathogenic":
        return 1, "combined"

    if phylop > -0.5 and ddg > -0.5 and label == "Benign":
        return 1, "combined"

    # -----------------------------
    # TIER 2: Moderate OR conflicting signals
    # -----------------------------
    # One strong signal
    if strong_conservation or strong_ddg:
        return 2, "combined"

    # Both moderate signals
    if moderate_conservation and moderate_ddg:
        return 2, "combined"

    # Conflict cases (important for learning!)
    if strong_conservation and label == "Benign":
        return 2, "conflict"

    if strong_ddg and label == "Benign":
        return 2, "conflict"

    # -----------------------------
    # TIER 3: Weak / ambiguous
    # -----------------------------
    return 3, "combined"

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("🚀 Finalizing dataset...")

    sequences = fetch_all_sequences()

    final = []
    tier_counts = {1: 0, 2: 0, 3: 0}
    tier_limits = {1: 35, 2: 40, 3: 25}

    for record in records:
        tier, factor = assign_tier(record)

        if tier_counts[tier] >= tier_limits[tier]:
            continue

        gene = record["gene"]
        position = record["position"]

        domain, critical = GENE_DOMAINS.get(gene, ("Unknown domain", False))

        sequence = sequences.get(gene)
        seq_context = get_sequence_context(sequence, position)

        record["domain"] = domain
        record["domain_critical"] = critical
        record["task_tier"] = tier
        record["deciding_factor"] = factor
        record["sequence_context"] = seq_context

        final.append(record)
        tier_counts[tier] += 1

        if len(final) % 20 == 0:
            print(f"📈 Selected {len(final)} records...")

        if sum(tier_counts.values()) >= 100:
            break

    print("\n" + "=" * 50)
    print(f"✅ Final counts")
    print(f"Tier 1: {tier_counts[1]}")
    print(f"Tier 2: {tier_counts[2]}")
    print(f"Tier 3: {tier_counts[3]}")
    print(f"Total: {len(final)}")

    # -----------------------------
    # SAVE
    # -----------------------------
    with open("mutations.json", "w") as f:
        json.dump(final, f, indent=2)

    print("💾 Saved to mutations.json")


# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    main()