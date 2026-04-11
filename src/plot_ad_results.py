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
        frames.append(df)
    wb.close()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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

    # Annotate n per month
    for bar, n, pct in zip(bars, ns, pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"n={n}", ha="center", va="bottom", fontsize=8, color=GRAY)

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
    """Bar chart: sex-specific keyword detection rate."""
    if "Sex-specific keywords?" not in df.columns:
        log.warning("Sex keyword column not found — skipping sex figure.")
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"]
    has_sex = valid["Sex-specific keywords?"].str.lower().str.strip() == "yes"
    n_sex = has_sex.sum()
    n_total = len(valid)
    pct_sex = 100 * n_sex / n_total if n_total else 0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: Overall rate
    categories = [f"Sex-specific\n(n={n_sex})", f"Not sex-specific\n(n={n_total - n_sex})"]
    values = [n_sex, n_total - n_sex]
    colors = [PURPLE, GRAY]
    wedges, texts, autotexts = ax1.pie(
        values, labels=categories, colors=colors,
        autopct="%1.1f%%", startangle=90,
        wedgeprops={"edgecolor": BG, "linewidth": 2},
    )
    for t in autotexts:
        t.set_color(TEXT)
        t.set_fontsize(11)
    ax1.set_title(f"Papers with Sex-Specific Analysis\n{year} — Alzheimer's & Dementia")

    # Right: Top keywords
    if "Sex keywords matched" in valid.columns:
        kw_counts: dict[str, int] = {}
        for val in valid["Sex keywords matched"].dropna():
            for kw in str(val).split(";"):
                kw = kw.strip()
                if kw:
                    kw_counts[kw] = kw_counts.get(kw, 0) + 1

        if kw_counts:
            top_kw = sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            labels = [k for k, _ in top_kw]
            counts = [v for _, v in top_kw]
            y_pos = range(len(labels))
            ax2.barh(y_pos, counts, color=PINK, alpha=0.85, edgecolor=ACCENT, linewidth=0.5)
            ax2.set_yticks(list(y_pos))
            ax2.set_yticklabels(labels, fontsize=9)
            ax2.invert_yaxis()
            ax2.set_xlabel("Number of Papers")
            ax2.set_title("Most Frequent Sex-Specific Keywords")
            ax2.grid(axis="x", alpha=0.3)
        else:
            ax2.text(0.5, 0.5, "No keywords detected", ha="center", va="center",
                     transform=ax2.transAxes, color=GRAY)

    plt.tight_layout()
    path = out_dir / "fig2_sex_keyword_analysis.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def fig_country_distribution(df: pd.DataFrame, year: int, out_dir: Path):
    """Horizontal bar: top countries by paper count and sharing rate."""
    if "First author affiliation country" not in df.columns:
        return

    valid = df[df.get("False Positive?", pd.Series(dtype=str)).str.lower() != "yes"].copy()
    valid = valid[valid["First author affiliation country"].notna()]
    valid = valid[valid["First author affiliation country"] != ""]

    country_counts = valid["First author affiliation country"].value_counts().head(15)
    if country_counts.empty:
        return

    valid["_shared"] = (
        valid["Shared code?"].str.lower().str.strip().eq("yes") |
        valid["Shared data?"].str.lower().str.strip().eq("yes")
    )
    sharing_by_country = valid.groupby("First author affiliation country")["_shared"].mean() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Paper count
    countries = country_counts.index.tolist()
    counts = country_counts.values.tolist()
    colors_bar = [PURPLE if i < 3 else "#4C1D95" for i in range(len(countries))]
    ax1.barh(countries, counts, color=colors_bar, alpha=0.85, edgecolor=ACCENT, linewidth=0.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("Number of Papers")
    ax1.set_title(f"Top Countries — First Author ({year})")
    ax1.grid(axis="x", alpha=0.3)
    for i, (c, n) in enumerate(zip(countries, counts)):
        ax1.text(n + 0.2, i, str(n), va="center", fontsize=9)

    # Right: Sharing rate
    sharing_vals = [sharing_by_country.get(c, 0) for c in countries]
    colors_share = [PINK if v > 30 else BLUE_DARK for v in sharing_vals]
    ax2.barh(countries, sharing_vals, color=colors_share, alpha=0.85,
             edgecolor=ACCENT, linewidth=0.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("% Papers Sharing Code or Data")
    ax2.set_title("Code/Data Sharing Rate by Country")
    ax2.axvline(np.mean([v for v in sharing_vals if v > 0]),
                color=ACCENT, linestyle="--", linewidth=1, alpha=0.6)
    ax2.grid(axis="x", alpha=0.3)
    ax2.set_xlim(0, 100)
    for i, v in enumerate(sharing_vals):
        ax2.text(v + 0.5, i, f"{v:.0f}%", va="center", fontsize=9)

    plt.tight_layout()
    path = out_dir / "fig3_country_distribution.png"
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
    counts = {p: links.str.lower().str.contains(kw).sum() for p, kw in platform_map.items()}
    counts["Other"] = len(links) - sum(counts.values())
    counts = {k: v for k, v in counts.items() if v > 0}

    if not counts:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    platforms = list(counts.keys())
    vals = list(counts.values())
    palette = [PURPLE, PINK, BLUE_DARK, "#0E7490", "#065F46", GRAY]
    ax.bar(platforms, vals, color=palette[:len(platforms)], alpha=0.85,
           edgecolor=ACCENT, linewidth=0.5)
    ax.set_ylabel("Number of Links")
    ax.set_title(f"Code/Data Hosting Platforms — Alzheimer's & Dementia ({year})")
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.1, str(v), ha="center", fontsize=10)

    plt.tight_layout()
    path = out_dir / "fig4_hosting_platforms.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate publication-ready figures for A&D audit.")
    parser.add_argument("--xlsx", type=Path, required=True, help="Curated workbook path")
    parser.add_argument("--year", type=int, required=True, help="Year analysed")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for figures")
    args = parser.parse_args()

    out_dir = args.out_dir or (args.xlsx.parent / "figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== Step 7: Generating figures ===")
    df = load_df(args.xlsx)
    if df.empty:
        log.error("No data loaded — aborting.")
        return

    fig_sharing_over_time(df, args.year, out_dir)
    fig_sex_keyword_summary(df, args.year, out_dir)
    fig_country_distribution(df, args.year, out_dir)
    fig_hosting_platforms(df, args.year, out_dir)

    log.info(f"\nAll figures saved to: {out_dir}")
    log.info("=== Step 7 complete ===")


if __name__ == "__main__":
    main()
