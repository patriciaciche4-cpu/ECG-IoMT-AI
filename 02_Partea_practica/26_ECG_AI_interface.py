# os permite lucrul cu foldere, fisiere si cai de acces Windows.
import os
# Tkinter este folosit pentru construirea interfetei grafice.
import tkinter as tk
# ttk ofera componente grafice mai moderne, iar messagebox afiseaza ferestre de avertizare/eroare.
from tkinter import ttk, messagebox
# Pandas este folosit pentru citirea si prelucrarea fisierelor CSV.
import pandas as pd
# NumPy este folosit pentru vectori, calcule numerice si gestionarea valorilor NaN.
import numpy as np
# Joblib incarca modelul Random Forest salvat anterior.
import joblib

# ============================================================
# CONFIGURARE
# ============================================================

# Folderul in care MATLAB salveaza automat inregistrarile ECG de tip Record_XXX.
DATABASE_FOLDER = r"C:\Users\User\Desktop\FIM-AN 3\Practica\ECG-DATABASE"

# Folderul in care se afla modelul Random Forest antrenat.
MODEL_FOLDER = (
    r"C:\Users\User\Desktop\FIM-AN 3\Practica"
    r"\mit-bih-arrhythmia-database-1.0.0"
)

# Construim automat calea completa catre fisierul modelului.
MODEL_PATH = os.path.join(
    MODEL_FOLDER,
    "random_forest_ecg_N_V_F_v4.joblib"
)

# ============================================================
# GASIRE RECORDURI
# ============================================================
def get_records():
    # Cauta automat toate folderele care incep cu Record_. Astfel, nu trebuie introdus manual numele unei inregistrari.
    """Returneaza automat toate folderele Record_XXX din baza ECG."""
    if not os.path.isdir(DATABASE_FOLDER):
        return []
    records = []
    for name in os.listdir(DATABASE_FOLDER):
        folder = os.path.join(DATABASE_FOLDER, name)
        if os.path.isdir(folder) and name.lower().startswith("record_"):
            records.append(name)
    return sorted(records)

# ============================================================
# CAUTARE FISIERE RECORD
# ============================================================
def record_path(record_name, filename):
    # Construieste calea catre un fisier din inregistrarea selectata.
    return os.path.join(DATABASE_FOLDER, record_name, filename)

def get_record_files(record_name):
    # Pornind de la numele Record_XXX, construieste automat toate fisierele folosite de analiza.
    """
    Construieste automat toate caile pentru recordul selectat.
    Nu exista niciun Record_XXX scris manual aici.
    """
    folder = os.path.join(DATABASE_FOLDER, record_name)
    return {
        "folder": folder,
        "features": os.path.join(
            folder, f"AI_features_{record_name}.csv"
        ),
        "ai_results": os.path.join(
            folder, f"AI_results_{record_name}.csv"
        ),
        "summary": os.path.join(
            folder, f"ECG_analysis_summary_{record_name}.csv"
        ),
        "rpeaks": os.path.join(
            folder, f"R_peaks_{record_name}.csv"
        ),
        "ecg_filtered": os.path.join(
            folder, "ECG_filtered.csv"
        ),
        "ecg_raw": os.path.join(
            folder, "ECG_raw.csv"
        ),
        "info": os.path.join(
            folder, "info.txt"
        ),
        "report": os.path.join(
            folder, f"ECG_final_decision_{record_name}.txt"
        ),
    }

# ============================================================
# FEREASTRA PRINCIPALA
# ============================================================

# Cream fereastra principala a aplicatiei.
root = tk.Tk()
# Stabilim titlul si dimensiunea initiala a ferestrei.
root.title("Analiză ECG + AI")
root.geometry("850x650")
root.minsize(750, 600)

# ============================================================
# STIL
# ============================================================
style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass
style.configure(
    "Title.TLabel",
    font=("Arial", 24, "bold")
)
style.configure(
    "Subtitle.TLabel",
    font=("Arial", 11)
)

# ============================================================
# TITLU
# ============================================================
title = ttk.Label(
    root,
    text="ANALIZĂ ECG + AI",
    style="Title.TLabel"
)
title.pack(pady=(25, 5))

