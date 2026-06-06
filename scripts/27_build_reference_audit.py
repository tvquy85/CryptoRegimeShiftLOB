from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

import bibtexparser
import pandas as pd
import requests


CoverageRule = dict[str, Any]


COVERAGE_RULES: dict[str, CoverageRule] = {
    "fi_2010": {"keys": {"ntakaris2018benchmark"}, "label": "FI-2010 / LOB benchmark dataset"},
    "deeplob": {"keys": {"deeplob2019", "sirignano2019deeplob"}, "label": "DeepLOB / canonical deep LOB"},
    "lob_benchmark": {"keys": {"ntakaris2018benchmark", "prata2024lobbenchmark", "briola2025lobframe"}, "label": "LOB benchmark/comparison"},
    "lob_transformer_deep_temporal": {"keys": {"xiao2025lit", "bai2018tcn", "briola2025lobframe"}, "label": "Transformer/deep temporal LOB"},
    "market_microstructure": {
        "keys": {"madhavan2000microstructure", "ohara2015highfrequency", "gould2013limitorderbooks", "cont2010stochasticlob", "cartea2015algorithmic"},
        "label": "Market microstructure",
    },
    "crypto_microstructure": {
        "keys": {"almeida2024cryptomicrostructure", "schnaubelt2019bitcoinlob", "angerer2025cryptoorderbook", "iosco_crypto2023", "fsb2023crypto"},
        "label": "Crypto microstructure / market integrity",
    },
    "dataset_documentation": {"keys": {"cryptolake_data"}, "label": "Dataset provider documentation"},
    "time_series_validation": {"keys": {"bergmeir2018timeseriescv", "cerqueira2020timeserieseval"}, "label": "Time-series validation"},
    "distribution_shift": {"keys": {"quinonero2009datasetshift", "ovadia2019uncertainty", "koh2021wilds"}, "label": "Distribution shift"},
    "bootstrap_statistical_validation": {"keys": {"efron1979bootstrap", "politis1994stationarybootstrap"}, "label": "Bootstrap/statistical validation"},
    "backtest_overfitting": {"keys": {"white2000realitycheck", "bailey2016backtestoverfitting", "lopezdeprado2018afml"}, "label": "Backtest overfitting/data snooping"},
}


PEER_REVIEWED_TYPES = {"article", "inproceedings", "conference", "proceedings"}
REPORT_OR_DOC_TYPES = {"techreport", "book", "misc", "manual"}


@dataclass(frozen=True)
class ReferenceMetadata:
    title: str = ""
    year: str = ""
    venue: str = ""
    doi: str = ""
    source: str = ""
    status: str = "MISSING"


def strip_bibtex_code_fence(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:bibtex)?\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip() + "\n"


def parse_bib_entries(text: str) -> list[dict[str, Any]]:
    clean = strip_bibtex_code_fence(text)
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    db = bibtexparser.loads(clean, parser=parser)
    return sorted(db.entries, key=lambda entry: str(entry.get("ID", "")).lower())


