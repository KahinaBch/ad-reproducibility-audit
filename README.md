# AD Reproducibility Audit

**Sub-repository 3 of 4** — GBM6330E Final Project | KahinaBch  
🌐 [Main Website](https://kahinabch.github.io/ad-diversity-website)

---

## Overview

A reproducible pipeline to audit open-science practices in *Alzheimer's & Dementia* (Wiley).

Adapted from: [KahinaBch/mrm-reproducible-research-2025](https://github.com/KahinaBch/mrm-reproducible-research-2025)  
Original methodology: Boudreau et al. "On the open-source landscape of Magnetic Resonance in Medicine"

Detailed workflow protocol: [`docs/REPRODUCIBILITY_PROTOCOL.md`](docs/REPRODUCIBILITY_PROTOCOL.md)

**Key differences from the MRM pipeline:**
- Journal: *Alzheimer's & Dementia* (ISSN: 1552-5260)
- ✅ Code-availability / reproducibility keyword scan (Step 3) + repository-link extraction
- ✅ **Sex-specific keyword detection added** (novel contribution — Step 4)
- ✅ Optional author metadata + name-based gender inference (Step 5b; exploratory)
- ✅ Geographic origin analysis retained

---

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | `src/get_ad_dois_by_year.py` | Retrieve DOI list from Crossref |
| 2 | `src/sort_ad_pdfs_by_acceptance_and_build_workbook.py` | Sort PDFs by acceptance month, build Excel workbook |
| 3 | `src/scan_keywords_update_workbook.py` | Scan PDFs for code-availability / reproducibility keywords (+ repo link) |
| 4 | `src/scan_sex_keywords_update_workbook.py` | **NOVEL**: detect sex-specific analysis keywords |
| 4b | `src/scan_dataset_mentions_update_workbook.py` | Detect mentions of known AD datasets (keyword search using dataset catalogue names) |
| 5 | Manual curation | Validate keyword matches (False Positive?, Shared code?, Shared data?) |
| 5b | `src/add_author_gender_from_doi.py` | Add first/last author + inferred gender (optional) |
| 6 | `src/add_affiliation_country_from_pdfs.py` | Extract first-author country from PDFs |
| 7 | `src/run_ad_analysis.py` | Statistical analysis |
| 8 | `src/plot_ad_results.py` | Publication-ready figures |

### Notes on logs and augmentation

The scan scripts write CSV logs that can be merged back into the workbook-derived dataframe during Steps 7–8 to prevent undercounting when workbook cells are blank.

All figures produced by Step 8 are percent/proportion based (not raw counts), and each output file contains a single plot (no multi-panel figures).

- Step 3 writes `workbooks/{year}/keyword_scan_log.csv` (includes `repo_link` and `matched_row`)
- Step 4 writes `workbooks/{year}/sex_keyword_scan_log.csv`
- Step 4b writes `workbooks/{year}/dataset_scan_log.csv`
- Step 5b writes `workbooks/{year}/author_gender_log.csv`

---

## Results (2025 run)

This repository includes a complete end-to-end run for 2025 under `data/raw/pdfs/2025/`, `workbooks/2025/`, and `plots/2025/`.

Headline results by step:

- **Step 1 (DOIs):** Crossref retrieval produced **6,931 DOIs** → `data/raw/ad_2025_dois.csv`.
- **Step 2 (PDF sort + workbook):** **913 PDFs** were organized into month folders under `data/raw/pdfs/2025/{Month}/` and compiled into `workbooks/2025/AD-ReproducibleResearch_2025.xlsx` (**913 workbook rows**).
- **Step 3 (Open-science keyword scan):** `workbooks/2025/keyword_scan_log.csv` created; Step 7 summary shows **810/913 papers (88.7%)** with an open-science keyword match and **86/913 papers (9.4%)** with an extracted repository link (including **80 GitHub links**).
- **Step 4 (Sex-specific keywords):** `workbooks/2025/sex_keyword_scan_log.csv` created; Step 7 summary shows **233/913 papers (25.5%)** with sex-specific keywords.
  - Sex-aware level breakdown in the workbook: **37 “sex-aware main focus”**, **196 “sex-aware consideration”**, remainder “none/unknown”.
- **Step 4b (Dataset mentions):** `workbooks/2025/dataset_scan_log.csv` created; **482/913 PDFs (52.8%)** mentioned ≥1 known dataset.
  - Most frequently detected datasets (counts): **ADNI (175)**, **NACC (136)**, **UK Biobank (92)**, **MAPT (72)**, **A4 Study (41)**.
- **Step 5 (Manual curation):** Workbook columns `False Positive?`, `Shared code?`, `Shared data?` were manually reviewed/curated to validate scan outputs.
- **Step 5b (Author metadata + gender, optional):** `workbooks/2025/author_gender_log.csv` created for first/last authors; used by Step 8 to generate gender distribution figures.
- **Step 6 (Country extraction):** `workbooks/2025/pdf_affiliation_country_log.csv` created; Step 7 summary shows **905/913 papers (99.1%)** with an identified first-author country.
- **Step 7 (Analysis):** `workbooks/2025/AD_2025_analysis.xlsx` generated. Key results:
  - **Code sharing:** 809/913 (88.6%)
  - **Data sharing:** 27/913 (3.0%)
  - **Code OR data sharing:** 810/913 (88.7%)
  - Hosting platforms detected in links (counts): **GitHub 80**, **OSF 4**, **Zenodo 2**
- **Step 8 (Figures):** Figures written to `plots/2025/fig*.png` (see Step 8 section below for per-figure descriptions).

Notes:
- Step 7/8 “sharing” metrics are augmented using scan logs to avoid undercounting when workbook fields are blank.
- Step 4b results are computed from the PDF scan log (one row per scanned PDF).

---

## Prerequisites

You will need:
- Python 3.11+
- PDFs of *Alzheimer's & Dementia* articles for the target year (manual download — copyright restrictions prevent inclusion)

## Installation

```bash
conda env create -f environment.yml
conda activate ad-reproducibility
```

Or with pip:
```bash
pip install -r requirements.txt
```

---

## Running the Pipeline

If you already have a curated workbook and the scan logs (e.g., `workbooks/2025/`), you can run only Steps 7–8.

### Step 1 — Retrieve DOI list
```bash
python src/get_ad_dois_by_year.py --year 2023 --out data/raw/ad_2023_dois.csv
```

### Step 2 — Sort PDFs and build workbook
```bash
python src/sort_ad_pdfs_by_acceptance_and_build_workbook.py \
  --year 2023 \
  --pdf-folder /path/to/your/2023_pdfs
```
Output: `workbooks/2023/AD-ReproducibleResearch_2023.xlsx`

### Step 3 — Scan code-availability / reproducibility keywords
```bash
python src/scan_keywords_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

Outputs:
- Updates workbook columns including `Keywords Matched` and `Code repository link`
- Writes `workbooks/2023/keyword_scan_log.csv` with `repo_link` and `matched_row`

### Step 4 — Scan sex-specific keywords (NOVEL STEP)
```bash
python src/scan_sex_keywords_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

Outputs:
- Updates workbook columns including `Sex-specific keywords?`, `Sex keywords matched`, `Sex-aware level`
- Writes `workbooks/2023/sex_keyword_scan_log.csv`

### Step 4b — Scan dataset mentions (keyword search)
This step uses dataset names from the dataset catalogue JSON (`ad-dataset-catalogue/data/neuroimaging_genetics.json`, field: `name`) and scans PDF text for those names.

```bash
python src/scan_dataset_mentions_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

Optional (explicit JSON path):
```bash
python src/scan_dataset_mentions_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --dataset-json ../ad-dataset-catalogue/data/neuroimaging_genetics.json
```

Outputs:
- Updates workbook columns: `Dataset(s) mentioned?`, `Dataset names matched`
- Writes `workbooks/2023/dataset_scan_log.csv`

### Step 5 — Manual curation
Open the workbook and manually verify:
- `False Positive?` (Yes/blank)
- `Shared code?` (Yes/blank)
- `Shared data?` (Yes/blank)
- `Language(s)`

### Step 5b — Add first/last author + inferred gender (intermediate)
```bash
python src/add_author_gender_from_doi.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

### Step 6 — Extract countries
```bash
python src/add_affiliation_country_from_pdfs.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

### Step 7 — Statistical analysis
```bash
python src/run_ad_analysis.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --year 2023
```

Optional (recommended if `Link` / sharing fields are incomplete in the workbook):
```bash
python src/run_ad_analysis.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --year 2023 \
  --keyword-log-csv workbooks/2023/keyword_scan_log.csv
```

### Step 8 — Generate figures
```bash
python src/plot_ad_results.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --year 2023 \
  --out-dir plots/2023
```

Output location:
- If `--out-dir` is provided, all figures are written there.
- Otherwise, the default is `plots/{year}/`.

Optional inputs (defaults: looks for logs next to the workbook):
```bash
python src/plot_ad_results.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --year 2023 \
  --keyword-log-csv workbooks/2023/keyword_scan_log.csv \
  --sex-keyword-log-csv workbooks/2023/sex_keyword_scan_log.csv \
  --author-gender-log-csv workbooks/2023/author_gender_log.csv \
  --dataset-log-csv workbooks/2023/dataset_scan_log.csv \
  --dataset-json ../ad-dataset-catalogue/data/neuroimaging_genetics.json
```

Figures produced (all are percentages/proportions; one plot per file):
- `fig1_sharing_by_month.png`: Monthly % of papers sharing code and/or data (year timeline).
- `fig2_sex_keyword_analysis.png`: % of papers flagged as containing sex-specific keywords (overall).
- `fig3_country_distribution.png`: Distribution of first-author countries (share of papers by country).
- `fig4_hosting_platforms.png`: Breakdown of where shared resources are hosted (e.g., GitHub/OSF/Zenodo).
- `fig6_sex_aware_level_distribution.png`: Distribution of “sex-aware level” categories (share of papers per level).
- `fig7_top_sex_keywords.png`: Top matched sex-related keywords (share of papers mentioning each keyword).
- `fig8_country_sharing_rate.png`: % sharing code/data by country (conditional sharing rate per country).
- `fig9_github_link_rate.png`: % of papers with a GitHub link (overall).
- `fig10_first_author_gender_distribution.png`: First-author gender distribution (from `author_gender_log.csv`).
- `fig11_last_author_gender_distribution.png`: Last-author gender distribution (from `author_gender_log.csv`).
- `fig12_dataset_proportions_all_papers.png`: Dataset mentions as % of all papers (denominator = all valid papers).
- `fig13_dataset_proportions_dataset_found_papers.png`: Dataset mentions as % of dataset-mention papers only (denominator = papers with ≥1 dataset).

Dataset figure coloring:
- Bars are color-coded by dataset origin inferred from the dataset catalogue JSON (`origin` country list), grouped into region buckets (e.g., Americas/Europe/Asia/Multi-region).

---

## Data Organization

Recommended structure:

```
data/
  raw/
    ad_{year}_dois.csv                    ← DOI list from Crossref
workbooks/
  {year}/
    AD-ReproducibleResearch_{year}.xlsx   ← Curated workbook
    AD_{year}_analysis.xlsx               ← Statistical summary workbook
    keyword_scan_log.csv                  ← Step 3 log
    sex_keyword_scan_log.csv              ← Step 4 log
    dataset_scan_log.csv                  ← Step 4b log
    author_gender_log.csv                 ← Step 5b log (optional)
    pdf_affiliation_country_log.csv       ← Step 6 log
plots/
  {year}/
    fig1_sharing_by_month.png
    fig2_sex_keyword_analysis.png
    fig3_country_distribution.png
    fig4_hosting_platforms.png
    fig6_sex_aware_level_distribution.png
    fig7_top_sex_keywords.png
    fig8_country_sharing_rate.png
    fig9_github_link_rate.png
    fig10_first_author_gender_distribution.png
    fig11_last_author_gender_distribution.png
    fig12_dataset_proportions_all_papers.png
    fig13_dataset_proportions_dataset_found_papers.png
docs/
  REPRODUCIBILITY_PROTOCOL.md             ← End-to-end process and QC guidance
```

---

## ⚠️ Disclaimer

See [DISCLAIMER.md](DISCLAIMER.md) for a full statement of scope limitations.

**Key points:**
- Results are specific to one journal and one time window
- Keyword detection is a heuristic — manual validation (Step 5) is essential
- PDFs not included due to copyright
- The pipeline is reproducible and extendable to other journals/years

---

## Sex-Specific Keyword List

The following keywords are used in Step 4 to detect sex-stratified analyses:

Classification output in workbook:
- `Sex-aware level = sex-aware main focus` when a keyword appears in title.
- `Sex-aware level = sex-aware consideration` when a keyword appears in main text (not title).

Title-only broad terms: `sex`, `gender`, `woman`, `female`

**Core:** `sex-stratified`, `sex differences`, `gender-specific`

**Extended:** `sex-disaggregated`, `sex-based analysis`, `female-specific`, `male-specific`,
`sex as a biological variable`, `sex as a covariate`, `sex-conditioned`,
`menopause`, `hormonal influence`, `APOE sex interaction`, `sex-specific`,
`estrogen`, `testosterone`, `stratified by sex`, `subgroup analysis by sex`

---

## License

No license file is included in this sub-repository.
