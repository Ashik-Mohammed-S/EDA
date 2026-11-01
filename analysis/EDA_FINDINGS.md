# Bank campaign — full-variable findings

Analyzed 45,181 target-labeled records. Positive target count: 5,287; observed rate: 11.702%. Profiled 19 raw source columns and 22 analytical variables.

## Quality checks

- 30 records without a yes/no target are excluded; age/month missingness is retained.
- No outliers or unknown categories are dropped or imputed.
- Duration is post-contact; all associations are descriptive.

Highest raw-source missingness (original populations; no automatic column dropping):

| Source | Column | Missing | Missing % |
| --- | --- | --- | --- |
| bank_source | month | 50 | 0.11% |
| bank_source | response | 30 | 0.07% |
| bank_source | age | 20 | 0.04% |
| bank_source | salary | 0 | 0.00% |
| bank_source | customerid | 0 | 0.00% |
| bank_source | balance | 0 | 0.00% |
| bank_source | marital | 0 | 0.00% |
| bank_source | default | 0 | 0.00% |
| bank_source | housing | 0 | 0.00% |
| bank_source | jobedu | 0 | 0.00% |

Duration mixes seconds and minutes and is normalized to seconds. It is a post-contact diagnostic, not a pre-contact decision feature. Pdays=-1 is not previously contacted; only the derived elapsed-days field masks that sentinel.

## Variable-level comparisons

Numeric target-group summaries include exact count, mean, standard deviation, median, quartiles, tail percentiles and range in numeric_by_target.csv. Missing, unknown and IQR-flagged values are retained and visible.

Leading binned associations (not ranked causal drivers or predictive validation):

| Variable | Binned Cramér’s V | Point-biserial r | Missing fraction |
| --- | --- | --- | --- |
| duration_seconds | 0.403 | 0.395 | 0.000 |
| poutcome | 0.312 | — | 0.000 |
| source_month | 0.260 | — | 0.001 |
| month | 0.260 | — | 0.001 |
| pdays_since_contact | 0.245 | -0.152 | 0.817 |
| pdays | 0.179 | 0.104 | 0.000 |
| previous | 0.169 | 0.093 | 0.000 |
| prior_contact | 0.167 | — | 0.000 |
| age_band | 0.160 | — | 0.000 |
| contact | 0.151 | — | 0.000 |

Examples of higher observed rates among sufficiently populated categorical groups (all groups remain in the full export):

| Variable | Group | n | Positive | Rate | 95% Wilson |
| --- | --- | --- | --- | --- | --- |
| poutcome | success | 1,510 | 978 | 64.77% | 62.32% – 67.14% |
| job | student | 938 | 269 | 28.68% | 25.88% – 31.65% |
| job | retired | 2,263 | 516 | 22.80% | 21.12% – 24.58% |
| housing | no | 20,069 | 3,353 | 16.71% | 16.20% – 17.23% |
| poutcome | other | 1,839 | 307 | 16.69% | 15.06% – 18.47% |
| job | unemployed | 1,303 | 202 | 15.50% | 13.64% – 17.57% |
| education | tertiary | 13,292 | 1,995 | 15.01% | 14.41% – 15.63% |
| contact | cellular | 29,267 | 4,367 | 14.92% | 14.52% – 15.33% |
| job | management | 9,454 | 1,301 | 13.76% | 13.08% – 14.47% |
| education | unknown | 1,856 | 252 | 13.58% | 12.09% – 15.21% |
| contact | telephone | 2,904 | 390 | 13.43% | 12.24% – 14.72% |
| poutcome | failure | 4,897 | 618 | 12.62% | 11.72% – 13.58% |

These are unadjusted historical associations. Small groups, correlated features, missingness, selection and multiple comparisons limit interpretation. Do not use these tables as lending eligibility rules or claims of campaign uplift. Correlation views are pairwise complete and scoped to selected continuous fields.

The interactive dashboard retains full denominators under its four cohort filters. Numeric bounds and category grouping are fixed globally. Raw source audits and correlation matrices remain full-cohort and are labeled accordingly.