def extract_cite_keys(tex_text: str) -> set[str]:
    keys: set[str] = set()
    pattern = re.compile(r"\\cite(?:\[[^\]]*\])?(?:\[[^\]]*\])?\{([^}]+)\}")
    for match in pattern.finditer(tex_text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def normalize_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("\\&", " and ")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(left: str, right: str) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return float(SequenceMatcher(None, left_norm, right_norm).ratio())


def title_match_acceptable(left: str, right: str, *, threshold: float = 0.90) -> bool:
    """Return True when titles match exactly enough for bibliography audit.

    Crossref occasionally returns a short canonical title while BibTeX stores a
    subtitle, e.g. "XGBoost" vs "XGBoost: A Scalable Tree Boosting System".
    Treating containment as acceptable prevents false DOI mismatch flags while
    preserving strict matching for unrelated titles.
    """
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return False
    if title_similarity(left_norm, right_norm) >= threshold:
        return True
    shorter, longer = sorted((left_norm, right_norm), key=len)
    return len(shorter) >= 6 and shorter in longer


def entry_venue(entry: dict[str, Any]) -> str:
    for key in ("journal", "booktitle", "publisher", "institution"):
        if entry.get(key):
            return str(entry[key])
    return ""


def venue_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return title_similarity(left, right)


def _first_item(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return str(value or "")


def _crossref_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not payload or payload.get("status") != "ok":
        return None
    message = payload.get("message")
    return message if isinstance(message, dict) else None


def crossref_by_doi(doi: str, *, timeout: float = 12.0) -> ReferenceMetadata:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi.strip(), safe='')}"
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "CryptoRegimeShift reference audit (mailto:anonymous@example.com)"})
        if response.status_code == 404:
            return ReferenceMetadata(doi=doi, status="NOT_FOUND", source="crossref_doi")
        response.raise_for_status()
        message = _crossref_message(response.json())
        if not message:
            return ReferenceMetadata(doi=doi, status="NOT_FOUND", source="crossref_doi")
        return ReferenceMetadata(
            title=_first_item(message.get("title")),
            year=str(((message.get("published-print") or message.get("published-online") or message.get("issued") or {}).get("date-parts") or [[""]])[0][0]),
            venue=_first_item(message.get("container-title")),
            doi=str(message.get("DOI") or doi),
            source="crossref_doi",
            status="FOUND",
        )
    except requests.RequestException:
        return ReferenceMetadata(doi=doi, status="VERIFY_TIMEOUT", source="crossref_doi")


def crossref_by_title(title: str, *, timeout: float = 12.0) -> ReferenceMetadata:
    if not title:
        return ReferenceMetadata(status="MISSING", source="crossref_title")
    params = {"query.title": title, "rows": 3, "select": "DOI,title,container-title,issued,published-print,published-online,type"}
    try:
        response = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=timeout,
            headers={"User-Agent": "CryptoRegimeShift reference audit (mailto:anonymous@example.com)"},
        )
        response.raise_for_status()
        message = _crossref_message(response.json())
        items = message.get("items", []) if message else []
        if not items:
            return ReferenceMetadata(status="NOT_FOUND", source="crossref_title")
        best = max(items, key=lambda item: title_similarity(title, _first_item(item.get("title"))))
        return ReferenceMetadata(
            title=_first_item(best.get("title")),
            year=str(((best.get("published-print") or best.get("published-online") or best.get("issued") or {}).get("date-parts") or [[""]])[0][0]),
            venue=_first_item(best.get("container-title")),
            doi=str(best.get("DOI") or ""),
            source="crossref_title",
            status="FOUND",
        )
    except requests.RequestException:
        return ReferenceMetadata(status="VERIFY_TIMEOUT", source="crossref_title")


