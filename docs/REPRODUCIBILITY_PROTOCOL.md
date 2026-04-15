# Reproducibility Protocol (AD Reproducibility Audit)

This protocol defines the expected data organization, execution order, and quality-control checks for reproducing the *Alzheimer's & Dementia* audit.

## 1) Scope

- Target journal: *Alzheimer's & Dementia* (ISSN: 1552-5260)
- Analysis focus:
  - Open-science sharing indicators
  - Sex-specific analysis signals (AD-specific contribution)
  - Dataset mention detection (catalogue-based keyword search)
  - First-author affiliation country
- Optional / exploratory:
  - Author metadata + name-based gender inference (Step 5b)

## 2) Required structure

```
.
├── data/
│   ├── raw/
│   │   └── ad_{year}_dois.csv
│   └── derived/
├── src/
├── workbooks/
│   └── {year}/
├── plots/
│   └── {year}/
└── docs/
```

## 3) Inputs and outputs by step

### Step 1 — DOI retrieval
Script: `src/get_ad_dois_by_year.py`

- Input: year argument
- Output: `data/raw/ad_{year}_dois.csv`

### Step 2 — PDF sorting + workbook creation
Script: `src/sort_ad_pdfs_by_acceptance_and_build_workbook.py`

- Input: year, PDF folder containing downloaded PDFs (flat folder)
- Output: `workbooks/{year}/AD-ReproducibleResearch_{year}.xlsx`

Notes:
- The script extracts date metadata from each PDF and sorts papers into month folders.
- Current implementation uses acceptance-date patterns detected in PDF text to infer month.
- Article titles are extracted from PDF metadata/text (filename used only as fallback).
- If a month cannot be inferred, papers are placed in `Unclassified` in the workbook.

### Step 3 — Code-availability / reproducibility keyword scan
Script: `src/scan_keywords_update_workbook.py`

- Input: year PDF folder, workbook path
- Output:
  - Updated workbook
  - Updates workbook columns including `Keywords Matched` and `Code repository link`
  - `workbooks/{year}/keyword_scan_log.csv` (includes `repo_link` and `matched_row`)

### Step 4 — Sex-specific keyword scan (AD-specific)
Script: `src/scan_sex_keywords_update_workbook.py`

- Input: year PDF folder, workbook path
- Output:
  - Updated workbook columns:
    - `Sex-specific keywords?`
    - `Sex keywords matched`
    - `Sex-aware level`
  - `workbooks/{year}/sex_keyword_scan_log.csv`

Step 4 classification rules:
- `sex-aware main focus`: sex/gender keyword match in the article title.
- `sex-aware consideration`: sex/gender keyword match in body text (but not title).
- Broad terms `sex`, `gender`, `woman`, `female` are checked in title only.

### Step 4b — Dataset mention scan (catalogue-based)
Script: `src/scan_dataset_mentions_update_workbook.py`

- Input:
  - year PDF folder
  - workbook path
  - dataset catalogue JSON path (default: sibling repo `ad-dataset-catalogue/data/neuroimaging_genetics.json`)
- Output:
  - Updated workbook columns:
    - `Dataset(s) mentioned?`
    - `Dataset names matched`
  - `workbooks/{year}/dataset_scan_log.csv` (includes `datasets_found` and `matched_row`)

Notes:
- This is a keyword-search heuristic; manual validation is recommended.

### Step 5 — Manual curation

Manual checks in workbook:
- `False Positive?`
- `Shared code?`
- `Shared data?`
- `Language(s)`

### Step 5b — Author and name-based gender enrichment (intermediate)
Script: `src/add_author_gender_from_doi.py`

- Input: curated workbook with DOI column
- Output:
  - Updated workbook columns:
    - `First author`
    - `First author gender`
    - `Last author`
    - `Last author gender`
  - `workbooks/{year}/author_gender_log.csv`

Notes:
- Author names are retrieved from Crossref metadata using DOI.
- Gender is inferred from first names when identifiable (`Male`, `Female`, `Androgynous`, `Unknown`).

### Step 6 — Country extraction
Script: `src/add_affiliation_country_from_pdfs.py`

- Input: year PDF folder, workbook path
- Output:
  - Updated workbook country fields
  - `workbooks/{year}/pdf_affiliation_country_log.csv`

### Step 7 — Statistical analysis
Script: `src/run_ad_analysis.py`

- Input: curated workbook
- Output: `workbooks/{year}/AD_{year}_analysis.xlsx`

Notes:
- If the workbook has blank link/sharing fields, Step 7 can optionally merge `keyword_scan_log.csv` by (month, sheet row) to fill missing `Link` / `Code repository link` and infer missing sharing flags.

### Step 8 — Plot generation
Script: `src/plot_ad_results.py`

- Input: curated workbook
- Output: `plots/{year}/fig*.png`

Notes:
- Step 8 can optionally merge `keyword_scan_log.csv` and `sex_keyword_scan_log.csv` to fill missing fields.
- Step 8 can optionally read `author_gender_log.csv` to generate first/last author gender distribution figures.

## 4) Quality control checklist

Before statistics (Step 7):
- Workbook has all month sheets expected for the analysis period.
- `False Positive?`, `Shared code?`, and `Shared data?` columns have been reviewed.
- Sex-keyword scan completed and logs generated.
- Country extraction completed and log reviewed for unresolved rows.

Before plots (Step 8):
- Step 7 output workbook exists.
- Missing values are handled or documented.

## 5) Reproducibility notes

- PDFs are not distributed in-repo due to copyright constraints.
- Keep script execution logs/version notes in this `docs/` folder when keyword lists or extraction rules are updated.
- Any methodological change should be recorded in README and protocol together.

## 6) Current run status (2025)

- Manual retrieval completed for *Alzheimer's & Dementia* Volume 21 PDFs.
- Source folder used: `data/raw/pdfs/2025`
- Sorting executed with:
  - `src/sort_ad_pdfs_by_acceptance_and_build_workbook.py --year 2025 --pdf-folder data/raw/pdfs/2025 --out workbooks/2025/AD-ReproducibleResearch_2025.xlsx`
- Result:
  - Month subfolders created under `data/raw/pdfs/2025/` (January to December)
  - Workbook created at `workbooks/2025/AD-ReproducibleResearch_2025.xlsx`
  - Top-level original flat PDFs moved to `data/raw/pdfs/2025/original_flat_backup/` for cleanup and traceability.
  - Title column corrected from PDF-derived title extraction.
  - Step 4 re-run after title correction with sex-aware levels:
    - `sex-aware main focus`: 37
    - `sex-aware consideration`: 196
    - `none`: 680
