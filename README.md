# AD Reproducibility Audit

**Sub-repository 3 of 4** — GBM6330E Final Project | KahinaBch  
🌐 [Main Website](https://kahinabch.github.io/ad-diversity-website)

---

## Overview

A reproducible pipeline to audit open-science practices in *Alzheimer's & Dementia* (Wiley).

Adapted from: [KahinaBch/mrm-reproducible-research-2025](https://github.com/KahinaBch/mrm-reproducible-research-2025)  
Original methodology: Boudreau et al. "On the open-source landscape of Magnetic Resonance in Medicine"

**Key differences from the MRM pipeline:**
- Journal: *Alzheimer's & Dementia* (ISSN: 1552-5260)
- ❌ Author gender analysis **removed** (not in scope)
- ✅ **Sex-specific keyword detection added** (novel contribution — Step 4)
- ✅ Geographic origin analysis retained

---

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | `src/get_ad_dois_by_year.py` | Retrieve DOI list from Crossref |
| 2 | `src/sort_ad_pdfs_by_acceptance_and_build_workbook.py` | Sort PDFs by acceptance month, build Excel workbook |
| 3 | `src/scan_keywords_update_workbook.py` | Scan PDFs for open-science keywords |
| 4 | `src/scan_sex_keywords_update_workbook.py` | **NOVEL**: detect sex-specific analysis keywords |
| 5 | Manual curation | Validate keyword matches (False Positive?, Shared code?, Shared data?) |
| 6 | `src/add_affiliation_country_from_pdfs.py` | Extract first-author country from PDFs |
| 7 | `src/run_ad_analysis.py` | Statistical analysis |
| 8 | `src/plot_ad_results.py` | Publication-ready figures |

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

### Step 1 — Retrieve DOI list
```bash
python src/get_ad_dois_by_year.py --year 2023 --out data/derived/ad_2023_dois.csv
```

### Step 2 — Sort PDFs and build workbook
```bash
python src/sort_ad_pdfs_by_acceptance_and_build_workbook.py \
  --year 2023 \
  --pdf-folder /path/to/your/2023_pdfs
```
Output: `workbooks/2023/AD-ReproducibleResearch_2023.xlsx`

### Step 3 — Scan open-science keywords
```bash
python src/scan_keywords_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

### Step 4 — Scan sex-specific keywords (NOVEL STEP)
```bash
python src/scan_sex_keywords_update_workbook.py \
  --year-folder /path/to/your/2023_pdfs \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx
```

### Step 5 — Manual curation
Open the workbook and manually verify:
- `False Positive?` (Yes/blank)
- `Shared code?` (Yes/blank)
- `Shared data?` (Yes/blank)
- `Language(s)`

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

### Step 8 — Generate figures
```bash
python src/plot_ad_results.py \
  --xlsx workbooks/2023/AD-ReproducibleResearch_2023.xlsx \
  --year 2023 \
  --out-dir figures/2023
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

**Core:** `sex-stratified`, `sex differences`, `gender-specific`

**Extended:** `sex-disaggregated`, `sex-based analysis`, `female-specific`, `male-specific`,
`sex as a biological variable`, `sex as a covariate`, `sex-conditioned`,
`menopause`, `hormonal influence`, `APOE sex interaction`, `sex-specific`,
`estrogen`, `testosterone`, `stratified by sex`, `subgroup analysis by sex`

---

## Output Structure

```
workbooks/
  {year}/
    AD-ReproducibleResearch_{year}.xlsx      ← OSF-style curated workbook
    AD_{year}_analysis.xlsx                  ← Statistical summary
    keyword_scan_log.csv                     ← Open-science keyword scan log
    sex_keyword_scan_log.csv                 ← Sex keyword scan log
    pdf_affiliation_country_log.csv          ← Country extraction log
figures/
  {year}/
    fig1_sharing_by_month.png
    fig2_sex_keyword_analysis.png
    fig3_country_distribution.png
    fig4_hosting_platforms.png
```

## License

MIT — fully reproducible and open for extension by the community.
