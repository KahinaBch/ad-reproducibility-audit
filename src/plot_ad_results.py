"""
plot_ad_results.py
-------------------
Step 7 of the AD Reproducibility Audit pipeline.

Generates publication-ready figures from the curated workbook:
1. Code/data sharing rates over time (with historical comparison)
2. Hosting platform breakdown (pie/bar)
3. Geographic origin of first authors (bar)
4. Sex-specific keyword rate (bar + annotation)
5. Conditional sharing rate by country

Color palette matches the main website (purple/pink/dark blue theme).

Adapted from: KahinaBch/mrm-reproducible-research-2025
"""

import argparse
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/pipeline use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import openpyxl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Color palette ─────────────────────────────────────────────────────────────
PURPLE = "#7C3AED"
PINK = "#BE185D"
BLUE_DARK = "#1E3A8A"
BG = "#0F0A1E"
TEXT = "#F3F4F6"
ACCENT = "#DDD6FE"
GRAY = "#6B7280"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": "#1A1030",
    "axes.edgecolor": "#3D2070",
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "text.color": TEXT,
    "grid.color": "#2D1B69",
    "grid.alpha": 0.4,
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
})

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Historical sharing rates from MRM study for comparison context
HISTORICAL_SHARING = {
    "2019 (MRM)": 11,
    "2020 (MRM)": 14,
    "2021 (MRM)": 31,
}


def load_df(xlsx_path: Path) -> pd.DataFrame:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    frames = []
    for month in MONTHS:
        if month not in wb.sheetnames:
            continue
        ws = wb[month]
        data = list(ws.values)
        if len(data) < 2:
            continue
        df = pd.DataFrame(data[1:], columns=data[0])
        df["_Month"] = month
        df["_MonthNum"] = MONTHS.index(month) + 1
        df["_RowInSheet"] = list(range(2, 2 + len(df)))
        frames.append(df)
    wb.close()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _looks_like_repo_link(val: str) -> bool:
    if not val:
        return False
    s = str(val).strip().lower()
    if not s or s in {"none", "nan"}:
        return False
    return s.startswith("http") or "github.com" in s or "gitlab.com" in s or "osf.io" in s or "zenodo" in s


def augment_from_keyword_scan_log(df: pd.DataFrame, keyword_log_csv: Path | None) -> pd.DataFrame:
    """Merge Step 3 keyword scan log (month + matched_row) to fill link/sharing fields."""
    if df.empty or not keyword_log_csv:
        return df
    keyword_log_csv = Path(keyword_log_csv)
    if not keyword_log_csv.exists():
        return df

    log_df = pd.read_csv(keyword_log_csv)
    cols = {c.lower(): c for c in log_df.columns}
    needed = {"month", "matched_row", "keywords_found", "repo_link"}
    if not needed.issubset(set(cols.keys())):
        return df

    log_df = log_df.rename(columns={
        cols["month"]: "month",
        cols["matched_row"]: "matched_row",
        cols["keywords_found"]: "keywords_found",
        cols["repo_link"]: "repo_link",
    })

    log_df["month"] = log_df["month"].astype(str)
    log_df["matched_row"] = pd.to_numeric(log_df["matched_row"], errors="coerce")
    log_df = log_df.dropna(subset=["matched_row"])
    log_df["matched_row"] = log_df["matched_row"].astype(int)

    df2 = df.merge(
        log_df[["month", "matched_row", "keywords_found", "repo_link"]],
        how="left",
        left_on=["_Month", "_RowInSheet"],
        right_on=["month", "matched_row"],
    )

    repo_link = df2.get("repo_link", pd.Series("", index=df2.index)).fillna("")
    if "Link" in df2.columns:
        existing = df2["Link"].fillna("").astype(str).str.strip()
        df2["Link"] = existing.where(existing.ne(""), repo_link)
    if "Code repository link" in df2.columns:
        existing = df2["Code repository link"].fillna("").astype(str).str.strip()
        df2["Code repository link"] = existing.where(existing.ne(""), repo_link)

    # Infer sharing if empty
    code_indicators = {
        "github", "gitlab", "repository", "repo", "script", "pipeline", "workflow", "open-source", "open source",
        "code availability", "reproducible", "reproducibility",
    }
    data_indicators = {"zenodo", "dryad", "figshare", "osf", "dataverse", "open data", "dataset", "data availability"}

    kw = df2.get("keywords_found", pd.Series("", index=df2.index)).fillna("").astype(str).str.lower()
    kw_set = kw.apply(lambda v: {t.strip() for t in v.split(";") if t.strip()})
    inferred_code = kw_set.apply(lambda s: any(t in s for t in code_indicators)) | repo_link.apply(_looks_like_repo_link)
    inferred_data = kw_set.apply(lambda s: any(t in s for t in data_indicators))

    if "Shared code?" in df2.columns:
        existing = df2["Shared code?"].fillna("").astype(str).str.strip()
        df2["Shared code?"] = existing.where(existing.ne(""), inferred_code.map(lambda b: "Yes" if b else ""))
    if "Shared data?" in df2.columns:
        existing = df2["Shared data?"].fillna("").astype(str).str.strip()
        df2["Shared data?"] = existing.where(existing.ne(""), inferred_data.map(lambda b: "Yes" if b else ""))

    return df2


