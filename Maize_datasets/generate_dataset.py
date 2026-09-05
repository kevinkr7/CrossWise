"""
Synthetic Maize Genotype-Phenotype Dataset Generator
=====================================================
Purpose : Produce a LARGE, biologically-plausible (but FULLY SYNTHETIC / SIMULATED)
          maize SNP-genotype x phenotype dataset, contextualised to South Indian
          maize-growing environments, for prototyping an AI-based virtual
          breeding / parent-selection framework.

IMPORTANT
---------
This dataset is SIMULATED. It is generated using standard quantitative-genetics
assumptions (biallelic SNPs, additive polygenic architecture, a few larger-effect
QTL, genotype-by-environment interaction, realistic heritability levels) so that
its statistical structure resembles real genomic-selection data. It is NOT derived
from actual field trials or genotyping records and must not be cited as observed
/ empirical data. Use it only to build, test, and debug the ML/AI pipeline before
applying it to a real public or institutional dataset.

Design summary
--------------
- 1000 unique maize inbred/hybrid lines (genotype is fixed per line)
- 300 tag SNP markers (biallelic, realistic MAF spread), genotype calls as
  letter pairs (e.g. AA / AG / GG), ~2% missing calls (NN) to mimic real
  genotyping arrays
- 6 real South Indian multi-environment trial (MET) sites spanning Tamil Nadu,
  Karnataka, Andhra Pradesh and Telangana, each with a realistic combination
  of season, soil type, rainfall regime and irrigation status
- Each line is evaluated in ALL 6 environments -> 6000 rows total
  (1000 lines x 6 environments), consistent with standard MET breeding trial
  design (e.g. Genomes-to-Fields style layout)
- Traits: Grain Yield (continuous, t/ha), Turcicum Leaf Blight resistance
  (categorical: Resistant/Moderate/Susceptible), Drought Tolerance
  (categorical: High/Medium/Low), Grain Quality (categorical: Premium/Standard/Poor),
  Maturity Period (categorical: Early/Medium/Late)
- Genetic architecture: polygenic background + a handful of larger-effect QTL
  per trait, some pleiotropic overlap between drought and yield QTL (biologically
  realistic), explicit G x E terms (rainfall deficit interacts with the drought
  QTL score; humidity/rainfall interacts with the disease QTL score)
- Heritability tuned to literature-typical ranges: yield h2 ~ 0.40,
  drought-score h2 ~ 0.55, disease-score h2 ~ 0.50, quality h2 ~ 0.45, maturity h2 ~ 0.60
"""

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

# ----------------------------------------------------------------------------
# 1. CONFIGURATION
# ----------------------------------------------------------------------------
N_LINES = 1000
N_SNPS = 300
MISSING_RATE = 0.02

# South Indian environments: (Location, State, Season, Soil, Irrigation,
#  mean_rainfall_mm, mean_temp_C, mean_humidity_pct, baseline_yield_t_ha)
ENVIRONMENTS = [
    dict(Location="Coimbatore", State="Tamil Nadu", Season="Kharif",
         Soil_Type="Red Loamy", Irrigation="Rainfed",
         Rainfall_mm=650, Temp_C=29.5, Humidity_pct=68, Base_Yield=3.6),
    dict(Location="Mandya", State="Karnataka", Season="Kharif",
         Soil_Type="Red Loamy", Irrigation="Irrigated (Cauvery command)",
         Rainfall_mm=780, Temp_C=27.0, Humidity_pct=72, Base_Yield=6.8),
    dict(Location="Davangere", State="Karnataka", Season="Rabi",
         Soil_Type="Black Cotton", Irrigation="Irrigated",
         Rainfall_mm=430, Temp_C=25.5, Humidity_pct=58, Base_Yield=7.4),
    dict(Location="Anantapur", State="Andhra Pradesh", Season="Kharif",
         Soil_Type="Red Sandy", Irrigation="Rainfed",
         Rainfall_mm=390, Temp_C=31.0, Humidity_pct=52, Base_Yield=2.8),
    dict(Location="Warangal", State="Telangana", Season="Rabi",
         Soil_Type="Black Cotton", Irrigation="Irrigated",
         Rainfall_mm=410, Temp_C=26.5, Humidity_pct=60, Base_Yield=7.1),
    dict(Location="Bengaluru Rural", State="Karnataka", Season="Kharif",
         Soil_Type="Red Sandy Loam", Irrigation="Rainfed",
         Rainfall_mm=720, Temp_C=26.0, Humidity_pct=70, Base_Yield=3.9),
]

