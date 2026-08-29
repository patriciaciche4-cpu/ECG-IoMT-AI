import os
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# ============================================================
# 1. CALE DATASET
# ============================================================

database_folder = (
    r"C:\Users\User\Desktop\FIM-AN 3\Practica"
    r"\mit-bih-arrhythmia-database-1.0.0"
)

dataset_file = os.path.join(
    database_folder,
    "ai_dataset_N_V_F_2400_v2.csv"
)


# ============================================================
# 2. INCARCARE
# ============================================================

df = pd.read_csv(dataset_file)

df["record"] = df["record"].astype(str)

print("=" * 60)
print("RANDOM FOREST V4 - SPLIT AUTOMAT PE RECORD")
print("=" * 60)

print(
    "Total exemple:",
    len(df)
)


# ============================================================
# 3. CARACTERISTICI
# ============================================================

feature_columns = [
    column
    for column in df.columns
    if column not in [
        "label",
        "record",
        "r_peak"
    ]
]

X = df[feature_columns]
y = df["label"]


# ============================================================
# 4. DISTRIBUTIA TOTALA
# ============================================================

print("\n" + "=" * 60)
print("DISTRIBUTIA TOTALA")
print("=" * 60)

total_distribution = (
    df["label"]
    .value_counts()
    .sort_index()
)

print(total_distribution)


# ============================================================
# 5. DISTRIBUTIA PE RECORD
# ============================================================

record_distribution = pd.crosstab(
    df["record"],
    df["label"]
)

for cls in ["N", "V", "F"]:

    if cls not in record_distribution.columns:
        record_distribution[cls] = 0

record_distribution = record_distribution[
    ["N", "V", "F"]
]


print("\n" + "=" * 60)
print("DISTRIBUTIA PE RECORD")
print("=" * 60)

print(record_distribution)


# ============================================================
# 6. CAUTARE AUTOMATA A UNUI TEST SET
# ============================================================

records = sorted(
    df["record"].unique()
)

rng = np.random.RandomState(42)

target_test_fraction = 0.20

target_test_examples = (
    len(df)
    * target_test_fraction
)

target_test_class_counts = (
    total_distribution
    * target_test_fraction
)


# ------------------------------------------------------------
# Functie care calculeaza cat de buna este o selectie
# ------------------------------------------------------------

def score_test_set(selected_records):

    selected_records = list(
        selected_records
    )

    selected = record_distribution.loc[
        selected_records
    ]

    counts = selected.sum()

    # Penalizare pentru lipsa claselor
    if any(
        counts.get(cls, 0) == 0
        for cls in ["N", "V", "F"]
    ):
        return 1e12

    # Diferenta fata de distributia tinta
    class_error = np.sum(
        (
            counts[
                ["N", "V", "F"]
            ].values
            -
            target_test_class_counts[
                ["N", "V", "F"]
            ].values
        ) ** 2
    )

    # Diferenta fata de 20% total
    total_error = (
        (
            counts.sum()
            -
            target_test_examples
        )
        ** 2
    )

    return (
        class_error
        + 0.25 * total_error
    )


# ============================================================
# 7. CAUTARE
# ============================================================

best_records = None
best_score = np.inf

num_records = len(records)

# Incercam multe combinatii aleatorii.
# Nu folosim split pe exemple, ci doar pe RECORD.

for iteration in range(20000):

    shuffled = records.copy()

    rng.shuffle(
        shuffled
    )

    # Selectam aproximativ 20% dintre recorduri
    number_test_records = max(
        1,
        int(
            round(
                0.20
                * num_records
            )
        )
    )

    candidate = shuffled[
        :number_test_records
    ]

    score = score_test_set(
        candidate
    )

    if score < best_score:

        best_score = score

        best_records = sorted(
            candidate
        )


# ============================================================
# 8. TRAIN / TEST RECORDS
# ============================================================

test_records = best_records

train_records = [
    record
    for record in records
    if record not in test_records
]


print("\n" + "=" * 60)
print("SPLIT FINAL")
print("=" * 60)

print(
    "TRAIN records:",
    train_records
)

print(
    "TEST records:",
    test_records
)


# ============================================================
# 9. CREARE DATASETURI
# ============================================================

train_df = df[
    df["record"].isin(
        train_records
    )
].copy()