subtitle = ttk.Label(
    root,
    text="Sistem prototip pentru analiza automată a semnalului ECG",
    style="Subtitle.TLabel"
)
subtitle.pack(pady=(0, 25))

# ============================================================
# CONFIGURARE
# ============================================================
configuration_frame = ttk.LabelFrame(
    root,
    text="Configurare analiză",
    padding=20
)
configuration_frame.pack(
    fill="x",
    padx=40,
    pady=10
)

ttk.Label(
    configuration_frame,
    text="Înregistrare:"
).grid(
    row=0,
    column=0,
    padx=10,
    pady=10,
    sticky="w"
)

# Variabila in care este retinuta inregistrarea aleasa din lista.
record_var = tk.StringVar()

record_combo = ttk.Combobox(
    configuration_frame,
    textvariable=record_var,
    state="readonly",
    width=35
)

record_combo.grid(
    row=0,
    column=1,
    padx=10,
    pady=10
)

ttk.Label(
    configuration_frame,
    text="Activitate:"
).grid(
    row=1,
    column=0,
    padx=10,
    pady=10,
    sticky="w"
)

# Variabila in care este retinuta activitatea aleasa de utilizator.
activity_var = tk.StringVar()

activity_combo = ttk.Combobox(
    configuration_frame,
    textvariable=activity_var,
    state="readonly",
    width=35,
    values=[
        "Repaus",
        "Mers",
        "Efort fizic",
        "Stres / anxietate",
        "Somn",
        "Alta activitate"
    ]
)

activity_combo.current(0)

activity_combo.grid(
    row=1,
    column=1,
    padx=10,
    pady=10
)

# ============================================================
# ACTUALIZARE RECORDURI
# ============================================================
def refresh_records():
    # Reimprospateaza lista de inregistrari citind din nou folderul ECG-DATABASE.
    records = get_records()
    record_combo["values"] = records
    if records:
        # Pastreaza selectia curenta daca ea exista.
        current = record_var.get()
        if current in records:
            record_combo.set(current)
        else:
            record_combo.current(len(records) - 1)
    else:
        record_var.set("")

    show_result(
        "Selectează o înregistrare și apasă „ANALIZEAZĂ ECG”.\n\n"
        "Interfața va detecta automat ultima înregisrare Record_XXX "
        "din ECG-DATABASE."
    )

# ============================================================
# REZULTATE
# ============================================================
results_frame = ttk.LabelFrame(
    root,
    text="Rezultatele analizei",
    padding=20
)

results_frame.pack(
    fill="both",
    expand=True,
    padx=40,
    pady=10
)

result_text = tk.Text(
    results_frame,
    height=15,
    width=80,
    font=("Consolas", 11),
    state="disabled",
    wrap="word"
)

result_text.pack(
    fill="both",
    expand=True
)

def show_result(text):
    # Afiseaza rezultatul analizei in caseta de text din interfata.
    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.insert(tk.END, text)
    result_text.config(state="disabled")

# Prima încărcare a listei de înregistrări.
# Este apelată DUPĂ definirea funcției show_result().
refresh_records()

# ============================================================
# FUNCTII UTILE
# ============================================================
def safe_float(value, default=np.nan):
    # Converteste o valoare la numar. Daca nu se poate, returneaza NaN pentru a evita blocarea programului.
    try:
        return float(value)
    except Exception:
        return default