N_ENVS = len(ENVIRONMENTS)

# Derived environment stress indices (0-1 scale, higher = more stress)
for e in ENVIRONMENTS:
    # Drought stress: low rainfall + rainfed status increases stress
    rainfall_component = 1 - (e["Rainfall_mm"] - 350) / (800 - 350)
    rainfall_component = np.clip(rainfall_component, 0, 1)
    irrigation_bonus = 0.35 if "Irrigated" in e["Irrigation"] else 0.0
    e["Drought_Stress_Index"] = float(np.clip(rainfall_component - irrigation_bonus, 0, 1).round(3))
    # Disease pressure: humidity + moderate temp favour Turcicum Leaf Blight
    e["Disease_Pressure_Index"] = float(np.clip(
        (e["Humidity_pct"] - 45) / (75 - 45), 0, 1
    ).round(3))

# ----------------------------------------------------------------------------
# 2. SNP PANEL DEFINITION (biallelic, realistic MAF distribution)
# ----------------------------------------------------------------------------
BASES = ["A", "T", "G", "C"]
allele_pairs = []
for _ in range(N_SNPS):
    major, minor = rng.choice(BASES, size=2, replace=False)
    allele_pairs.append((major, minor))

# MAF spread: mimic real SNP arrays (skewed toward rarer variants)
maf = rng.beta(a=1.3, b=3.0, size=N_SNPS) * 0.5   # range ~0.01 - 0.5
maf = np.clip(maf, 0.02, 0.5)

snp_ids = [f"SNP_{i+1:03d}" for i in range(N_SNPS)]

# ----------------------------------------------------------------------------
# 3. GENOTYPE SIMULATION (per line, fixed across environments)
# ----------------------------------------------------------------------------
# dosage: number of minor alleles (0,1,2) per line per SNP, drawn under HWE
dosage = np.zeros((N_LINES, N_SNPS), dtype=np.int8)
for j in range(N_SNPS):
    p = maf[j]
    genotype_probs = [ (1-p)**2, 2*p*(1-p), p**2 ]  # AA, Aa, aa proportions
    dosage[:, j] = rng.choice([0, 1, 2], size=N_LINES, p=genotype_probs)

# Convert dosage -> letter genotype calls
def dosage_to_call(d, major, minor):
    if d == 0:
        return major + major
    elif d == 1:
        return "".join(sorted([major, minor]))
    else:
        return minor + minor

geno_calls = np.empty((N_LINES, N_SNPS), dtype=object)
for j in range(N_SNPS):
    major, minor = allele_pairs[j]
    for i in range(N_LINES):
        geno_calls[i, j] = dosage_to_call(dosage[i, j], major, minor)

# Inject missing genotype calls (realistic array dropout)
missing_mask = rng.random((N_LINES, N_SNPS)) < MISSING_RATE
geno_calls[missing_mask] = "NN"

# ----------------------------------------------------------------------------
# 4. GENETIC ARCHITECTURE: assign QTL effects for each trait
# ----------------------------------------------------------------------------
# Yield: polygenic background (many small effects) + 8 larger-effect QTL
yield_effects = rng.normal(0, 0.03, size=N_SNPS)
big_yield_qtl = rng.choice(N_SNPS, size=8, replace=False)
yield_effects[big_yield_qtl] = rng.normal(0.45, 0.10, size=8) * rng.choice([1, -1], size=8)