test_df = df[
    df["record"].isin(
        test_records
    )
].copy()


X_train = train_df[
    feature_columns
]

y_train = train_df[
    "label"
]

X_test = test_df[
    feature_columns
]

y_test = test_df[
    "label"
]


# ============================================================
# 10. VERIFICARE DISTRIBUTII
# ============================================================

print("\n" + "=" * 60)
print("DISTRIBUTIE TRAIN")
print("=" * 60)

print(
    y_train.value_counts()
)


print("\n" + "=" * 60)
print("DISTRIBUTIE TEST")
print("=" * 60)

print(
    y_test.value_counts()
)


print("\n" + "=" * 60)
print("PROCENTE")
print("=" * 60)

print(
    "TOTAL:"
)

print(
    (
        y.value_counts(
            normalize=True
        )
        * 100
    ).round(2)
)


print(
    "\nTRAIN:"
)

print(
    (
        y_train.value_counts(
            normalize=True
        )
        * 100
    ).round(2)
)


print(
    "\nTEST:"
)

print(
    (
        y_test.value_counts(
            normalize=True
        )
        * 100
    ).round(2)
)


# ============================================================
# 11. VERIFICARE OBLIGATORIE
# ============================================================

for cls in ["N", "V", "F"]:

    train_count = (
        y_train == cls
    ).sum()

    test_count = (
        y_test == cls
    ).sum()

    if train_count == 0:
        raise ValueError(
            f"Clasa {cls} lipseste din TRAIN!"
        )

    if test_count == 0:
        raise ValueError(
            f"Clasa {cls} lipseste din TEST!"
        )


# Verificare data leakage

common_records = (
    set(train_records)
    .intersection(
        set(test_records)
    )
)

if common_records:

    raise ValueError(
        "Data leakage! Recorduri comune: "
        + str(common_records)
    )

print(
    "\nVerificare data leakage: OK"
)


# ============================================================
# 12. RANDOM FOREST
# ============================================================

print("\n" + "=" * 60)
print("ANTRENARE RANDOM FOREST V4")
print("=" * 60)

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

print(
    "Antrenarea s-a terminat."
)


# ============================================================
# 13. PREDICTIE
# ============================================================

y_pred = model.predict(
    X_test
)


# ============================================================
# 14. ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)


print("\n" + "=" * 60)
print("REZULTATE")
print("=" * 60)

print(
    f"Accuracy: {accuracy * 100:.3f}%"
)


# ============================================================
# 15. CLASSIFICATION REPORT
# ============================================================

classes = [
    "N",
    "V",
    "F"
]

print("\n" + "=" * 60)
print("CLASSIFICATION REPORT")
print("=" * 60)

report = classification_report(
    y_test,
    y_pred,
    labels=classes,
    digits=4,
    zero_division=0
)

print(
    report
)


# ============================================================
# 16. MATRICE DE CONFUZIE
# ============================================================

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=classes
)

cm_df = pd.DataFrame(
    cm,
    index=classes,
    columns=classes
)

print("\n" + "=" * 60)
print("MATRICEA DE CONFUZIE")
print("=" * 60)

print(
    cm_df
)


# ============================================================
# 17. FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame({
    "Feature": feature_columns,
    "Importance":
        model.feature_importances_
})

importance = (
    importance
    .sort_values(
        "Importance",
        ascending=False
    )
)


print("\n" + "=" * 60)
print("TOP 20 CARACTERISTICI")
print("=" * 60)

print(
    importance.head(20).to_string(
        index=False
    )
)


# ============================================================
# 18. SALVARE MODEL
# ============================================================

model_file = os.path.join(
    database_folder,
    "random_forest_ecg_N_V_F_v4.joblib"
)

joblib.dump(
    {
        "model": model,
        "feature_columns":
            feature_columns,
        "train_records":
            train_records,
        "test_records":
            test_records,
        "classes":
            classes
    },
    model_file
)


# ============================================================
# 19. SALVARE IMPORTANCE
# ============================================================

importance_file = os.path.join(
    database_folder,
    "random_forest_feature_importance_v4.csv"
)

importance.to_csv(
    importance_file,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 60)
print("MODEL SALVAT")
print("=" * 60)

print(
    model_file
)

print(
    "\nFeature importance:"
)

print(
    importance_file
)