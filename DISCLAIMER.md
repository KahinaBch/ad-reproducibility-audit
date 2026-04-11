# DISCLAIMER — Scope and Limitations of This Study

This document explicitly states the limitations of the reproducibility audit
conducted in this repository. Transparency about scope is a core scientific value.

---

## 1. Journal Specificity

This analysis is **restricted to a single journal**: *Alzheimer's & Dementia* (Wiley,
ISSN: 1552-5260 / 1552-5279). Results cannot be generalised to:
- The broader Alzheimer's disease literature
- Other dementia journals (e.g., *JAMA Neurology*, *Brain*, *Neurology*)
- Preprints (bioRxiv, medRxiv)
- Book chapters, conference abstracts, or review articles

## 2. Time Window

The analysis covers a **specific calendar year** of accepted articles. Year-to-year
variation in sharing rates is expected, and a single-year snapshot does not capture trends.

## 3. Keyword-Based Detection

Open-science indicators are detected via **keyword matching** (Step 3) followed by
**manual curation** (Step 4, in the original MRM methodology). Despite manual validation:
- False positives may remain (keyword present but no actual sharing)
- False negatives may occur (code/data shared but using non-standard terminology)
- Data Availability Statements vary in specificity and are not standardised

## 4. Sex-Specific Keyword Analysis

The sex-specific keyword detection (Step 4, novel contribution) is a **proxy measure**
for sex-stratified analysis. It captures papers that *mention* sex-related keywords, not
papers that perform rigorous sex-stratified statistics. A paper may:
- Mention sex as a demographic variable without stratifying results
- Use different terminology not covered by our keyword list
- Perform sex-stratified analyses without using the exact keywords in our list

The keyword list was defined a priori and is documented in `src/scan_sex_keywords_update_workbook.py`.

## 5. Country Attribution

Country is attributed to the **first author's affiliation** as extracted from the PDF.
This is a heuristic and may not reflect:
- The actual location of the research (e.g., a US-affiliated author studying an African cohort)
- Multi-institutional or multi-national papers (only first affiliation used)
- Changes in affiliation since publication

## 6. PDF Availability

PDFs are **not included** in this repository due to copyright restrictions. The pipeline
requires manual download of PDFs from the publisher (Wiley Online Library). This is a
limitation for full automated reproducibility, but the scripts, workbooks, and outputs
(figures, statistics) are fully documented and reproducible given access to the PDFs.

## 7. Reproducibility of This Pipeline

Despite the above limitations, this pipeline is **fully reproducible** given:
- Access to PDFs of *Alzheimer's & Dementia* articles for the target year
- A Python 3.11 environment with the packages in `environment.yml`
- Execution of Steps 1–7 in order (see README.md)

The pipeline can be **extended** to:
- Other journals (change ISSN in Step 1)
- Other years (change `--year` argument)
- Additional keywords (add to keyword lists in Steps 3 and 4)
- Additional analyses (add new scripts to `src/`)

---

*"All models are wrong, but some are useful."* — George Box

This study is one useful data point in the broader conversation about open-science
practices in Alzheimer's disease research.
