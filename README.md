# Bank Campaign Response EDA

[![Validation](https://github.com/Ashik-Mohammed-S/EDA/actions/workflows/validate.yml/badge.svg)](https://github.com/Ashik-Mohammed-S/EDA/actions/workflows/validate.yml)

Understand subscription response rates across campaign segments while retaining the denominator behind every rate.

Independent public portfolio work; historical educational notebooks remain under `historical/`. The current implementation and results described here take precedence over historical in-sample numbers.

## Data and approach

45,211 source records; 45,181 records with valid yes/no response labels are analyzed.

Summarize response rates by job, education, marital status, loan/housing status and previous outcome. Treat call duration as a post-contact diagnostic rather than an available pre-contact predictor.

## Current full-data result

| Measure | Current analysis | Baseline where applicable |
| --- | --- | --- |
| Analyzed records | 45,181 | — |
| Positive responses | 5,287 | — |
| Observed response rate | 11.702% | — |

Results are specific to the documented dataset and split. See generated `results/analysis.json` after execution for full metrics and assumptions.

## Run locally

Use the Python version in `.python-version`, then:

```sh
python -m pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/run_notebook.py --mode full
```

Reference data is committed under `dataset/`, directly or as reconstructable compressed parts. The downloader verifies checksums and restores stored data offline. See [DATA.md](DATA.md) and [dataset-sources.json](dataset-sources.json) for provenance and upstream terms. Package installation and the spaCy model, where needed, require network access on a fresh machine.

## Review the implementation

Inspect target filtering, group denominators and the distinction between pre-contact and post-contact information. Start with [scripts/analysis.py](scripts/analysis.py), then the root notebook. The workflow validates dependencies, smoke checks and full-data notebook execution with dataset downloads disabled.

## Limitations

This is target-conditioned descriptive EDA. Segment associations are not treatment effects; no predictive accuracy or causal campaign uplift is claimed.

[Method notes](ANALYSIS.md) · [All portfolio projects](https://github.com/Ashik-Mohammed-S/Ashik-Mohammed-S/blob/main/PORTFOLIO.md)
