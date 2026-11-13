# Endometriosis Risk Prediction — Two-Tier Pipeline

A machine learning project to help close the gap between a person noticing
symptoms at home and getting seen at a hospital. Instead of one model, this
uses a **two-tier pipeline** so the tool is honest about what it can and
can't tell from symptoms alone:

- **Tier 1 — instant, free, home-only.** A quick symptom questionnaire
  (pain scores, cycle history, family history, infertility status, BMI)
  gives an immediate risk flag. No test kit or lab required.
- **Tier 2 — few-day turnaround, still no hospital visit.** If Tier 1
  flags elevated risk, the person is told to order a low-cost **mail-in
  finger-prick kit** for CA-125 and CRP (both real, consumer-available,
  self-collected blood tests processed by an accredited lab). Once those
  results arrive, a second model gives a much more reliable estimate
  before recommending an actual doctor visit.

## Why two tiers, not one

Testing showed symptom/demographic fields alone plateau around **65–73%
accuracy** no matter the algorithm (logistic regression, random forest,
gradient boosting, SVM, ensembling, and threshold tuning were all tried —
see `reports/tier1/`). Restoring CA-125 and CRP pushes accuracy to
**~99.7%**, because those two lab markers are the dominant signal in this
dataset. Rather than pretend a symptom-only model can hit clinical-grade
accuracy, the pipeline is upfront: Tier 1 is a screening nudge, Tier 2 is
where the real diagnostic power is, and it only asks for lab values when
there's already a reason to.

## Results summary

| | Tier 1 (home-only) | Tier 2 (+ CA-125/CRP) |
|---|---|---|
| Features | 12 | 14 |
| Accuracy | 69.4% | 99.7% |
| Recall | 57.8% | 100% |
| ROC-AUC | 0.750 | 1.000 |

Full metrics, confusion matrices, ROC curves, and feature importance plots
are in `reports/tier1/` and `reports/tier2/`.

**Caveat:** all of this is trained on a single synthetic dataset
(`data/endometriosis_data.csv`). CA-125/CRP behaving as near-deterministic
predictors is a property of how this dataset was generated — before
treating these numbers as real-world performance, validate against real
clinical data if you can get access to it.

## Project structure

```
project/
├── data/
│   ├── endometriosis_data.csv      # raw data (5000 rows, 15 columns)
│   └── processed/
│       ├── tier1/                  # scaled train/test splits + scaler
│       └── tier2/
├── models/
│   ├── tier1_model.pkl             # {model, model_name, feature_names, tier}
│   └── tier2_model.pkl
├── reports/
│   ├── tier1/                      # confusion matrix, ROC curve, feature importance
│   └── tier2/
├── src/
│   ├── data_preprocessing.py       # step 1: clean, split, scale -> both tiers
│   ├── train_model.py              # step 2: compare models, save best per tier
│   ├── evaluate_model.py           # step 3: metrics + plots per tier
│   └── predict.py                  # step 4: run the two-tier pipeline on a new patient
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Run in order from the project root — each step depends on the previous one's output:

```bash
python src/data_preprocessing.py   # builds data/processed/tier1/ and tier2/
python src/train_model.py          # builds models/tier1_model.pkl and tier2_model.pkl
python src/evaluate_model.py       # builds reports/tier1/ and tier2/
python src/predict.py              # interactive: answer symptom questions, get a risk flag
python src/predict.py --demo       # run on a built-in example patient instead
```

`predict.py` walks through the Tier 1 questionnaire, and if risk is
elevated (probability ≥ 0.5), tells you a mail-in kit is recommended. If
you already have CA-125/CRP values (or re-run it once your kit results
arrive), it feeds them into Tier 2 for the refined estimate.

## Retraining on new data

`data_preprocessing.py` and `train_model.py` both point at
`data/endometriosis_data.csv` by default. To retrain on a different
dataset, replace that file (keeping the same column names) and re-run the
four scripts in order.

Note: a second dataset (`structured_endometriosis_data.csv`) was
evaluated during development but excluded — it has no shared patient
identifier with the primary dataset (row-alignment and pooling tests both
confirmed no real correspondence), so its extra fields (menstrual
irregularity, hormone abnormality, chronic pain level) couldn't be merged
in without fabricating relationships between unrelated records. It's left
as a note for future data collection: those fields may be worth adding to
the *same* population's questionnaire, rather than a separate dataset.