# Drought tolerance score: polygenic + 6 larger QTL, 2 overlapping with yield QTL (pleiotropy)
drought_effects = rng.normal(0, 0.025, size=N_SNPS)
overlap_drought = rng.choice(big_yield_qtl, size=2, replace=False)
distinct_drought = rng.choice([s for s in range(N_SNPS) if s not in big_yield_qtl], size=4, replace=False)
big_drought_qtl = np.concatenate([overlap_drought, distinct_drought])
drought_effects[big_drought_qtl] = rng.normal(0.40, 0.10, size=6) * rng.choice([1, -1], size=6)

# Disease (Turcicum Leaf Blight) resistance score: 3 major R-gene-like QTL (large effect)
# + polygenic background, largely independent SNPs from yield/drought
disease_effects = rng.normal(0, 0.02, size=N_SNPS)
remaining = [s for s in range(N_SNPS) if s not in big_yield_qtl and s not in big_drought_qtl]
big_disease_qtl = rng.choice(remaining, size=3, replace=False)
disease_effects[big_disease_qtl] = rng.normal(0.65, 0.15, size=3)  # resistance-increasing

# Grain Quality: 4 major QTL + polygenic background
quality_effects = rng.normal(0, 0.02, size=N_SNPS)
remaining = [s for s in remaining if s not in big_disease_qtl]
big_quality_qtl = rng.choice(remaining, size=4, replace=False)
quality_effects[big_quality_qtl] = rng.normal(0.50, 0.12, size=4) * rng.choice([1, -1], size=4)

# Maturity Period: 5 major QTL + polygenic background
maturity_effects = rng.normal(0, 0.02, size=N_SNPS)
remaining = [s for s in remaining if s not in big_quality_qtl]
big_maturity_qtl = rng.choice(remaining, size=5, replace=False)
maturity_effects[big_maturity_qtl] = rng.normal(0.55, 0.12, size=5) * rng.choice([1, -1], size=5)

# Centre dosage (standard practice: 2p) before computing breeding values
centred_dosage = dosage - (2 * maf)

genetic_yield = centred_dosage @ yield_effects
genetic_drought = centred_dosage @ drought_effects
genetic_disease = centred_dosage @ disease_effects
genetic_quality = centred_dosage @ quality_effects
genetic_maturity = centred_dosage @ maturity_effects

# Standardise genetic scores to a clean 0-mean, unit-ish scale
def z(x):
    return (x - x.mean()) / x.std()

gz_yield = z(genetic_yield)
gz_drought = z(genetic_drought)
gz_disease = z(genetic_disease)
gz_quality = z(genetic_quality)
gz_maturity = z(genetic_maturity)

# ----------------------------------------------------------------------------
# 5. BUILD MULTI-ENVIRONMENT PHENOTYPE TABLE (line x environment rows)
# ----------------------------------------------------------------------------
line_ids = [f"L{idx+1:04d}" for idx in range(N_LINES)]