def find_column(df, possible_names):
    # Cauta automat o coloana dupa mai multe denumiri posibile, pentru compatibilitate intre fisiere.
    """Gaseste prima coloana existenta din lista."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# ============================================================
# ANALIZA ECG + AI
# ============================================================
def analyze_record():
    # Functia principala: incarca modelul si datele, face predictia AI, calculeaza statisticile si afiseaza rezultatul.
    record_name = record_var.get()
    activity = activity_var.get()

    if not record_name:
        messagebox.showwarning(
            "Atenție",
            "Selectează o înregistrare ECG."
        )
        return
    files = get_record_files(record_name)

    features_file = files["features"]
    summary_file = files["summary"]
    ai_file = files["ai_results"]

    # --------------------------------------------------------
    # VERIFICARI
    # --------------------------------------------------------
    if not os.path.exists(features_file):
        messagebox.showerror(
            "Fișier lipsă",
            f"Nu există:\n\n{features_file}\n\n"
            "Rulează mai întâi ecg_reader_FINAL.m pentru "
            "înregistrarea respectivă."
        )
        return

    if not os.path.exists(summary_file):
        messagebox.showerror(
            "Fișier lipsă",
            f"Nu există:\n\n{summary_file}\n\n"
            "Rulează mai întâi ecg_reader_FINAL.m."
        )
        return

    if not os.path.exists(MODEL_PATH):
        messagebox.showerror(
            "Model lipsă",
            f"Modelul Random Forest nu a fost găsit:\n\n{MODEL_PATH}"
        )
        return

    try:
        # ====================================================
        # 1. MODEL
        # ====================================================

        # Incarcam modelul Random Forest salvat pe disc.
        model_data = joblib.load(MODEL_PATH)

        if not isinstance(model_data, dict):
            raise ValueError(
                "Modelul V4 nu este salvat sub forma unui dicționar."
            )

        if "model" not in model_data:
            raise ValueError(
                "Modelul nu conține cheia 'model'."
            )

        if "feature_columns" not in model_data:
            raise ValueError(
                "Modelul nu conține cheia 'feature_columns'."
            )

        model = model_data["model"]
        feature_columns = list(model_data["feature_columns"])

        # ====================================================
        # 2. FEATURES
        # ====================================================

        # Citim caracteristicile generate de MATLAB din fisierul CSV.
        features = pd.read_csv(features_file)

        if features.empty:
            raise ValueError(
                f"Fișierul {os.path.basename(features_file)} "
                "nu conține exemple ECG."
            )

        missing_features = [
            column
            for column in feature_columns
            if column not in features.columns
        ]

        if missing_features:
            raise ValueError(
                "Lipsesc caracteristici necesare modelului:\n\n"
                + "\n".join(missing_features)
            )
        X = features[feature_columns].copy()

        # Verificare valori lipsa / infinite.
        X = X.replace([np.inf, -np.inf], np.nan)
        if X.isnull().any().any():
            bad_columns = X.columns[X.isnull().any()].tolist()
            raise ValueError(
                "Caracteristicile conțin valori lipsă sau infinite.\n\n"
                "Coloane afectate:\n"
                + "\n".join(bad_columns)
            )
        if len(X) == 0:
            raise ValueError(
                "Nu există exemple ECG valide pentru clasificare."
            )

        # ====================================================
        # 3. PREDICTIE
        # ====================================================

        # Modelul clasifica fiecare bataie ECG in una dintre clasele N, V sau F.
        predictions = model.predict(X)

        # ====================================================
        # 4. CLASE
        # ====================================================

        if hasattr(model, "classes_"):
            model_classes = [str(x) for x in model.classes_]
        else:
            model_classes = ["N", "V", "F"]

        # ====================================================
        # 5. PROBABILITATI
        # ====================================================
        probabilities = None

        if hasattr(model, "predict_proba"):
            # Obtinerea probabilitatilor pentru fiecare clasa, daca modelul le suporta.
            probabilities = model.predict_proba(X)

        # ====================================================
        # 6. CREARE AI_RESULTS
        # ====================================================
        ai_results = pd.DataFrame()

        # Coloana Beat este folosita de celelalte programe Python.
        ai_results["Beat"] = np.arange(
            1,
            len(predictions) + 1
        )

        ai_results["AI_class"] = [
            str(x) for x in predictions
        ]

        # Initializare.
        ai_results["prob_N"] = 0.0
        ai_results["prob_V"] = 0.0
        ai_results["prob_F"] = 0.0

        if probabilities is not None:
            for class_name, column_name in [
                ("N", "prob_N"),
                ("V", "prob_V"),
                ("F", "prob_F")
            ]:
                if class_name in model_classes:
                    class_index = model_classes.index(class_name)
                    ai_results[column_name] = probabilities[:, class_index]

        # ====================================================
        # 7. SALVARE AI_RESULTS
        # ====================================================

        # Salvam predictiile si probabilitatile pentru fiecare bataie.
        ai_results.to_csv(
            ai_file,
            index=False
        )

        # ====================================================
        # 8. SUMMARY ECG
        # ====================================================

        # Citim valorile HR si HRV calculate anterior de MATLAB.
        summary = pd.read_csv(summary_file)

        if summary.empty:
            raise ValueError(
                "ECG_analysis_summary este gol."
            )

        data = summary.iloc[0]

        # Folosim valorile produse de MATLAB.
        HR = safe_float(data.get("HR_mediu_bpm"))
        HR_min = safe_float(data.get("HR_min_bpm"))
        HR_max = safe_float(data.get("HR_max_bpm"))
        RR = safe_float(data.get("RR_mediu_s"))
        SDNN = safe_float(data.get("SDNN_ms"))
        RMSSD = safe_float(data.get("RMSSD_ms"))
        pNN50 = safe_float(data.get("pNN50_percent"))

        # ====================================================
        # 9. DISTRIBUTIA CLASELOR
        # ====================================================

        total = len(ai_results)

        N = int(
            (ai_results["AI_class"] == "N").sum()
        )

        V = int(
            (ai_results["AI_class"] == "V").sum()
        )

        F = int(
            (ai_results["AI_class"] == "F").sum()
        )

        N_percent = N / total * 100
        V_percent = V / total * 100
        F_percent = F / total * 100

        # ====================================================
        # 10. PROBABILITATI MEDII
        # ====================================================

        prob_N = float(ai_results["prob_N"].mean())
        prob_V = float(ai_results["prob_V"].mean())
        prob_F = float(ai_results["prob_F"].mean())

        # Atentie:
        # aceasta este probabilitatea medie maxima dintre clase,
        # nu o "acuratete" a modelului.
        confidence = max(
            prob_N,
            prob_V,
            prob_F
        )

        # ====================================================
        # 11. CLASA PREDOMINANTA
        # ====================================================

        class_counts = {
            "N": N,
            "V": V,
            "F": F
        }
        predominant = max(
            class_counts,
            key=class_counts.get
        )

        predominant_percent = (
            class_counts[predominant]
            / total
            * 100
        )

        # ====================================================
        # 12. DECIZIE CONTEXTUALA - ACTIVITATEA CONTEAZA
        # Aici HR este interpretat in functie de activitatea selectata.
        # Exemplu: limita pentru efort fizic este mai mare decat cea pentru repaus.
        # ====================================================

        # Praguri orientative pentru HR in functie de activitate.
        # Aceste praguri NU reprezinta criterii medicale de diagnostic.
        hr_limits = {
            "Repaus": (50, 100),
            "Mers": (50, 120),
            "Efort fizic": (50, 180),
            "Stres / anxietate": (50, 120),
            "Somn": (40, 100),
            "Alta activitate": (50, 120)
        }

        hr_low_limit, hr_high_limit = hr_limits.get(
            activity,
            (50, 100)
        )

        hr_context_alert = False
        hr_context_message = ""

        if pd.notna(HR):
            if HR > hr_high_limit:
                hr_context_alert = True
                hr_context_message = (
                    f"HR mediu ({HR:.1f} bpm) este peste limita "
                    f"orientativa folosita pentru activitatea "
                    f"'{activity}' ({hr_high_limit} bpm)."
                )
            elif HR < hr_low_limit:
                hr_context_alert = True
                hr_context_message = (
                    f"HR mediu ({HR:.1f} bpm) este sub limita "
                    f"orientativa folosita pentru activitatea "
                    f"'{activity}' ({hr_low_limit} bpm)."
                )
            else:
                hr_context_message = (
                    f"HR mediu ({HR:.1f} bpm) este compatibil cu "
                    f"intervalul orientativ folosit pentru activitatea "
                    f"'{activity}' ({hr_low_limit}-{hr_high_limit} bpm)."
                )
        else:
            hr_context_message = "HR mediu nu este disponibil."

        # Important:
        # Efortul fizic poate creste in mod normal frecventa cardiaca.
        # Prin urmare, un HR mare in timpul efortului NU declanseaza
        # singur o alerta. AI si HR sunt evaluate separat.
        # Alerta AI apare daca o clasa anormala (V sau F) devine predominanta.
        ai_alert = predominant != "N"

        if ai_alert:
            alert = "ATENȚIE"
        elif hr_context_alert:
            alert = "ATENȚIE"
        else:
            alert = "NORMAL"

        # ====================================================
        # 13. INTERPRETARE
        # ====================================================

        if activity == "Efort fizic" and pd.notna(HR) and HR <= hr_high_limit:
            activity_note = (
                "Activitatea selectata este efort fizic; frecventa cardiaca "
                "crescuta poate fi compatibila cu acest context si nu este "
                "considerata singura un motiv de alerta."
            )
        elif activity == "Mers" and pd.notna(HR) and HR <= hr_high_limit:
            activity_note = (
                "Activitatea selectata este mers; frecventa cardiaca este "
                "evaluata folosind un prag mai permisiv decat la repaus."
            )
        elif activity == "Stres / anxietate" and pd.notna(HR) and HR <= hr_high_limit:
            activity_note = (
                "Activitatea selectata este stres/anxietate; o crestere a "
                "frecventei cardiace poate aparea in acest context."
            )
        else:
            activity_note = ""

        if predominant == "N" and not hr_context_alert:
            interpretation = (
                "Modelul AI indica o predominanta a clasei N (Normal), iar "
                + hr_context_message + " "
                + activity_note
                + " Rezultatul trebuie interpretat impreuna cu semnalul ECG "
                "si nu reprezinta un diagnostic medical."
            )
        elif predominant != "N" and not hr_context_alert:
            interpretation = (
                f"Modelul AI indica o predominanta a clasei {predominant}. "
                + hr_context_message + " "
                + activity_note
                + " Alerta este determinata de clasificarea AI, nu de HR. "
                "Rezultatul necesita verificarea semnalului ECG si nu "
                "reprezinta un diagnostic medical."
            )
        elif predominant == "N" and hr_context_alert:
            interpretation = (
                "Modelul AI indica o predominanta a clasei N, dar "
                + hr_context_message + " "
                "Este necesara verificarea semnalului ECG. Rezultatul nu "
                "reprezinta un diagnostic medical."
            )
        else:
            interpretation = (
                f"Modelul AI indica o predominanta a clasei {predominant}, "
                "iar "
                + hr_context_message + " "
                "Atat clasificarea AI, cat si componenta HR necesita "
                "verificarea semnalului ECG. Rezultatul nu reprezinta "
                "un diagnostic medical."
            )

        # ====================================================
        # 14. TEXT REZULTAT
        # ====================================================

        def fmt(value, decimals=2):
            if pd.isna(value):
                return "N/A"
            return f"{value:.{decimals}f}"

        output = ""

        output += "================================================\n"
        output += "                 REZULTATE ECG\n"
        output += "================================================\n\n"

        output += f"Înregistrare: {record_name}\n"
        output += f"Activitate:   {activity}\n\n"

        output += "FRECVENȚĂ CARDIACĂ\n"
        output += "------------------------------------------------\n"
        output += f"HR mediu:     {fmt(HR)} bpm\n"
        output += f"HR minim:     {fmt(HR_min)} bpm\n"
        output += f"HR maxim:     {fmt(HR_max)} bpm\n"
        output += f"RR mediu:     {fmt(RR, 4)} s\n"
        output += f"Interval HR folosit: {hr_low_limit}-{hr_high_limit} bpm\n"
        output += f"Evaluare HR:   {hr_context_message}\n\n"

        output += "HRV\n"
        output += "------------------------------------------------\n"
        output += f"SDNN:         {fmt(SDNN)} ms\n"
        output += f"RMSSD:        {fmt(RMSSD)} ms\n"
        output += f"pNN50:        {fmt(pNN50)} %\n\n"

        output += "CLASIFICARE AI\n"
        output += "------------------------------------------------\n"
        output += f"N:            {N} ({N_percent:.2f}%)\n"
        output += f"V:            {V} ({V_percent:.2f}%)\n"
        output += f"F:            {F} ({F_percent:.2f}%)\n\n"

        output += (
            f"Clasa predominantă: {predominant} "
            f"({predominant_percent:.2f}%)\n"
        )

        output += f"Probabilitate medie N: {prob_N:.3f}\n"
        output += f"Probabilitate medie V: {prob_V:.3f}\n"
        output += f"Probabilitate medie F: {prob_F:.3f}\n"
        output += f"Încredere maximă medie: {confidence:.3f}\n\n"

        output += "================================================\n"
        output += f"                  ⚠ {alert}\n"
        output += "================================================\n\n"

        output += interpretation

        show_result(output)

        # ====================================================
        # 15. RAPORT FINAL
        # ====================================================

        report_text = (
            "SISTEM AUTOMAT DE DECIZIE ECG + AI\n"
            "========================================\n\n"
            + output
            + "\n\n"
            + "Notă: rezultatul AI este orientativ și nu reprezintă "
              "un diagnostic medical.\n"
        )

        with open(
            files["report"],
            "w",
            encoding="utf-8"
        ) as file:
            file.write(report_text)

        messagebox.showinfo(
            "Analiză finalizată",
            f"Analiza ECG + AI pentru {record_name} "
            "a fost finalizată.\n\n"
            f"Rezultatele AI au fost salvate în:\n"
            f"{os.path.basename(ai_file)}"
        )

    except Exception as error:
        messagebox.showerror(
            "Eroare analiză ECG + AI",
            str(error)
        )

# ============================================================
# AFISARE ECG FILTRAT - POP-UP
# ============================================================

def show_ecg():
    # Deschide ECG-ul filtrat intr-o fereastra separata, fara R-peaks si fara clasele AI.
    """
    Afiseaza DOAR ECG-ul filtrat intr-o fereastra pop-up.
    Nu afiseaza R-peaks si nu afiseaza clasele AI.
    """

    record_name = record_var.get()

    if not record_name:
        messagebox.showwarning(
            "Atenție",
            "Selectează o înregistrare."
        )
        return
    files = get_record_files(record_name)
    ecg_file = files["ecg_filtered"]

    if not os.path.exists(ecg_file):
        messagebox.showerror(
            "ECG lipsă",
            f"Nu există ECG_filtered.csv pentru {record_name}.\n\n"
            "Rulează mai întâi ecg_reader_FINAL.m."
        )
        return

    try:
        import matplotlib.pyplot as plt

        # Incarcam semnalul ECG filtrat generat de MATLAB.
        ecg = pd.read_csv(ecg_file)

        # Detectare automata a coloanei de timp.
        time_col = find_column(
            ecg,
            ["Time_s", "time_s", "Time", "time"]
        )

        # Detectare automata a semnalului filtrat.
        signal_col = find_column(
            ecg,
            [
                "ECG_filtered_ADC",
                "ECG_filtered",
                "ECG_Filtered_ADC",
                "Filtered_ECG"
            ]
        )

        if time_col is None:
            # Daca MATLAB a exportat doar semnalul,
            # construim timpul din Fs daca exista in info.
            signal_col = signal_col or (
                ecg.columns[0] if len(ecg.columns) else None
            )

            if signal_col is None:
                raise ValueError(
                    "Nu s-a găsit coloana ECG în ECG_filtered.csv."
                )
            signal = pd.to_numeric(
                ecg[signal_col],
                errors="coerce"
            ).values

            time = np.arange(len(signal))

            xlabel = "Eșantion"
        else:
            if signal_col is None:
                # Incearca sa gaseasca prima coloana numerica
                # diferita de timpul.
                numeric_candidates = []

                for col in ecg.columns:
                    if col == time_col:
                        continue

                    converted = pd.to_numeric(
                        ecg[col],
                        errors="coerce"
                    )

                    if converted.notna().sum() > 0:
                        numeric_candidates.append(col)

                if not numeric_candidates:
                    raise ValueError(
                        "Nu s-a găsit coloana semnalului ECG filtrat."
                    )
                signal_col = numeric_candidates[0]
            time = pd.to_numeric(
                ecg[time_col],
                errors="coerce"
            ).values

            signal = pd.to_numeric(
                ecg[signal_col],
                errors="coerce"
            ).values

            xlabel = "Timp [s]"

        valid = (
            np.isfinite(time)
            & np.isfinite(signal)
        )

        time = time[valid]
        signal = signal[valid]

        if len(signal) == 0:
            raise ValueError(
                "ECG_filtered.csv nu conține valori valide."
            )

        # ====================================================
        # POP-UP MATPLOTLIB
        # ====================================================

        # Cream o fereastra pop-up separata pentru graficul ECG.
        ecg_window = tk.Toplevel(root)

        ecg_window.title(
            f"ECG filtrat - {record_name}"
        )

        ecg_window.geometry(
            "1250x750"
        )

        ecg_window.minsize(
            950,
            600
        )

        # Folosim matplotlib intr-o fereastra separata.
        # Astfel graficul NU apare in Spyder/Plots.
        from matplotlib.backends.backend_tkagg import (
            FigureCanvasTkAgg
        )
        from matplotlib.figure import Figure

        figure = Figure(
            figsize=(12, 7),
            dpi=100
        )

        ax = figure.add_subplot(111)
        # Desenam exclusiv semnalul ECG filtrat.
        ax.plot(
            time,
            signal,
            linewidth=0.8,
            label="ECG filtrat"
        )
        ax.set_title(
            f"ECG filtrat - {record_name}",
            fontsize=16,
            fontweight="bold"
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel("ECG [ADC]")

        ax.grid(
            True,
            alpha=0.3
        )
        ax.legend(
            loc="upper right"
        )
        ax.set_xlim(
            time[0],
            time[-1]
        )
        figure.tight_layout()

        canvas = FigureCanvasTkAgg(
            figure,
            master=ecg_window
        )
        canvas.draw()
        canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )
        close_button = ttk.Button(
            ecg_window,
            text="ÎNCHIDE",
            command=ecg_window.destroy
        )
        close_button.pack(
            pady=(0, 12)
        )
    except Exception as error:
        messagebox.showerror(
            "Eroare ECG",
            str(error)
        )

# ============================================================
# AFISARE RAPORT
# ============================================================
def show_report():
    # Deschide raportul final salvat pentru inregistrarea selectata.
    record_name = record_var.get()

    if not record_name:
        messagebox.showwarning(
            "Atenție",
            "Selectează o înregistrare."
        )
        return
    files = get_record_files(record_name)
    report_file = files["report"]

    if not os.path.exists(report_file):
        messagebox.showwarning(
            "Raport indisponibil",
            "Raportul final nu există încă.\n\n"
            "Apasă mai întâi „ANALIZEAZĂ ECG”."
        )
        return

    try:
        with open(
            report_file,
            "r",
            encoding="utf-8"
        ) as file:
            report = file.read()
        report_window = tk.Toplevel(root)
        report_window.title(
            f"Raport ECG + AI - {record_name}"
        )
        report_window.geometry(
            "800x650"
        )
        text = tk.Text(
            report_window,
            font=("Consolas", 10),
            wrap="word"
        )
        text.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )
        text.insert(
            "1.0",
            report
        )
        text.config(
            state="disabled"
        )
        ttk.Button(
            report_window,
            text="ÎNCHIDE",
            command=report_window.destroy
        ).pack(
            pady=(0, 12)
        )
    except Exception as error:
        messagebox.showerror(
            "Eroare raport",
            str(error)
        )

# ============================================================
# BUTOANE
# ============================================================
button_frame = ttk.Frame(root)
button_frame.pack(
    pady=15
)
ttk.Button(
    button_frame,
    text="ANALIZEAZĂ ECG",
    command=analyze_record
).grid(
    row=0,
    column=0,
    padx=8
)
ttk.Button(
    button_frame,
    text="VEZI ECG",
    command=show_ecg
).grid(
    row=0,
    column=1,
    padx=8
)
ttk.Button(
    button_frame,
    text="VEZI RAPORT",
    command=show_report
).grid(
    row=0,
    column=2,
    padx=8
)
ttk.Button(
    button_frame,
    text="ACTUALIZEAZĂ",
    command=refresh_records
).grid(
    row=0,
    column=3,
    padx=8
)

# ============================================================
# PORNIRE
# ============================================================
# Porneste bucla principala a interfetei grafice; programul ramane activ pana la inchiderea ferestrei.
root.mainloop()
