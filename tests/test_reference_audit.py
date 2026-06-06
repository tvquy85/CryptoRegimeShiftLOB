from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "27_build_reference_audit.py"
    spec = importlib.util.spec_from_file_location("reference_audit", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bib_parser_handles_optional_code_fence() -> None:
    module = _load_script_module()
    text = """```bibtex
@article{demo,
  title={A Good Title},
  author={Doe, Jane},
  journal={Journal},
  year={2024},
  doi={10.0000/demo}
}
```"""

    entries = module.parse_bib_entries(text)

    assert len(entries) == 1
    assert entries[0]["ID"] == "demo"


def test_doi_metadata_match_passes() -> None:
    module = _load_script_module()
    entry = {
        "ID": "demo",
        "ENTRYTYPE": "article",
        "title": "A Good Title",
        "journal": "Journal of Tests",
        "year": "2024",
        "doi": "10.0000/demo",
    }

    row = module.audit_entry(
        entry,
        {"demo"},
        crossref_doi_lookup=lambda doi: module.ReferenceMetadata(
            title="A Good Title",
            year="2024",
            venue="Journal of Tests",
            doi=doi,
            status="FOUND",
        ),
    )

    assert row["audit_status"] == "PASS"
    assert row["doi_status"] == "FOUND"
    assert row["title_similarity"] >= 0.99


def test_doi_title_mismatch_is_questionable() -> None:
    module = _load_script_module()
    entry = {
        "ID": "demo",
        "ENTRYTYPE": "article",
        "title": "A Good Title",
        "journal": "Journal of Tests",
        "year": "2024",
        "doi": "10.0000/demo",
    }

    row = module.audit_entry(
        entry,
        {"demo"},
        crossref_doi_lookup=lambda doi: module.ReferenceMetadata(
            title="A Different Paper",
            year="2024",
            venue="Journal of Tests",
            doi=doi,
            status="FOUND",
        ),
    )

    assert row["audit_status"] == "QUESTIONABLE"
    assert "DOI_TITLE_MISMATCH" in row["issue"]


def test_doi_short_crossref_title_with_bibtex_subtitle_passes() -> None:
    module = _load_script_module()
    entry = {
        "ID": "xgboost",
        "ENTRYTYPE": "inproceedings",
        "title": "{XGBoost}: A Scalable Tree Boosting System",
        "booktitle": "Proceedings of KDD",
        "year": "2016",
        "doi": "10.1145/2939672.2939785",
    }

    row = module.audit_entry(
        entry,
        {"xgboost"},
        crossref_doi_lookup=lambda doi: module.ReferenceMetadata(
            title="XGBoost",
            year="2016",
            venue="Proceedings of KDD",
            doi=doi,
            status="FOUND",
        ),
    )

    assert row["audit_status"] == "PASS"
    assert "DOI_TITLE_MISMATCH" not in row["issue"]


def test_missing_doi_article_with_crossref_match_is_flagged() -> None:
    module = _load_script_module()
    entry = {
        "ID": "demo",
        "ENTRYTYPE": "article",
        "title": "A Good Title",
        "journal": "Journal of Tests",
        "year": "2024",
    }

    row = module.audit_entry(
        entry,
        {"demo"},
        crossref_title_lookup=lambda title: module.ReferenceMetadata(
            title="A Good Title",
            year="2024",
            venue="Journal of Tests",
            doi="10.0000/demo",
            status="FOUND",
        ),
    )

    assert row["audit_status"] == "QUESTIONABLE"
    assert row["doi_status"] == "MISSING_DOI"
    assert "Add DOI 10.0000/demo" in row["recommendation"]


def test_peer_reviewed_proceedings_without_doi_can_pass_with_verified_url() -> None:
    module = _load_script_module()
    entry = {
        "ID": "pmlr_demo",
        "ENTRYTYPE": "inproceedings",
        "title": "A Good Proceedings Paper",
        "booktitle": "Proceedings of Machine Learning Research",
        "year": "2021",
        "url": "https://proceedings.mlr.press/v1/demo.html",
    }

    row = module.audit_entry(
        entry,
        {"pmlr_demo"},
        crossref_title_lookup=lambda title: module.ReferenceMetadata(status="NOT_FOUND"),
        url_lookup=lambda url: "OK",
    )

    assert row["audit_status"] == "PASS"
    assert row["doi_status"] == "NO_DOI_URL_VERIFIED"


def test_arxiv_peer_reviewed_alternative_is_flagged() -> None:
    module = _load_script_module()
    entry = {
        "ID": "demo",
        "ENTRYTYPE": "misc",
        "title": "A Good Preprint",
        "year": "2024",
        "archivePrefix": "arXiv",
        "eprint": "2401.00001",
    }

    row = module.audit_entry(
        entry,
        {"demo"},
        arxiv_lookup=lambda eprint: module.ReferenceMetadata(title="A Good Preprint", year="2024", venue="arXiv", status="FOUND"),
        crossref_title_lookup=lambda title: module.ReferenceMetadata(
            title="A Good Preprint",
            year="2025",
            venue="Journal of Tests",
            doi="10.0000/peer",
            status="FOUND",
        ),
    )

    assert row["audit_status"] == "QUESTIONABLE"
    assert "ARXIV_HAS_PEER_REVIEWED_ALTERNATIVE" in row["issue"]


def test_arxiv_only_without_peer_match_is_canonical_flag() -> None:
    module = _load_script_module()
    entry = {
        "ID": "demo",
        "ENTRYTYPE": "misc",
        "title": "A Good Preprint",
        "year": "2024",
        "archivePrefix": "arXiv",
        "eprint": "2401.00001",
    }

    row = module.audit_entry(
        entry,
        {"demo"},
        arxiv_lookup=lambda eprint: module.ReferenceMetadata(title="A Good Preprint", year="2024", venue="arXiv", status="FOUND"),
        crossref_title_lookup=lambda title: module.ReferenceMetadata(status="NOT_FOUND"),
    )

    assert row["audit_status"] == "ARXIV_ONLY"
    assert "ARXIV_ONLY_ACCEPTABLE_IF_CANONICAL" in row["issue"]


def test_arxiv_lookup_falls_back_to_abs_page(monkeypatch) -> None:
    module = _load_script_module()

    def fake_get(url, **kwargs):
        response = Mock()
        if "export.arxiv.org" in url:
            raise module.requests.Timeout("api timeout")
        response.text = (
            '<meta name="citation_title" content="A Good Preprint">'
            '<meta name="citation_date" content="2018/03/01">'
        )
        response.raise_for_status = Mock()
        return response

    monkeypatch.setattr(module.requests, "get", fake_get)

    meta = module.arxiv_by_id("1803.01271", timeout=0.1)

    assert meta.status == "FOUND"
    assert meta.source == "arxiv_abs"
    assert meta.title == "A Good Preprint"
    assert meta.year == "2018"


def test_coverage_requires_dataset_documentation() -> None:
    module = _load_script_module()
    entries = [
        {"key": "ntakaris2018benchmark"},
        {"key": "deeplob2019"},
        {"key": "madhavan2000microstructure"},
    ]
    import pandas as pd

    coverage = module.build_coverage(pd.DataFrame(entries), {"ntakaris2018benchmark", "deeplob2019", "madhavan2000microstructure"})
    dataset = coverage[coverage["category"] == "dataset_documentation"].iloc[0]
    assert dataset["status"] == "MISSING_CANONICAL"

    entries.append({"key": "cryptolake_data"})
    coverage = module.build_coverage(
        pd.DataFrame(entries),
        {"ntakaris2018benchmark", "deeplob2019", "madhavan2000microstructure", "cryptolake_data"},
    )
    dataset = coverage[coverage["category"] == "dataset_documentation"].iloc[0]
    assert dataset["status"] == "PASS"