def augment_from_sex_keyword_scan_log(df: pd.DataFrame, sex_keyword_log_csv: Path | None) -> pd.DataFrame:
    """Merge Step 4 sex keyword scan log (month + pdf filename).

    Expected columns: pdf, month, sex_analysis, sex_aware_level
    """
    if df.empty or not sex_keyword_log_csv:
        return df
    sex_keyword_log_csv = Path(sex_keyword_log_csv)
    if not sex_keyword_log_csv.exists():
        return df

    log_df = pd.read_csv(sex_keyword_log_csv)
    cols = {c.lower(): c for c in log_df.columns}
    needed = {"pdf", "month", "sex_analysis", "sex_aware_level"}
    if not needed.issubset(set(cols.keys())):
        return df

    log_df = log_df.rename(columns={
        cols["pdf"]: "pdf",
        cols["month"]: "month",
        cols["sex_analysis"]: "sex_analysis",
        cols["sex_aware_level"]: "sex_aware_level",
    })

    log_df["month"] = log_df["month"].astype(str)
    log_df["pdf"] = log_df["pdf"].astype(str)

    # Normalize join keys
    df_key = df.copy()
    if "Filename" in df_key.columns:
        df_key["_FilenameNorm"] = df_key["Filename"].fillna("").astype(str).str.strip()
    else:
        df_key["_FilenameNorm"] = ""
    df_key["_MonthNorm"] = df_key.get("_Month", df_key.get("Month", "")).fillna("").astype(str).str.strip()

    log_df["_FilenameNorm"] = log_df["pdf"].fillna("").astype(str).str.strip()
    log_df["_MonthNorm"] = log_df["month"].fillna("").astype(str).str.strip()

    df2 = df_key.merge(
        log_df[["_FilenameNorm", "_MonthNorm", "sex_analysis", "sex_aware_level"]],
        how="left",
        on=["_FilenameNorm", "_MonthNorm"],
    )

    # Fill workbook columns if present and blank
    if "Sex-specific keywords?" in df2.columns:
        existing = df2["Sex-specific keywords?"].fillna("").astype(str).str.strip()
        incoming = df2["sex_analysis"].fillna("").astype(str).str.strip()
        df2["Sex-specific keywords?"] = existing.where(existing.ne(""), incoming)
    if "Sex-aware level" in df2.columns:
        existing = df2["Sex-aware level"].fillna("").astype(str).str.strip()
        incoming = df2["sex_aware_level"].fillna("").astype(str).str.strip()
        df2["Sex-aware level"] = existing.where(existing.ne(""), incoming)

    return df2.drop(columns=["_FilenameNorm", "_MonthNorm"], errors="ignore")


def _safe_yes_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    return df[col].fillna("").astype(str).str.lower().str.strip().eq("yes")


