# Data cleaning pipeline

Pure-Python (stdlib only, no pandas) reproducible pipeline for the e-commerce
dirty dataset described in `../README.txt`.

## Layout

```
pipeline/
  raw/                     copy of the original CSVs (never modified)
  clean/                   output: analysis-ready CSVs
  rejects/                 output: quarantined rows with reject_reason
  reports/                 output: profiling / cleaning / validation reports
  common.py                shared cleaning helpers (date parsing, lookups...)
  01_profile.py            profiles the RAW data (missingness, formats, FK checks...)
  02_investigate.py        deeper investigation of specific anomalies found in step 1
  03_clean.py              THE pipeline: raw/ -> clean/ + rejects/ + cleaning_log.md
  04_validate.py           re-runs quality checks on clean/ vs raw/, before/after report
```

## How to run

```bash
cd pipeline
python3 01_profile.py      # optional: regenerate the raw-data profile
python3 02_investigate.py  # optional: regenerate the deep-dive investigation
python3 03_clean.py        # required: runs the cleaning pipeline
python3 04_validate.py     # required: before/after quality comparison
```

Everything is deterministic and idempotent — running `03_clean.py` again
reproduces the same `clean/` and `rejects/` output from `raw/`.

## Key documents

- `reports/data_quality_issues.md` — full issue catalog classified by DAMA
  dimension (Completeness, Uniqueness, Validity, Consistency, Accuracy,
  Integrity), with the reasoning behind every cleaning decision.
- `reports/cleaning_log.md` — machine-generated log of exactly what
  `03_clean.py` did and how many rows/values each rule affected.
- `reports/validation_before_after.txt` — quality metrics computed on
  `raw/` vs `clean/`.

## Design principles followed (per README.txt instructions)

1. Raw CSVs are never edited by hand or in place — `clean/` is always
   regenerated from `raw/` by the script.
2. A value is only changed/removed when there is an explicit, documented
   reason tied to a stated business rule or an unambiguous data error.
3. Genuinely ambiguous cases (e.g. `DD/MM/YYYY` vs `MM/DD/YYYY` when both
   readings are valid) are resolved with a clearly documented assumption and
   flagged in an audit column, not silently guessed.
4. Rows that fail referential-integrity or business-rule checks are
   quarantined into `rejects/` with a reason, not silently dropped —
   nothing is deleted from the record without a trace.
