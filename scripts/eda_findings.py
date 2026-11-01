from pathlib import Path
import pandas as pd,json

def write_findings(root,project):
    root=Path(root);out=root/'results';report=json.loads((out/'analysis.json').read_text(encoding='utf-8'))
    profile=pd.read_csv(out/'all_source_variable_profiles.csv');segments=pd.read_csv(out/'target_summary.csv');numeric=pd.read_csv(out/'numeric_by_target.csv');association=pd.read_csv(out/'variable_associations.csv')
    text='# '+('Bank campaign' if project=='bank' else 'Credit application')+' — full-variable findings\n\n'
    text+=f"Analyzed {report['rows']:,} target-labeled records. Positive target count: {report['metrics']['positive_records']:,}; observed rate: {report['metrics']['target_rate']:.3%}. Profiled {len(profile)} raw source columns and {report['metrics']['analyzed_variables']} analytical variables.\n\n"
    text+='## Quality checks\n\n'
    for note in report['data_quality']['quality_notes']:text+='- '+note+'\n'
    text+='\nHighest raw-source missingness (original populations; no automatic column dropping):\n\n| Source | Column | Missing | Missing % |\n| --- | --- | --- | --- |\n'
    for r in profile.sort_values('missing_pct',ascending=False).head(10).itertuples():text+=f'| {r.table} | {r.variable} | {r.missing:,} | {r.missing_pct:.2f}% |\n'
    if project=='credit':
        sentinel=profile.loc[(profile.variable=='DAYS_EMPLOYED')&(profile.table=='current_application_source'),'sentinel_365243'].iloc[0]
        text+=f'\nThe current employment-day field contains {int(sentinel):,} instances of sentinel 365243. These applicants remain in the cohort; sentinel-aware analytical employment fields are missing. Source XNA/unknown categories are not reassigned to the majority group.\n'
    else:text+='\nDuration mixes seconds and minutes and is normalized to seconds. It is a post-contact diagnostic, not a pre-contact decision feature. Pdays=-1 is not previously contacted; only the derived elapsed-days field masks that sentinel.\n'
    text+='\n## Variable-level comparisons\n\nNumeric target-group summaries include exact count, mean, standard deviation, median, quartiles, tail percentiles and range in numeric_by_target.csv. Missing, unknown and IQR-flagged values are retained and visible.\n\nLeading binned associations (not ranked causal drivers or predictive validation):\n\n| Variable | Binned Cramér’s V | Point-biserial r | Missing fraction |\n| --- | --- | --- | --- |\n'
    for r in association.head(10).itertuples():
        correlation=f'{r.point_biserial_r:.3f}' if pd.notna(r.point_biserial_r) else '—'
        text+=f'| {r.variable} | {r.binned_cramers_v:.3f} | {correlation} | {r.missing_fraction:.3f} |\n'
    examples=['job','education','poutcome','housing','contact'] if project=='bank' else ['NAME_EDUCATION_TYPE','NAME_INCOME_TYPE','OCCUPATION_TYPE','NAME_CONTRACT_TYPE','previous_history']
    shown=segments.loc[segments.variable.isin(examples)&(segments.observations>=(200 if project=='bank' else 1000))].sort_values('target_rate',ascending=False).head(12)
    text+='\nExamples of higher observed rates among sufficiently populated categorical groups (all groups remain in the full export):\n\n| Variable | Group | n | Positive | Rate | 95% Wilson |\n| --- | --- | --- | --- | --- | --- |\n'
    for r in shown.itertuples():text+=f'| {r.variable} | {r.group} | {r.observations:,} | {r.positive:,} | {r.target_rate:.2%} | {r.ci95_low:.2%} – {r.ci95_high:.2%} |\n'
    text+='\nThese are unadjusted historical associations. Small groups, correlated features, missingness, selection and multiple comparisons limit interpretation. Do not use these tables as lending eligibility rules or claims of campaign uplift. Correlation views are pairwise complete and scoped to selected continuous fields.\n\nThe interactive dashboard retains full denominators under its four cohort filters. Numeric bounds and category grouping are fixed globally. Raw source audits and correlation matrices remain full-cohort and are labeled accordingly.\n'
    (out/'EDA_FINDINGS.md').write_text(text,encoding='utf-8')
    return text

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--project',required=True);a=p.parse_args();write_findings(a.root,a.project)