def fig_sex_analysis_by_month(df: pd.DataFrame, year: int, out_dir: Path):
    """Monthly % of papers with sex-analysis keywords (Step 4)."""
    if "Sex-specific keywords?" not in df.columns:
        log.warning("Sex-specific keywords column not found — skipping sex-analysis-by-month plot.")
        return

    monthly = []
    for i, month in enumerate(MONTHS, 1):
        m_df = df[df["_MonthNum"] == i]
        if len(m_df) == 0:
            continue
        valid = m_df[m_df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"]
        if len(valid) == 0:
            continue
        has_sex = _safe_yes_series(valid, "Sex-specific keywords?")
        pct = float(100 * has_sex.mean())
        monthly.append({"month": month[:3], "pct": round(pct, 1)})

    if not monthly:
        log.warning("No monthly data for sex-analysis-by-month plot.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    months = [r["month"] for r in monthly]
    pcts = [r["pct"] for r in monthly]

    bars = ax.bar(months, pcts, color=PINK, alpha=0.85, edgecolor=ACCENT, linewidth=0.6, zorder=3)
    ax.plot(months, pcts, color=ACCENT, linewidth=2, marker="o", markersize=5, zorder=4)

    for bar, pct in zip(bars, pcts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{pct:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            color=ACCENT,
        )

    ax.set_xlabel("Acceptance Month")
    ax.set_ylabel("% Papers with Sex-Analysis Keywords")
    ax.set_title(f"Sex-Analysis Keyword Detection by Acceptance Month ({year})")
    ax.grid(axis="y", zorder=0)
    ax.set_ylim(0, max(pcts + [10]) * 1.2)

    plt.tight_layout()
    path = out_dir / "fig5_sex_analysis_by_month.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_sex_analysis_overall(df: pd.DataFrame, year: int, out_dir: Path):
    """Single-plot figure: overall % of valid papers flagged as sex-analysis."""
    if "Sex-specific keywords?" not in df.columns:
        log.warning("Sex-specific keywords column not found — skipping sex-analysis plot.")
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    if len(valid) == 0:
        return

    has_sex = _safe_yes_series(valid, "Sex-specific keywords?")
    pct_sex = float(100 * has_sex.mean())
    pct_no = 100.0 - pct_sex

    fig, ax = plt.subplots(figsize=(8.5, 5))
    labels = ["Sex analysis (Yes)", "Sex analysis (No)"]
    vals = [round(pct_sex, 1), round(pct_no, 1)]
    colors = [PINK, GRAY]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor=ACCENT, linewidth=0.6)
    ax.set_ylabel("% of Valid Papers")
    ax.set_title(f"Sex-Analysis Keyword Detection Rate — Alzheimer's & Dementia ({year})")
    ax.set_ylim(0, max(vals + [10]) * 1.25)
    ax.grid(axis="y", alpha=0.3)

    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{v:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            color=ACCENT,
        )

    plt.tight_layout()
    # Keep filename stable even though this is now a single-plot figure.
    path = out_dir / "fig2_sex_keyword_analysis.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_top_sex_keywords(df: pd.DataFrame, year: int, out_dir: Path):
    """Single-plot figure: top sex keywords, shown as % of sex-analysis papers."""
    if "Sex keywords matched" not in df.columns or "Sex-specific keywords?" not in df.columns:
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    valid = valid[_safe_yes_series(valid, "Sex-specific keywords?")]
    if len(valid) == 0:
        return

    kw_counts: dict[str, int] = {}
    for val in valid["Sex keywords matched"].dropna():
        for kw in str(val).split(";"):
            kw = kw.strip()
            if kw:
                kw_counts[kw] = kw_counts.get(kw, 0) + 1

    if not kw_counts:
        return

    top_kw = sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)[:12]
    labels = [k for k, _ in top_kw]
    counts = np.array([v for _, v in top_kw], dtype=float)
    denom = float(len(valid))
    pcts = (counts / denom * 100).round(1) if denom else counts * 0

    fig, ax = plt.subplots(figsize=(10.5, 6))
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, pcts, color=PINK, alpha=0.85, edgecolor=ACCENT, linewidth=0.5)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("% of Sex-Analysis Papers")
    ax.set_title(f"Most Frequent Sex-Analysis Keywords ({year})")
    ax.grid(axis="x", alpha=0.3)

    for bar, v in zip(bars, pcts):
        ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    path = out_dir / "fig7_top_sex_keywords.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_sex_aware_level_distribution(df: pd.DataFrame, year: int, out_dir: Path):
    """Overall distribution of Sex-aware level, as % of valid papers."""
    if "Sex-aware level" not in df.columns and "sex_aware_level" not in df.columns:
        log.warning("Sex-aware level column not found — skipping sex-aware-level plot.")
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    if len(valid) == 0:
        return

    level_col = "Sex-aware level" if "Sex-aware level" in valid.columns else "sex_aware_level"
    levels = valid[level_col].fillna("").astype(str).str.strip().str.lower()
    levels = levels.replace({"": "none", "nan": "none"})

    # Normalize common variants
    levels = levels.replace({
        "sex-aware main focus": "main focus",
        "sex-aware consideration": "consideration",
        "none": "none",
    })
    levels = levels.where(levels.isin({"main focus", "consideration", "none"}), "other")

    order = ["main focus", "consideration", "none", "other"]
    counts = levels.value_counts()
    counts = counts.reindex(order).fillna(0).astype(int)
    total = int(counts.sum())
    pcts = (counts / total * 100).round(1) if total else counts * 0

    fig, ax = plt.subplots(figsize=(8.5, 5))
    labels = ["Main focus", "Consideration", "None", "Other"]
    vals = [float(pcts[k]) for k in order]
    colors = [PURPLE, PINK, BLUE_DARK, GRAY]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor=ACCENT, linewidth=0.6)
    ax.set_ylabel("% of Valid Papers")
    ax.set_title(f"Sex-Aware Level Distribution — Alzheimer's & Dementia ({year})")
    ax.set_ylim(0, max(vals + [10]) * 1.25)
    ax.grid(axis="y", alpha=0.3)

    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{v:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            color=ACCENT,
        )

    plt.tight_layout()
    path = out_dir / "fig6_sex_aware_level_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_sharing_over_time(df: pd.DataFrame, year: int, out_dir: Path):
    """Monthly sharing rates across the year + historical comparison."""
    monthly = []
    for i, month in enumerate(MONTHS, 1):
        m_df = df[df["_MonthNum"] == i]
        if len(m_df) == 0:
            continue
        valid = m_df[m_df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"]
        if len(valid) == 0:
            continue
        pct = 100 * (
            (valid["Shared code?"].str.lower().str.strip().eq("yes") |
             valid["Shared data?"].str.lower().str.strip().eq("yes")).mean()
        )
        monthly.append({"month": month[:3], "pct": round(pct, 1), "n": len(valid)})

    if not monthly:
        log.warning("No monthly data for sharing-over-time plot.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    months = [r["month"] for r in monthly]
    pcts = [r["pct"] for r in monthly]
    ns = [r["n"] for r in monthly]

    bars = ax.bar(months, pcts, color=PURPLE, alpha=0.8, edgecolor=ACCENT, linewidth=0.6, zorder=3)
    ax.plot(months, pcts, color=ACCENT, linewidth=2, marker="o", markersize=5, zorder=4)

    # Annotate percentage per month (avoid raw counts)
    for bar, pct in zip(bars, pcts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{pct:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            color=ACCENT,
        )

    # Historical reference line
    annual_pct = np.mean(pcts)
    ax.axhline(annual_pct, color=PINK, linestyle="--", linewidth=1.5, alpha=0.8,
               label=f"Annual mean: {annual_pct:.1f}%")

    ax.set_xlabel("Acceptance Month")
    ax.set_ylabel("% Papers Sharing Code or Data")
    ax.set_title(f"Code/Data Sharing Rate by Acceptance Month — Alzheimer's & Dementia ({year})")
    ax.legend(fontsize=9)
    ax.grid(axis="y", zorder=0)
    ax.set_ylim(0, max(pcts + [10]) * 1.2)

    plt.tight_layout()
    path = out_dir / "fig1_sharing_by_month.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_sex_keyword_summary(df: pd.DataFrame, year: int, out_dir: Path):
    """Deprecated: retained for backward compatibility.

    This function previously produced a multi-panel figure. Call:
    - fig_sex_analysis_overall
    - fig_top_sex_keywords
    instead.
    """
    fig_sex_analysis_overall(df, year, out_dir)


def fig_country_distribution(df: pd.DataFrame, year: int, out_dir: Path):
    """Single-plot figure: % of papers by first-author country (top 15)."""
    if "First author affiliation country" not in df.columns:
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    valid = valid[valid["First author affiliation country"].notna()]
    valid = valid[valid["First author affiliation country"] != ""]

    country_counts = valid["First author affiliation country"].value_counts().head(15)
    if country_counts.empty:
        return

    # Convert paper counts to proportions (%) among identified countries
    total_identified = country_counts.sum()
    country_pct = (country_counts / total_identified * 100).round(1) if total_identified else country_counts * 0

    fig, ax = plt.subplots(figsize=(10.5, 6))

    countries = country_counts.index.tolist()
    pct_vals = country_pct.values.tolist()
    colors_bar = [PURPLE if i < 3 else "#4C1D95" for i in range(len(countries))]
    bars = ax.barh(countries, pct_vals, color=colors_bar, alpha=0.85, edgecolor=ACCENT, linewidth=0.5)
    ax.invert_yaxis()
    ax.set_xlabel("% of Papers (among countries identified)")
    ax.set_title(f"First-Author Country Distribution ({year})")
    ax.grid(axis="x", alpha=0.3)
    for bar, v in zip(bars, pct_vals):
        ax.text(v + 0.2, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    path = out_dir / "fig3_country_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_country_sharing_rate(df: pd.DataFrame, year: int, out_dir: Path):
    """Single-plot figure: % sharing (code OR data) by country (top 15 countries)."""
    if "First author affiliation country" not in df.columns:
        return
    if "Shared code?" not in df.columns and "Shared data?" not in df.columns:
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    valid = valid[valid["First author affiliation country"].notna()]
    valid = valid[valid["First author affiliation country"] != ""]
    if len(valid) == 0:
        return

    country_counts = valid["First author affiliation country"].value_counts().head(15)
    if country_counts.empty:
        return
    countries = country_counts.index.tolist()

    valid["_shared"] = (
        valid.get("Shared code?", pd.Series("", index=valid.index)).fillna("").astype(str).str.lower().str.strip().eq("yes") |
        valid.get("Shared data?", pd.Series("", index=valid.index)).fillna("").astype(str).str.lower().str.strip().eq("yes")
    )
    sharing_by_country = (valid.groupby("First author affiliation country")["_shared"].mean() * 100).to_dict()
    sharing_vals = [round(float(sharing_by_country.get(c, 0)), 1) for c in countries]

    fig, ax = plt.subplots(figsize=(10.5, 6))
    colors_share = [PINK if v >= 30 else BLUE_DARK for v in sharing_vals]
    bars = ax.barh(countries, sharing_vals, color=colors_share, alpha=0.85, edgecolor=ACCENT, linewidth=0.5)
    ax.invert_yaxis()
    ax.set_xlabel("% Papers Sharing Code or Data")
    ax.set_title(f"Code/Data Sharing Rate by Country ({year})")
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(0, 100)

    for bar, v in zip(bars, sharing_vals):
        ax.text(v + 0.5, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)

    plt.tight_layout()
    path = out_dir / "fig8_country_sharing_rate.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_hosting_platforms(df: pd.DataFrame, year: int, out_dir: Path):
    """Bar chart of hosting platform usage."""
    if "Link" not in df.columns:
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"]
    links = valid["Link"].dropna()
    links = links[links.astype(str).str.strip() != ""]

    platform_map = {
        "GitHub": "github",
        "OSF": "osf.io",
        "Zenodo": "zenodo",
        "Dryad": "datadryad",
        "Figshare": "figshare",
    }
    counts = {p: int(links.str.lower().str.contains(kw).sum()) for p, kw in platform_map.items()}
    counts["Other"] = int(len(links) - sum(counts.values()))
    counts = {k: v for k, v in counts.items() if v > 0}

    if not counts:
        return

    total_links = sum(counts.values())
    pct = {k: (v / total_links * 100) if total_links else 0 for k, v in counts.items()}

    fig, ax = plt.subplots(figsize=(8, 5))
    platforms = list(counts.keys())
    vals = [round(pct[p], 1) for p in platforms]
    palette = [PURPLE, PINK, BLUE_DARK, "#0E7490", "#065F46", GRAY]
    ax.bar(platforms, vals, color=palette[:len(platforms)], alpha=0.85,
           edgecolor=ACCENT, linewidth=0.5)
    ax.set_ylabel("% of Links")
    ax.set_title(f"Code/Data Hosting Platforms — Alzheimer's & Dementia ({year})")
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.4, f"{v:.1f}%", ha="center", fontsize=10)

    plt.tight_layout()
    path = out_dir / "fig4_hosting_platforms.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_github_link_rate(df: pd.DataFrame, year: int, out_dir: Path):
    """Single-plot figure: % of valid papers that provide a GitHub link."""
    # We prefer the merged fields from keyword_scan_log.csv, but fall back to workbook columns.
    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    if len(valid) == 0:
        return

    link_cols = []
    for c in ["repo_link", "Link", "Code repository link"]:
        if c in valid.columns:
            link_cols.append(c)

    if not link_cols:
        log.warning("No link columns available — skipping GitHub link rate plot.")
        return

    def has_github(row) -> bool:
        for c in link_cols:
            v = row.get(c)
            if v is None:
                continue
            s = str(v).strip().lower()
            if not s or s in {"none", "nan"}:
                continue
            if "github.com" in s or s.startswith("github"):
                return True
        return False

    has_gh = valid.apply(has_github, axis=1)
    pct_yes = float(100 * has_gh.mean())
    pct_no = 100.0 - pct_yes

    fig, ax = plt.subplots(figsize=(8.5, 5))
    labels = ["GitHub link (Yes)", "GitHub link (No)"]
    vals = [round(pct_yes, 1), round(pct_no, 1)]
    colors = [PURPLE, GRAY]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor=ACCENT, linewidth=0.6)
    ax.set_ylabel("% of Valid Papers")
    ax.set_title(f"Papers Providing a GitHub Link — Alzheimer's & Dementia ({year})")
    ax.set_ylim(0, max(vals + [10]) * 1.25)
    ax.grid(axis="y", alpha=0.3)

    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{v:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            color=ACCENT,
        )

    plt.tight_layout()
    path = out_dir / "fig9_github_link_rate.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def _normalize_gender(val: str) -> str:
    s = "" if val is None else str(val).strip()
    if not s or s.lower() in {"nan", "none", ""}:
        return "Unknown"
    s_low = s.lower()
    if s_low.startswith("f"):
        return "Female"
    if s_low.startswith("m"):
        return "Male"
    if "andro" in s_low:
        return "Androgynous"
    if "unknown" in s_low:
        return "Unknown"
    return "Other"


def fig_author_gender_distribution(author_gender_log_csv: Path | None, year: int, out_dir: Path):
    """Two single-plot figures: first- and last-author gender distributions (%)."""
    if not author_gender_log_csv:
        return
    author_gender_log_csv = Path(author_gender_log_csv)
    if not author_gender_log_csv.exists():
        log.warning("Author gender log not found — skipping gender distribution plots.")
        return

    df = pd.read_csv(author_gender_log_csv)
    if df.empty:
        return

    if "status" in df.columns:
        df = df[df["status"].fillna("").astype(str).str.lower().str.strip().eq("ok")]
    if df.empty:
        return

    order = ["Female", "Male", "Androgynous", "Unknown", "Other"]

    def _plot(col: str, out_name: str, title: str, color: str):
        if col not in df.columns:
            return
        g = df[col].apply(_normalize_gender)
        counts = g.value_counts().reindex(order).fillna(0).astype(int)
        total = int(counts.sum())
        if total == 0:
            return
        pcts = (counts / total * 100).round(1)

        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        labels = order
        vals = [float(pcts[k]) for k in order]
        palette = [color, BLUE_DARK, "#A855F7", GRAY, "#0E7490"]
        bars = ax.bar(labels, vals, color=palette, alpha=0.85, edgecolor=ACCENT, linewidth=0.6)
        ax.set_ylabel("% of Papers")
        ax.set_title(f"{title} — Alzheimer's & Dementia ({year})")
        ax.set_ylim(0, max(vals + [10]) * 1.25)
        ax.grid(axis="y", alpha=0.3)

        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{v:.1f}%",
                ha="center",
                va="bottom",
                fontsize=10,
                color=ACCENT,
            )

        plt.tight_layout()
        path = out_dir / out_name
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        log.info(f"  Saved: {path}")

    _plot(
        col="first_author_gender",
        out_name="fig10_first_author_gender_distribution.png",
        title="First-Author Gender Distribution",
        color=PURPLE,
    )
    _plot(
        col="last_author_gender",
        out_name="fig11_last_author_gender_distribution.png",
        title="Last-Author Gender Distribution",
        color=PINK,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate publication-ready figures for A&D audit.")
    parser.add_argument("--xlsx", type=Path, required=True, help="Curated workbook path")
    parser.add_argument("--year", type=int, required=True, help="Year analysed")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for figures (default: plots/{year})")
    parser.add_argument(
        "--keyword-log-csv",
        type=Path,
        default=None,
        help="Optional Step 3 keyword scan log (default: alongside workbook if present)",
    )
    parser.add_argument(
        "--sex-keyword-log-csv",
        type=Path,
        default=None,
        help="Optional Step 4 sex keyword scan log (default: alongside workbook if present)",
    )
    parser.add_argument(
        "--author-gender-log-csv",
        type=Path,
        default=None,
        help="Optional author gender log CSV (default: alongside workbook if present)",
    )
    args = parser.parse_args()

    out_dir = args.out_dir or (Path("plots") / str(args.year))
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== Step 8: Generating figures ===")
    df = load_df(args.xlsx)
    keyword_log = args.keyword_log_csv
    if keyword_log is None:
        candidate = args.xlsx.parent / "keyword_scan_log.csv"
        keyword_log = candidate if candidate.exists() else None
    df = augment_from_keyword_scan_log(df, keyword_log)

    sex_keyword_log = args.sex_keyword_log_csv
    if sex_keyword_log is None:
        candidate = args.xlsx.parent / "sex_keyword_scan_log.csv"
        sex_keyword_log = candidate if candidate.exists() else None
    df = augment_from_sex_keyword_scan_log(df, sex_keyword_log)

    author_gender_log = args.author_gender_log_csv
    if author_gender_log is None:
        candidate = args.xlsx.parent / "author_gender_log.csv"
        author_gender_log = candidate if candidate.exists() else None
    if df.empty:
        log.error("No data loaded — aborting.")
        return

    fig_sharing_over_time(df, args.year, out_dir)
    fig_sex_analysis_overall(df, args.year, out_dir)
    fig_top_sex_keywords(df, args.year, out_dir)
    fig_sex_aware_level_distribution(df, args.year, out_dir)
    fig_country_distribution(df, args.year, out_dir)
    fig_country_sharing_rate(df, args.year, out_dir)
    fig_hosting_platforms(df, args.year, out_dir)
    fig_github_link_rate(df, args.year, out_dir)
    fig_author_gender_distribution(author_gender_log, args.year, out_dir)

    log.info(f"\nAll figures saved to: {out_dir}")
    log.info("=== Step 8 complete ===")


if __name__ == "__main__":
    main()