def arxiv_by_id(eprint: str, *, timeout: float = 25.0) -> ReferenceMetadata:
    if not eprint:
        return ReferenceMetadata(status="MISSING", source="arxiv")
    try:
        response = requests.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": eprint},
            timeout=timeout,
            headers={"User-Agent": "CryptoRegimeShift reference audit"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", namespace)
        if entry is None:
            return ReferenceMetadata(status="NOT_FOUND", source="arxiv")
        title = entry.findtext("atom:title", default="", namespaces=namespace)
        published = entry.findtext("atom:published", default="", namespaces=namespace)
        return ReferenceMetadata(
            title=re.sub(r"\s+", " ", title).strip(),
            year=published[:4],
            venue="arXiv",
            doi="",
            source="arxiv",
            status="FOUND",
        )
    except (requests.RequestException, ET.ParseError):
        try:
            response = requests.get(
                f"https://arxiv.org/abs/{urllib.parse.quote(eprint, safe='')}",
                timeout=timeout,
                headers={"User-Agent": "CryptoRegimeShift reference audit"},
            )
            response.raise_for_status()
            title_match = re.search(r'<meta\s+name="citation_title"\s+content="([^"]+)"', response.text, flags=re.IGNORECASE)
            date_match = re.search(r'<meta\s+name="citation_date"\s+content="([^"]+)"', response.text, flags=re.IGNORECASE)
            return ReferenceMetadata(
                title=(title_match.group(1) if title_match else ""),
                year=(date_match.group(1)[:4] if date_match else ""),
                venue="arXiv",
                doi="",
                source="arxiv_abs",
                status="FOUND",
            )
        except requests.RequestException:
            return ReferenceMetadata(status="VERIFY_TIMEOUT", source="arxiv")


def check_url(url: str, *, timeout: float = 12.0) -> str:
    if not url:
        return "MISSING_URL"
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "CryptoRegimeShift reference audit"})
        if response.status_code in {403, 405} or response.status_code >= 500:
            response = requests.get(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "CryptoRegimeShift reference audit"})
        if 200 <= response.status_code < 400:
            return "OK"
        return f"HTTP_{response.status_code}"
    except requests.RequestException:
        return "VERIFY_TIMEOUT"


def entry_categories(key: str) -> list[str]:
    categories = []
    for category, rule in COVERAGE_RULES.items():
        if key in rule["keys"]:
            categories.append(category)
    return categories


