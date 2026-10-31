# Recovered data and execution

The public copies below match the filenames and schemas used by this notebook.
Original lost-file byte identity cannot be proved. URLs are pinned to source commits,
and SHA-256 checksums in dataset-sources.json prevent silent source changes.
Data is downloaded locally rather than added as new dataset blobs in this PR.

| File | Rows / tokens | Source |
| --- | --- | --- |
| `bank_marketing_updated_v1.csv` | 45211 | [Pinned source](https://raw.githubusercontent.com/izharul-haque/Bank-Telemarketing-Campaign-Case/ba8894fdacef08528847a91790b3e67002e3ca46/bank_marketing_updated_v1.csv) |

Source repository license metadata: No explicit repository license was reported; data is restored by download and no new redistribution license is granted.

```sh
python -m pip install -r requirements.txt
python scripts/fetch_data.py
python scripts/run_notebook.py --mode quick
python -m jupyterlab
```

Install the spaCy English model first where used: `python -m spacy download en_core_web_sm`.
The notebook also restores missing reference files automatically when run from the repository root.
Set DATA_DIR to use another directory containing these same reference files.
Existing files with a different checksum are left untouched and reported as mismatches.

Both modes use all recovered rows and the original training/analysis workload. Full experiments are available with `--mode full`, or set RUN_MODE=full before
launching the notebook. Quick results demonstrate execution; they do not reproduce
the historical trained-model quality. The runner writes results/execution-report.json.

