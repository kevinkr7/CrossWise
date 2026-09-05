# Synthetic South-India Maize Genotype–Phenotype Dataset

**This dataset is entirely SIMULATED.** It was generated using standard
quantitative-genetics rules (biallelic SNPs, additive polygenic architecture,
a small number of larger-effect QTL, genotype-by-environment interaction,
realistic heritability) so that its statistical behaviour resembles real
genomic-selection data. **It is not derived from real genotyping or field
trial records.** Use it to build and debug your AI/ML pipeline; do not present
it as empirical/observed data in results claiming real-world findings — clearly
label it as simulated in your methodology if you use it for a proof-of-concept.

## Files
| File | Description |
|---|---|
| `synthetic_maize_dataset.csv` | Main dataset: 1000 lines × 6 environments = 6000 rows, 300 SNP columns + trait columns |
| `snp_panel_key.csv` | Per-SNP metadata: major/minor allele, minor allele frequency (MAF), which trait(s) each SNP is a large-effect QTL for |
| `environment_summary.csv` | The 6 environment definitions with derived stress indices |

## Structure of `synthetic_maize_dataset.csv`
`Line, Location, State, Season, Soil_Type, Irrigation, Rainfall_mm, Temp_C, Humidity_pct, SNP_001...SNP_300, Yield_t_ha, Disease_Resistance, Drought_Tolerance`

- **Line**: 1000 unique inbred/hybrid IDs (L0001–L1000). Genotype is identical for a line across all 6 environments (as in a real multi-environment trial).
- **SNP_001…SNP_300**: biallelic genotype calls as letter pairs (e.g. `AA`, `AG`, `GG`); `NN` = missing call (~2% missing rate, mimicking real SNP array dropout).
- **Yield_t_ha**: continuous grain yield (t/ha).
- **Disease_Resistance**: categorical — Resistant / Moderate / Susceptible (simulated Turcicum Leaf Blight response, a real and common South Indian maize disease).
- **Drought_Tolerance**: categorical — High / Medium / Low.

## The 6 simulated environments (real South Indian maize belts)
Coimbatore (TN), Mandya (Karnataka, irrigated), Davangere (Karnataka, Rabi/irrigated),
Anantapur (Andhra Pradesh, rainfed/drought-prone), Warangal (Telangana, Rabi/irrigated),
Bengaluru Rural (Karnataka, rainfed) — each with realistic season, soil type, irrigation
status, rainfall, temperature and humidity used to derive a drought-stress index and a
disease-pressure index per environment.

## Genetic architecture used
- **Yield**: polygenic background (all 300 SNPs, small effects) + 8 larger-effect QTL.
- **Drought tolerance score**: polygenic background + 6 larger-effect QTL, 2 of which
  overlap with yield QTL (pleiotropy, biologically realistic since drought stress
  directly affects yield).
- **Disease resistance score**: polygenic background + 3 major resistance-gene-like QTL
  (mimicking known *Ht*-type qualitative resistance loci in maize).
- **G×E**: yield is penalised in higher drought-stress environments in proportion to a
  line's (inverse) drought genetic score; disease phenotype is penalised in
  higher-humidity/disease-pressure environments.
- **Heritability** tuned to literature-typical values (~0.4 for yield, ~0.5–0.55 for the
  categorical traits' underlying scores) via the genetic-to-residual variance ratio.

## Regenerating / modifying
The full generation code is in `generate_dataset.py` (seeded, `np.random.default_rng(42)`,
fully reproducible). You can change `N_LINES`, `N_SNPS`, add more environments, or adjust
QTL effect sizes/heritability directly in the script.