def audit_entry(
    entry: dict[str, Any],
    cited_keys: set[str],
    *,
    crossref_doi_lookup: Callable[[str], ReferenceMetadata] | None = None,
    crossref_title_lookup: Callable[[str], ReferenceMetadata] | None = None,
    arxiv_lookup: Callable[[str], ReferenceMetadata] | None = None,
    url_lookup: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    crossref_doi_lookup = crossref_doi_lookup or crossref_by_doi
    crossref_title_lookup = crossref_title_lookup or crossref_by_title
    arxiv_lookup = arxiv_lookup or arxiv_by_id
    url_lookup = url_lookup or check_url

    key = str(entry.get("ID", ""))
    entry_type = str(entry.get("ENTRYTYPE", "")).lower()
    title = str(entry.get("title", ""))
    year = str(entry.get("year", ""))
    venue = entry_venue(entry)
    doi = str(entry.get("doi", "")).strip()
    url = str(entry.get("url", "")).strip()
    archive_prefix = str(entry.get("archivePrefix", entry.get("archiveprefix", ""))).lower()
    eprint = str(entry.get("eprint", "")).strip()
    categories = entry_categories(key)
    cited = key in cited_keys
    metadata = ReferenceMetadata(status="MISSING")
    doi_status = "MISSING"
    url_status = "NOT_REQUIRED"
    issues: list[str] = []
    recommendations: list[str] = []

    if doi:
        metadata = crossref_doi_lookup(doi)
        doi_status = metadata.status
        if metadata.status == "FOUND":
            sim = title_similarity(title, metadata.title)
            year_match = years_match(year, metadata.year)
            if not title_match_acceptable(title, metadata.title):
                issues.append("DOI_TITLE_MISMATCH")
                recommendations.append("Verify DOI/title manually before submission.")
            if not year_match:
                issues.append("DOI_YEAR_MISMATCH")
                recommendations.append("Check print vs online-first year.")
        elif metadata.status == "VERIFY_TIMEOUT":
            issues.append("DOI_VERIFY_TIMEOUT")
            recommendations.append("Rerun audit or manually verify DOI.")
        else:
            issues.append("DOI_NOT_FOUND")
            recommendations.append("Check DOI string or replace citation.")
    elif archive_prefix == "arxiv" or eprint:
        arxiv_meta = arxiv_lookup(eprint)
        peer_meta = crossref_title_lookup(title)
        metadata = peer_meta if peer_meta.status == "FOUND" else arxiv_meta
        doi_status = "ARXIV_ONLY"
        if peer_meta.status == "FOUND" and peer_meta.doi and title_match_acceptable(title, peer_meta.title):
            issues.append("ARXIV_HAS_PEER_REVIEWED_ALTERNATIVE")
            recommendations.append(f"Consider replacing/augmenting with DOI {peer_meta.doi}.")
            doi_status = "PEER_REVIEWED_ALTERNATIVE_FOUND"
        elif arxiv_meta.status == "FOUND":
            issues.append("ARXIV_ONLY_ACCEPTABLE_IF_CANONICAL")
            recommendations.append("Keep only if this is the canonical source for the model/protocol.")
        elif arxiv_meta.status == "VERIFY_TIMEOUT" or peer_meta.status == "VERIFY_TIMEOUT":
            issues.append("ARXIV_VERIFY_TIMEOUT")
            recommendations.append("Rerun arXiv/Crossref verification.")
    elif entry_type in PEER_REVIEWED_TYPES:
        metadata = crossref_title_lookup(title)
        if metadata.status == "FOUND" and metadata.doi and title_match_acceptable(title, metadata.title):
            doi_status = "MISSING_DOI"
            issues.append("MISSING_DOI")
            recommendations.append(f"Add DOI {metadata.doi}.")
        elif metadata.status == "VERIFY_TIMEOUT":
            doi_status = "VERIFY_TIMEOUT"
            issues.append("TITLE_VERIFY_TIMEOUT")
            recommendations.append("Rerun Crossref title search.")
        elif url:
            url_status = url_lookup(url)
            if url_status == "OK":
                doi_status = "NO_DOI_URL_VERIFIED"
                recommendations.append("No DOI found; canonical proceedings URL verified.")
            else:
                doi_status = "MISSING"
                issues.append(f"URL_{url_status}")
                recommendations.append("Verify proceedings URL or add DOI if available.")
        else:
            doi_status = "MISSING"
            issues.append("MISSING_DOI_OR_WEAK_SOURCE")
            recommendations.append("Add DOI or stronger peer-reviewed citation if available.")
    else:
        doi_status = "NOT_REQUIRED"

    if entry_type in REPORT_OR_DOC_TYPES and not doi and not (archive_prefix == "arxiv" or eprint):
        if entry_type == "book" and entry.get("publisher"):
            url_status = "NOT_REQUIRED"
        else:
            url_status = url_lookup(url) if url else "MISSING_URL"
            if url_status != "OK":
                issues.append(url_status)
                recommendations.append("Verify URL for report/documentation source.")

    sim = title_similarity(title, metadata.title)
    venue_sim = venue_similarity(venue, metadata.venue)
    year_match = years_match(year, metadata.year)
    venue_match = bool(venue and metadata.venue and venue_sim >= 0.70)
    if not cited:
        issues.append("UNUSED_ENTRY")

    audit_status = classify_status(issues, cited=cited, doi_status=doi_status)
    if not recommendations:
        recommendations.append("No action required.")

    return {
        "key": key,
        "entry_type": entry_type,
        "cited": bool(cited),
        "title": title,
        "bib_year": year,
        "bib_venue": venue,
        "bib_doi": doi,
        "doi_status": doi_status,
        "crossref_title": metadata.title,
        "crossref_year": metadata.year,
        "crossref_venue": metadata.venue,
        "title_similarity": round(sim, 4),
        "year_match": bool(year_match) if metadata.year else False,
        "venue_match": bool(venue_match),
        "url_status": url_status,
        "category": ";".join(categories),
        "audit_status": audit_status,
        "issue": ";".join(dict.fromkeys(issues)),
        "recommendation": " ".join(dict.fromkeys(recommendations)),
    }


def years_match(left: str, right: str) -> bool:
    try:
        if not left or not right:
            return False
        return abs(int(str(left)[:4]) - int(str(right)[:4])) <= 1
    except ValueError:
        return False


def classify_status(issues: list[str], *, cited: bool, doi_status: str) -> str:
    issue_set = set(issues)
    if any(issue.endswith("VERIFY_TIMEOUT") or issue == "TITLE_VERIFY_TIMEOUT" for issue in issue_set):
        return "VERIFY_TIMEOUT"
    hard_issues = {
        "DOI_TITLE_MISMATCH",
        "DOI_YEAR_MISMATCH",
        "DOI_NOT_FOUND",
        "MISSING_DOI",
        "MISSING_DOI_OR_WEAK_SOURCE",
        "ARXIV_HAS_PEER_REVIEWED_ALTERNATIVE",
        "MISSING_URL",
    }
    if issue_set & hard_issues:
        return "QUESTIONABLE"
    if "ARXIV_ONLY_ACCEPTABLE_IF_CANONICAL" in issue_set:
        return "ARXIV_ONLY"
    if not cited:
        return "UNUSED"
    return "PASS"


def build_coverage(audit: pd.DataFrame, cited_keys: set[str]) -> pd.DataFrame:
    rows = []
    for category, rule in COVERAGE_RULES.items():
        keys = set(rule["keys"])
        present = sorted(keys.intersection(set(audit["key"].astype(str))))
        cited = sorted(keys.intersection(cited_keys))
        rows.append(
            {
                "category": category,
                "label": rule["label"],
                "required_or_recommended_keys": ",".join(sorted(keys)),
                "present_keys": ",".join(present),
                "cited_keys": ",".join(cited),
                "status": "PASS" if cited else ("PRESENT_NOT_CITED" if present else "MISSING_CANONICAL"),
                "recommendation": "No action required." if cited else f"Add/cite a canonical source for {rule['label']}.",
            }
        )
    return pd.DataFrame(rows)


def write_reference_audit_doc(path: Path, audit: pd.DataFrame, coverage: pd.DataFrame, *, run_id: str) -> None:
    counts = audit["audit_status"].value_counts().to_dict() if not audit.empty else {}
    coverage_missing = coverage[coverage["status"].astype(str).ne("PASS")]

    def rows_for(status: str) -> list[str]:
        subset = audit[audit["audit_status"].astype(str).eq(status)]
        if subset.empty:
            return ["- Khong co."]
        return [
            f"- `{row.key}` ({row.entry_type}, cited={row.cited}): {row.issue or 'no issue'}; {row.recommendation}"
            for row in subset.itertuples(index=False)
        ]

    lines = [
        "# Reference audit P1-12",
        "",
        f"- `run_id`: `{run_id}`",
        "- Muc tieu: kiem tra DOI/title/venue/year, arXiv-only risk, URL/report sources, va coverage citation canonical.",
        "- Pham vi: `Paper_ICDM_2026/custom.bib` va cite keys trong `main.tex`.",
        "",
        "## Summary",
        "",
        f"- Total entries: `{len(audit)}`.",
        f"- Cited entries: `{int(audit['cited'].sum()) if not audit.empty else 0}`.",
        f"- PASS: `{int(counts.get('PASS', 0))}`.",
        f"- QUESTIONABLE: `{int(counts.get('QUESTIONABLE', 0))}`.",
        f"- ARXIV_ONLY: `{int(counts.get('ARXIV_ONLY', 0))}`.",
        f"- VERIFY_TIMEOUT: `{int(counts.get('VERIFY_TIMEOUT', 0))}`.",
        f"- UNUSED: `{int(counts.get('UNUSED', 0))}`.",
        "",
        "## Missing or weak coverage",
        "",
    ]
    if coverage_missing.empty:
        lines.append("- Khong co category canonical bi thieu citation.")
    else:
        for row in coverage_missing.itertuples(index=False):
            lines.append(f"- `{row.category}` `{row.status}`: {row.recommendation}")

    lines.extend(["", "## QUESTIONABLE", "", *rows_for("QUESTIONABLE")])
    lines.extend(["", "## ARXIV_ONLY", "", *rows_for("ARXIV_ONLY")])
    lines.extend(["", "## VERIFY_TIMEOUT", "", *rows_for("VERIFY_TIMEOUT")])
    lines.extend(["", "## UNUSED", "", *rows_for("UNUSED")])
    lines.extend(
        [
            "",
            "## Principal ML Scientist view",
            "",
            "Coverage citation hien co bao phu cac truc quan trong: FI-2010, DeepLOB, LOB benchmark, market microstructure, crypto microstructure, time-series validation, bootstrap va backtest-overfitting. Dataset documentation phai duoc cite ro de reviewer truy vet nguon L2 snapshots.",
            "",
            "## Reviewer ICDM view",
            "",
            "Truoc submission, nen review cac entry QUESTIONABLE, ARXIV_ONLY va UNUSED. ARXIV_ONLY co the chap nhan neu la nguon canonical; UNUSED co the giu trong draft nhung nen prune neu khong con duoc cite.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_reference_audit(root: Path, bib_path: Path, tex_path: Path, *, run_id: str) -> dict[str, Path]:
    bib_text = bib_path.read_text(encoding="utf-8")
    tex_text = tex_path.read_text(encoding="utf-8")
    entries = parse_bib_entries(bib_text)
    cited_keys = extract_cite_keys(tex_text)
    rows = [audit_entry(entry, cited_keys) for entry in entries]
    audit = pd.DataFrame(rows)
    coverage = build_coverage(audit, cited_keys)
    summary = (
        audit.groupby("audit_status", dropna=False)
        .size()
        .reset_index(name="n_entries")
        .sort_values("audit_status")
    )
    artifacts = root / "artifacts"
    docs = root / "docs"
    paper_assets = root / "outputs" / "paper_assets"
    logs = root / "outputs" / "logs" / run_id
    artifacts.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    paper_assets.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    paths = {
        "reference_audit": artifacts / "reference_audit.csv",
        "reference_coverage": artifacts / "reference_coverage.csv",
        "paper_summary": paper_assets / "table_28_reference_audit_summary.csv",
        "audit_doc": docs / "reference_audit.md",
        "metadata": logs / "metadata.json",
    }
    audit.to_csv(paths["reference_audit"], index=False)
    coverage.to_csv(paths["reference_coverage"], index=False)
    summary.to_csv(paths["paper_summary"], index=False)
    write_reference_audit_doc(paths["audit_doc"], audit, coverage, run_id=run_id)
    metadata = {
        "run_id": run_id,
        "script": "27_build_reference_audit.py",
        "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(),
        "bib_path": str(bib_path),
        "tex_path": str(tex_path),
        "n_entries": int(len(audit)),
        "n_cited": int(audit["cited"].sum()) if not audit.empty else 0,
        "artifacts": {key: str(value) for key, value in paths.items() if key != "metadata"},
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build bibliography/reference audit for the ICDM paper.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--bib", default=str(root / "Paper_ICDM_2026" / "custom.bib"))
    parser.add_argument("--tex", default=str(root / "Paper_ICDM_2026" / "main.tex"))
    parser.add_argument("--run-id", default="p1_12_reference_audit_v001")
    parser.add_argument("--rate-limit-seconds", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.rate_limit_seconds > 0:
        original_crossref_by_doi = crossref_by_doi
        original_crossref_by_title = crossref_by_title

        def delayed_doi(doi: str) -> ReferenceMetadata:
            time.sleep(args.rate_limit_seconds)
            return original_crossref_by_doi(doi)

        def delayed_title(title: str) -> ReferenceMetadata:
            time.sleep(args.rate_limit_seconds)
            return original_crossref_by_title(title)

        globals()["crossref_by_doi"] = delayed_doi
        globals()["crossref_by_title"] = delayed_title
    paths = build_reference_audit(root, Path(args.bib), Path(args.tex), run_id=args.run_id)
    print(f"Wrote reference audit artifacts: {paths}")


if __name__ == "__main__":
    main()