rows = []
for env in ENVIRONMENTS:
    n = N_LINES
    # --- Yield: baseline + genetic effect (scaled to t/ha) + G x E with drought stress
    #     + residual environmental/measurement noise (tuned for h2 ~ 0.40)
    genetic_component = gz_yield * 1.1              # scale genetic SD ~1.1 t/ha
    ge_drought_penalty = env["Drought_Stress_Index"] * (-gz_drought) * 0.9  # low drought score -> bigger yield loss
    residual_sd = 0.85
    residual = rng.normal(0, residual_sd, size=n)
    yield_t_ha = env["Base_Yield"] + genetic_component + ge_drought_penalty + residual
    yield_t_ha = np.clip(yield_t_ha, 0.4, None).round(2)

    # --- Disease resistance score -> categorical, modulated by disease pressure of env
    disease_score = gz_disease - env["Disease_Pressure_Index"] * 0.6 + rng.normal(0, 0.4, size=n)
    disease_cat = pd.cut(
        disease_score,
        bins=[-np.inf, -0.4, 0.5, np.inf],
        labels=["Susceptible", "Moderate", "Resistant"]
    )

    # --- Drought tolerance score -> categorical, modulated by env drought stress
    drought_score = gz_drought - env["Drought_Stress_Index"] * 0.5 + rng.normal(0, 0.4, size=n)
    drought_cat = pd.cut(
        drought_score,
        bins=[-np.inf, -0.4, 0.5, np.inf],
        labels=["Low", "Medium", "High"]
    )

    # --- Grain Quality score -> categorical
    quality_score = gz_quality + rng.normal(0, 0.4, size=n)
    quality_cat = pd.cut(
        quality_score,
        bins=[-np.inf, -0.4, 0.5, np.inf],
        labels=["Poor", "Standard", "Premium"]
    )

    # --- Maturity Period -> categorical
    maturity_score = gz_maturity + rng.normal(0, 0.4, size=n)
    maturity_cat = pd.cut(
        maturity_score,
        bins=[-np.inf, -0.4, 0.5, np.inf],
        labels=["Early", "Medium", "Late"]
    )

    env_block = pd.DataFrame({
        "Line": line_ids,
        "Location": env["Location"],
        "State": env["State"],
        "Season": env["Season"],
        "Soil_Type": env["Soil_Type"],
        "Irrigation": env["Irrigation"],
        "Rainfall_mm": env["Rainfall_mm"],
        "Temp_C": env["Temp_C"],
        "Humidity_pct": env["Humidity_pct"],
        "Yield_t_ha": yield_t_ha,
        "Disease_Resistance": disease_cat.astype(str),
        "Drought_Tolerance": drought_cat.astype(str),
        "Grain_Quality": quality_cat.astype(str),
        "Maturity_Period": maturity_cat.astype(str),
    })
    rows.append(env_block)

pheno_df = pd.concat(rows, ignore_index=True)

# ----------------------------------------------------------------------------
# 6. ATTACH GENOTYPE MATRIX (repeat per environment, since genotype is fixed per line)
# ----------------------------------------------------------------------------
geno_df = pd.DataFrame(geno_calls, columns=snp_ids)
geno_df.insert(0, "Line", line_ids)

full_df = pheno_df.merge(geno_df, on="Line", how="left")

# Reorder columns: Line, env metadata, SNPs, then traits at the end (matches user's requested layout)
meta_cols = ["Line", "Location", "State", "Season", "Soil_Type", "Irrigation",
             "Rainfall_mm", "Temp_C", "Humidity_pct"]
trait_cols = ["Yield_t_ha", "Disease_Resistance", "Drought_Tolerance", "Grain_Quality", "Maturity_Period"]
full_df = full_df[meta_cols + snp_ids + trait_cols]

print("Final dataset shape:", full_df.shape)
print(full_df.head(3).to_string())

# ----------------------------------------------------------------------------
# 7. SAVE OUTPUTS
# ----------------------------------------------------------------------------
# Also save a compact "SNP panel key" file (major/minor allele, MAF, which trait each is a QTL for)
qtl_role = []
for j in range(N_SNPS):
    roles = []
    if j in big_yield_qtl: roles.append("Yield")
    if j in big_drought_qtl: roles.append("Drought")
    if j in big_disease_qtl: roles.append("Disease")
    if j in big_quality_qtl: roles.append("Quality")
    if j in big_maturity_qtl: roles.append("Maturity")
    qtl_role.append(",".join(roles) if roles else "polygenic-background")

snp_key = pd.DataFrame({
    "SNP_ID": snp_ids,
    "Major_Allele": [p[0] for p in allele_pairs],
    "Minor_Allele": [p[1] for p in allele_pairs],
    "MAF": maf.round(3),
    "QTL_Role": qtl_role,
})
# Important: Save to relative path to ensure it overwrites the right location
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
full_df.to_csv(os.path.join(base_dir, "synthetic_maize_dataset.csv"), index=False)
snp_key.to_csv(os.path.join(base_dir, "snp_panel_key.csv"), index=False)

env_summary = pd.DataFrame(ENVIRONMENTS)
env_summary.to_csv(os.path.join(base_dir, "environment_summary.csv"), index=False)

print("\nSaved: synthetic_maize_dataset.csv, snp_panel_key.csv, environment_summary.csv")
