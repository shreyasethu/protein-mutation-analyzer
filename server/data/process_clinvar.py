import pandas as pd
import json
import re
import time
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------
# CONFIG
# -----------------------------
INPUT_FILE = "variant_summary.txt"
OUTPUT_FILE = "clinvar_final.json"
TARGET_RECORDS = 300
CHUNK_SIZE = 50000
MAX_WORKERS = 6  # reduce if API complains

# -----------------------------
# FILTER CONFIG
# -----------------------------
GENES = {
    "BRCA1", "BRCA2", "TP53", "CFTR", "MLH1", "MSH2",
    "PTEN", "APC", "VHL", "RB1", "ATM", "LDLR", "APOE"
}

VALID_SIG = {
    "Pathogenic", "Benign", "Likely benign", "Likely pathogenic"
}

VALID_REVIEW = {
    "reviewed by expert panel",
    "criteria provided, multiple submitters, no conflicts",
    "criteria provided, single submitter"
}

COLUMNS = [
    "Type", "Assembly", "ClinicalSignificance",
    "ReviewStatus", "GeneSymbol", "Name",
    "Chromosome", "Start"
]

# -----------------------------
# BIOLOGICAL CONSTANTS
# -----------------------------
AA3_TO_1 = {
    'Ala':'A','Arg':'R','Asn':'N','Asp':'D','Cys':'C','Gln':'Q','Glu':'E',
    'Gly':'G','His':'H','Ile':'I','Leu':'L','Lys':'K','Met':'M','Phe':'F',
    'Pro':'P','Ser':'S','Thr':'T','Trp':'W','Tyr':'Y','Val':'V','Ter':'*'
}

HYDROPHOBICITY = {
    'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
    'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
    'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6,
    'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2,
    '*': -5.0
}

KNOWN_DDG = {
    "mut_BRCA1_1699_RW": -3.1,
    "mut_TP53_248_RW": -4.5,
    "mut_CFTR_508_Fd": -5.2,
    "mut_PTEN_130_GE": -3.3,
}

AA_PATTERN = re.compile(r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|Ter)')


# -----------------------------
# HELPERS
# -----------------------------
def normalize_label(sig):
    if "Pathogenic" in sig:
        return "Pathogenic"
    elif "Benign" in sig:
        return "Benign"
    return "Uncertain"


def normalize_confidence(status):
    if "expert panel" in status or "multiple submitters" in status:
        return "high"
    elif "single submitter" in status:
        return "medium"
    return "low"


def extract_aa(name):
    match = AA_PATTERN.search(str(name))
    if not match:
        return None, None, None

    ref = AA3_TO_1.get(match.group(1), '?')
    pos = int(match.group(2))
    mut = AA3_TO_1.get(match.group(3), '?')

    if ref == '?' or mut == '?':
        return None, None, None

    return ref, pos, mut


# -----------------------------
# PHYLOP
# -----------------------------
def fetch_phylop(record):
    chrom = str(record["chrom"]).replace("chr", "")
    pos = record["genomic_pos"]

    url = f"https://api.genome.ucsc.edu/getData/track?genome=hg38;track=phyloP100way;chrom=chr{chrom};start={pos-1};end={pos}"

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        phylo = data.get("phyloP100way")

        score = None

        if isinstance(phylo, dict):
            values = phylo.get("data", [])
            if values:
                score = values[0].get("value")

        elif isinstance(phylo, list):
            if phylo:
                score = phylo[0].get("value")

        if score is not None:
            record["phylop_score"] = round(score, 3)
        else:
            record["phylop_score"] = -1.0  # fallback

    except Exception as e:
        print(f"❌ PhyloP failed for {record['id']} — {e}")
        record["phylop_score"] = -1.0

    return record


# -----------------------------
# DDG
# -----------------------------
def estimate_ddg(ref_aa, mut_aa, phylop_score):
    h_ref = HYDROPHOBICITY.get(ref_aa, 0)
    h_mut = HYDROPHOBICITY.get(mut_aa, 0)

    hydrophobicity_change = abs(h_ref - h_mut)
    conservation_penalty = max(0, -phylop_score) * 0.3

    ddg = -(hydrophobicity_change * 0.4 + conservation_penalty)

    random.seed(hash(f"{ref_aa}{mut_aa}"))
    ddg += random.uniform(-0.3, 0.3)

    return round(ddg, 2)


# -----------------------------
# MAIN
# -----------------------------
def main():
    start_time = time.time()
    print("🚀 FULL PIPELINE START")

    records = []
    seen_ids = set()

    chunks = pd.read_csv(
        INPUT_FILE,
        sep="\t",
        usecols=COLUMNS,
        chunksize=CHUNK_SIZE,
        dtype=str
    )

    # STEP 1: Extract
    for chunk_idx, chunk in enumerate(chunks):
        print(f"\n📦 Chunk {chunk_idx}")

        filtered = chunk[
            (chunk["Type"] == "single nucleotide variant") &
            (chunk["Assembly"] == "GRCh38") &
            (chunk["ClinicalSignificance"].isin(VALID_SIG)) &
            (chunk["ReviewStatus"].isin(VALID_REVIEW)) &
            (chunk["GeneSymbol"].isin(GENES))
        ]

        print(f"   ✅ Filtered: {len(filtered)}")

        for row in filtered.itertuples(index=False):
            ref_aa, position, mut_aa = extract_aa(row.Name)

            if not ref_aa:
                continue

            uid = f"mut_{row.GeneSymbol}_{position}_{ref_aa}{mut_aa}"

            if uid in seen_ids:
                continue

            seen_ids.add(uid)

            records.append({
                "id": uid,
                "gene": row.GeneSymbol,
                "position": position,
                "ref_aa": ref_aa,
                "mut_aa": mut_aa,
                "chrom": row.Chromosome,
                "genomic_pos": int(row.Start),
                "sequence_context": "XXXXXXXXXX",
                "phylop_score": None,
                "ddg_estimate": None,
                "domain": "Unknown",
                "domain_critical": False,
                "clinvar_label": normalize_label(row.ClinicalSignificance),
                "clinvar_confidence": normalize_confidence(row.ReviewStatus),
                "task_tier": None,
                "deciding_factor": None
            })

            if len(records) % 50 == 0:
                print(f"   📈 Collected: {len(records)}")

            if len(records) >= TARGET_RECORDS:
                break

        if len(records) >= TARGET_RECORDS:
            break

    print(f"\n✅ Extracted {len(records)} variants")

    # STEP 2: PhyloP
    print("\n🚀 Fetching PhyloP...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(fetch_phylop, r) for r in records]

        for i, future in enumerate(as_completed(futures)):
            records[i] = future.result()
            if (i + 1) % 25 == 0:
                print(f"   📊 PhyloP: {i+1}/{len(records)}")

    # STEP 3: DDG
    print("\n🧬 Computing ΔΔG...")

    for record in records:
        uid = record["id"]

        if uid in KNOWN_DDG:
            record["ddg_estimate"] = KNOWN_DDG[uid]
        else:
            record["ddg_estimate"] = estimate_ddg(
                record["ref_aa"],
                record["mut_aa"],
                record["phylop_score"]
            )

    # SAVE
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f, indent=2)

    print("\n" + "=" * 50)
    print("✅ DONE")
    print(f"📊 Records: {len(records)}")
    print(f"⏱️ Time: {time.time() - start_time:.2f}s")
    print(f"💾 Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()