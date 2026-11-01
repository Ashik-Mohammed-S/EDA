# Expanded exploratory analysis and dashboard

[Open the published Analytics Lens workspace](https://ashik-analytics-lens.swoonysnipe19.chatgpt.site). The hosted workspace includes both bank and credit projects. It starts owner-private and may require ChatGPT sign-in.

Coverage for this repository: 19 source columns and 22 analytical variables over 45,181 valid-target records. Original datasets and historical walkthroughs remain intact.

## Run and reproduce

Use the Python version in .python-version:

```sh
python -m pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/run_notebook.py --mode full
python -m unittest discover -s tests
python scripts/check_dashboard.py
python -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000/dashboard/. The local repository dashboard contains this dataset only; the published shared workspace includes both. The parity check requires Node. Both notebook modes use the full descriptive population, without sampling.

## Analysis outputs

- results/all_source_variable_profiles.csv: every original column's type, population, missingness, unique values, unknown markers and numeric descriptions. Identifiers and targets are audited but excluded from explanatory charts.
- results/numeric_by_target.csv: target-specific counts, mean, sample standard deviation, quantiles, range and tails for numeric analytical fields.
- results/target_summary.csv: every variable/bin/category, denominator, positive/negative counts, observed target rate, Wilson 95% interval and lift versus the overall rate.
- results/variable_associations.csv: binned Cramér's V and numeric point-biserial correlation. These are exploratory associations, not adjusted drivers or predictive validation.
- results/correlation_pearson.csv and correlation_spearman.csv: pairwise complete correlations for documented domain-selected continuous fields, not every possible column pair.
- results/EDA_FINDINGS.md and generated PNG figures: interpretable source-quality and variable-level findings.

A checked-in findings snapshot is in analysis/EDA_FINDINGS.md. Regenerated outputs are written to results/. Dashboard data is a compressed aggregate snapshot in dashboard/bank.json.gz, with SHA-256 and population counts in dashboard/manifest.json.

## Dynamic dashboard behavior

Four cohort filters recompute record counts, positive counts, rates, Wilson intervals, variable distributions, means, sample deviations, missingness and selected variable-pair tables. Export buttons save the currently selected cohort/variable table. Numeric bin boundaries are fixed full-cohort quantiles (up to 12 bins); categorical variables with more than 29 levels use the 29 most frequent levels plus an explicit Other group. Missing values have their own bin. All denominators are conserved.

Correlation panels and raw-source audits are explicitly full-population views and do not recompute when cohort filters change. The credit history panels also use full original/linked populations, with clear labels. The dashboard contains aggregate strata and moments only, not customer/applicant identifiers or individual rows.

## Data treatment and interpretation

Thirty records without a yes/no response are counted and excluded; missing ages/months and unknown categories remain. The mixed min/sec duration field is normalized to seconds and labeled post-contact. Pdays=-1 denotes no previous contact, not an ordinary elapsed-day value; only the derived elapsed-days field masks it. Salary is supplied source data, not independently validated income.

Outliers are retained. IQR flags are computed where the full-cohort IQR is nonzero; a flag does not mean an observation is erroneous. Descriptive intervals do not adjust for confounding, selection, repeated observations or multiple comparisons. Small groups are muted/flagged, not hidden. Do not interpret associations as causal effects, campaign uplift, lending eligibility rules or deployed prediction quality.

## Verification and publication

The builder asserts count and positive-count conservation for every variable and every pair. JavaScript/Python parity tests compare eight cohorts, including an empty cohort, with direct Python reference counts and means. The source datasets remain checksum-verified and restorable offline; fresh package installation needs network access. CI executes the full notebook, normalization tests, artifact integrity and browser-engine parity.

The published Site is a historical snapshot, not a live data connection. Regenerate the notebook outputs, inspect the findings, update the aggregate artifact and republish the Site after source/method changes. The underlying source terms and provenance remain in DATA.md and dataset-sources.json.

