# Comprehensive exploratory analysis

The primary notebook now covers source quality, all-variable profiles, numeric
target-group summaries, categorical rates with denominators and Wilson intervals,
IQR flags, selected bivariate relationships and correlations. No descriptive
population sampling or blanket outlier deletion is performed.

See [DASHBOARD.md](DASHBOARD.md) for the published/local interactive dashboard,
field transformations, population units, scope boundaries and exact run commands.
The [analysis snapshots](analysis/) are readable without rerunning the notebook;
regenerated tables and charts are written to results/.

The bank analysis has 22 analytical variables and profiles all 19 source columns.
The credit analysis has 137 current-applicant analytical variables and profiles
all 122 current and 37 previous source columns. Previous history is aggregated
before joining, and category-presence rates deduplicate applicant/category pairs.

Missing and unknown groups remain visible. Numeric bin boundaries are fixed full-
cohort quantiles. Correlations and raw-source/history audit views are full-cohort
statistics, explicitly unaffected by dashboard cohort filters. Associations are
descriptive, not causal effects, uplift, lending rules or predictive validation.

The earlier educational walkthroughs remain under historical/ for reference.
