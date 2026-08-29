clear;
clc;
close all;

%% ============================================================
% ECG_READER_FINAL
% ACHIZITIE + FILTRARE + R-PEAKS + HR/HRV + AI FEATURES
% ============================================================

%% ============================================================
% CONFIGURARE
% ============================================================

% Portul serial al ESP32 si viteza de comunicatie.
% Aceste valori trebuie sa corespunda configurarii ESP32.
port = "COM4";
baudrate = 115200;
% Se stabileste durata dorita a inregistrarii.
% Fs_aprox este doar rata estimata folosita pentru a calcula
% numarul initial de esantioane; ulterior se calculeaza Fs real
% din vectorul de timp masurat.
durata = 60;              % durata inregistrarii [s]
Fs_aprox = 250;           % rata aproximativa ESP32 [Hz]
N = Fs_aprox * durata;
database_folder = ...
    "C:\Users\User\Desktop\FIM-AN 3\Practica\ECG-DATABASE";

%% ============================================================
% CREARE BAZA DE DATE
% ============================================================
if ~isfolder(database_folder)
    mkdir(database_folder);
end

%% ============================================================
% DETERMINARE AUTOMATA RECORD NOU
% ============================================================

% Cauta toate folderele Record_XXX existente.
% Astfel, programul poate crea automat urmatorul numar de record.
folders = dir(fullfile(database_folder, "Record_*"));
folders = folders([folders.isdir]);
if isempty(folders)
    record_number = 1;
else
    numbers = [];
    for k = 1:length(folders)
        name = folders(k).name;
        number = sscanf(name, "Record_%d");
        if ~isempty(number)
            numbers(end+1) = number;
        end
    end
    if isempty(numbers)
        record_number = 1;
    else
        record_number = max(numbers) + 1;
    end

end

% Formateaza numele cu trei cifre: Record_001, Record_002 etc.
record_name = sprintf("Record_%03d", record_number);
record_folder = fullfile( ...
    database_folder, ...
    record_name ...
);
if ~isfolder(record_folder)
    mkdir(record_folder);
end

%% ============================================================
% CONECTARE ESP32
% ============================================================
disp("============================================================");
disp("                 ECG_READER_FINAL");
disp("============================================================");
disp("Conectare la ESP32...");

% Deschide conexiunea seriala cu ESP32 pentru achizitia ECG.
s = serialport(port, baudrate);

flush(s);
pause(1);

disp("Conectat cu succes.");
disp("");
disp("============================================================");
disp("RECORD: " + record_name);
disp("============================================================");

disp("Pregateste-te...");
pause(2);

disp("");
disp("INREGISTRAREA INCEPE!");
disp("Stai nemiscata timp de " + durata + " secunde.");
disp("");

%% ============================================================
% ACHIZITIE ECG
% ============================================================

% Prealocam vectorii pentru a stoca semnalul ECG si timpul fiecarui esantion.
ecg = zeros(N,1);
time = zeros(N,1);
tic;
for i = 1:N
    try
        % Citeste o valoare text de la ESP32 si o converteste in numar.
        value = str2double(readline(s));
        ecg(i) = value;
        time(i) = toc;
    catch
        ecg(i) = NaN;
        time(i) = toc;
    end
end
elapsed_time = toc;
clear s;
disp("");
disp("INREGISTRAREA S-A TERMINAT.");
disp("");

%% ============================================================
% ELIMINARE VALORI INVALIDe
% ============================================================
valid = ~isnan(ecg);
ecg = ecg(valid);
time = time(valid);
if length(ecg) < 10
    error("Nu au fost achizitionate suficiente esantioane ECG.");
end

%% ============================================================
% CALCUL Fs REAL
% ============================================================

% Calculam frecventa reala de esantionare din diferentele dintre
% momentele consecutive de achizitie.
Fs = 1 / mean(diff(time));

fprintf("============================================================\n");
fprintf("INFORMATII ACHIZITIE\n");
fprintf("============================================================\n");
fprintf("Record                 : %s\n", record_name);
fprintf("Durata solicitata      : %.2f s\n", durata);
fprintf("Durata masurata        : %.3f s\n", elapsed_time);
fprintf("Numar esantioane       : %d\n", length(ecg));
fprintf("Fs real estimat        : %.2f Hz\n", Fs);
fprintf("============================================================\n");

%% ============================================================
% SALVARE ECG RAW
% ============================================================
ECG_table = table( ...
    time, ...
    ecg, ...
    'VariableNames', ...
    {'Time_s','ECG_ADC'} ...
);
ecg_file = fullfile( ...
    record_folder, ...
    "ECG_raw.csv" ...
);
writetable(ECG_table, ecg_file);

%% ============================================================
% INFORMATII RECORD
% ============================================================
info_file = fullfile( ...
    record_folder, ...
    "info.txt" ...
);
fid = fopen(info_file, 'w');
fprintf(fid, "ECG RECORD INFORMATION\n");
fprintf(fid, "======================\n\n");
fprintf(fid, "Record ID: %s\n", record_name);
fprintf(fid, "Duration requested: %.2f s\n", durata);
fprintf(fid, "Duration measured: %.4f s\n", elapsed_time);
fprintf(fid, "Number of samples: %d\n", length(ecg));
fprintf(fid, "Sampling frequency: %.4f Hz\n", Fs);
fprintf(fid, "ESP32 port: %s\n", port);
fprintf(fid, "Baudrate: %d\n", baudrate);
fprintf(fid, "\nSignal: ECG raw\n");

fclose(fid);

%% ============================================================
% FILTRU BAND-PASS ECG
% 0.5 - 40 Hz
% ============================================================

low_cutoff = 0.5;
high_cutoff = 40;

% Proiectam un filtru Butterworth de ordinul 4, tip band-pass.
% Banda 0.5–40 Hz pastreaza componentele utile ale semnalului ECG
% si reduce componentele foarte lente si zgomotul de frecventa mai mare.
[b,a] = butter(4, ...
    [low_cutoff high_cutoff] / (Fs/2), ...
    'bandpass');

% filtfilt aplica filtrarea inainte si inapoi, evitand deplasarea
% de faza a semnalului ECG.
ecg_filtered = filtfilt(b, a, ecg);

%% ============================================================
% SALVARE ECG FILTRAT
% ============================================================
filtered_table = table( ...
    time, ...
    ecg_filtered, ...
    'VariableNames', ...
    {'Time_s','ECG_filtered_ADC'} ...
);
filtered_file = fullfile( ...
    record_folder, ...
    "ECG_filtered.csv" ...
);
writetable( ...
    filtered_table, ...
    filtered_file ...
);

%% ============================================================
% PREPROCESARE PENTRU DETECTAREA QRS
% Metoda: filtru + derivare + patrat + integrare
% ============================================================
qrs_low = 5;
qrs_high = 25;

[b_qrs, a_qrs] = butter(3, ...
    [qrs_low qrs_high] / (Fs/2), ...
    'bandpass');

% Pentru detectia QRS folosim o banda mai ingusta, 5–25 Hz,
% concentrata pe componentele rapide ale complexului QRS.
ecg_qrs = filtfilt( ...
    b_qrs, ...
    a_qrs, ...
    ecg_filtered ...
);

%% ============================================================
% DERIVARE
% ============================================================

% Derivarea evidentiaza modificarile rapide ale semnalului,
% caracteristice complexului QRS.
ecg_derivative = diff(ecg_qrs);
ecg_derivative(end+1) = ecg_derivative(end);

%% ============================================================
% RIDICARE LA PATRAT
% ============================================================

% Ridicarea la patrat face toate valorile pozitive si accentueaza
% componentele cu amplitudine mare, utile pentru detectia QRS.
ecg_squared = ecg_derivative .^ 2;

%% ============================================================
% INTEGRARE PE FEREASTRA MOBILA
% ~150 ms
% ============================================================

% Integram energia semnalului pe aproximativ 150 ms,
% o durata potrivita pentru evidentierea complexului QRS.
integration_window = round(0.15 * Fs);
ecg_integrated = movmean( ...
    ecg_squared, ...
    integration_window ...
);

%% ============================================================
% DETECTARE R-PEAKS
% ============================================================
fprintf('\n');
fprintf('============================================================\n');
fprintf('DETECTARE R-PEAKS\n');
fprintf('============================================================\n');

% Folosim Fs calculat din timpul real al achizitiei.
% Detectia se face pe ECG filtrat, iar ecg_integrated este
% folosit pentru verificarea activitatii QRS.

% Semnalul filtrat este transformat intr-un vector coloana.
% Valorile nevalide sunt inlocuite pentru a evita erori la findpeaks.
x = ecg_filtered(:);
x(~isfinite(x)) = 0;
r_locs = [];
r_values = [];
threshold = NaN;
if isempty(x) || length(x) < 10
    warning('Semnalul ECG filtrat este prea scurt sau invalid.');
else
    % Eliminare lenta a baseline-ului
    % Estimam si eliminam variatia lenta a liniei de baza.
% Fereastra este de aproximativ 200 ms.
    baseline_window = max(3, round(0.20 * Fs));
    baseline = movmedian(x, baseline_window);
    x_clean = x - baseline;

    % Prag adaptiv robust
    med_x = median(x_clean);
    abs_dev = abs(x_clean - med_x);
    robust_noise = median(abs_dev);
    signal_max = max(x_clean);
    signal_range = signal_max - med_x;

    if ~isfinite(robust_noise) || robust_noise <= 0
        robust_noise = max(std(x_clean), eps);
    end
    if ~isfinite(signal_range) || signal_range <= 0
        signal_range = max(x_clean) - min(x_clean);
    end

    % Calculam un prag adaptiv. Pragul depinde de nivelul de zgomot
% si de amplitudinea semnalului, astfel incat sa nu fie fix pentru
% toate inregistrarile.
    threshold = med_x + max(4 * robust_noise, 0.12 * signal_range);

    % Distanta minima: 0.35 s (permite HR pana la ~171 bpm)
    % Impunem o distanta minima intre doua varfuri detectate.
% 0.35 s limiteaza aparitia unor R-peaks prea apropiate.
    min_distance = max(1, round(0.35 * Fs));

    % Detectie principala
    % Detectam candidatii pentru R-peaks folosind semnalul curatat,
% pragul adaptiv si distanta minima dintre varfuri.
    [~, candidate_locs] = findpeaks( ...
        x_clean, ...
        'MinPeakHeight', threshold, ...
        'MinPeakDistance', min_distance);

    % Prag mai relaxat daca avem prea putine batai
    if numel(candidate_locs) < 5
        threshold2 = med_x + max(2.5 * robust_noise, 0.07 * signal_range);
        [~, candidate_locs] = findpeaks( ...
            x_clean, ...
            'MinPeakHeight', threshold2, ...
            'MinPeakDistance', min_distance);
        threshold = threshold2;
    end

    % Fallback pe prominence
    if numel(candidate_locs) < 5
        prominence = max(0.04 * signal_range, 2 * robust_noise, eps);
        [~, candidate_locs] = findpeaks( ...
            x_clean, ...
            'MinPeakProminence', prominence, ...
            'MinPeakDistance', min_distance);
    end

    % Relocalizare exacta pe varful pozitiv al ECG-ului filtrat
    search_window = max(1, round(0.08 * Fs));
    for k = 1:length(candidate_locs)
        left = max(1, candidate_locs(k) - search_window);
        right = min(length(x_clean), candidate_locs(k) + search_window);
        segment = x_clean(left:right);
        [~, local_max] = max(segment);
        real_peak = left + local_max - 1;
        r_locs(end+1,1) = real_peak; %#ok<SAGROW>
    end

    % Eliminare duplicate
    if ~isempty(r_locs)
        r_locs = sort(unique(r_locs));
        keep = true(size(r_locs));
        for k = 2:length(r_locs)
            if (r_locs(k) - r_locs(k-1)) < min_distance
                keep(k) = false;
            end
        end
        r_locs = r_locs(keep);
    end

    % Verificare optionala cu QRS integrat
    if ~isempty(r_locs) && ~isempty(ecg_integrated)
        qrs_window = max(1, round(0.12 * Fs));
        qrs_median_value = median(ecg_integrated);
        qrs_max_value = max(ecg_integrated);
        qrs_range_value = qrs_max_value - qrs_median_value;

        if isfinite(qrs_range_value) && qrs_range_value > 0
            qrs_threshold = qrs_median_value + 0.05 * qrs_range_value;
            keep_qrs = false(size(r_locs));
            for k = 1:length(r_locs)
                left = max(1, r_locs(k) - qrs_window);
                right = min(length(ecg_integrated), r_locs(k) + qrs_window);
                keep_qrs(k) = max(ecg_integrated(left:right)) >= qrs_threshold;
            end
            r_locs = r_locs(keep_qrs);
        end
    end

    if ~isempty(r_locs)
        r_values = ecg_filtered(r_locs);
    end
end

fprintf('R-peaks detectate : %d\n', length(r_locs));
fprintf('Prag detectie      : %.4f\n', threshold);

%% ============================================================
% R-PEAK VALUES
% ============================================================

% Convertim pozitiile esantioanelor R-peak in momente de timp.
r_times = time(r_locs);
r_values = ecg_filtered(r_locs);

%% ============================================================
% SALVARE R-PEAKS
% ============================================================
beat_number = (1:length(r_locs))';
R_peak_index = r_locs(:);
R_peak_time = r_times(:);
R_peak_value = r_values(:);

R_peaks_table = table( ...
    beat_number, ...
    R_peak_index, ...
    R_peak_time, ...
    R_peak_value, ...
    'VariableNames', ...
    {'Beat','R_peak_index','R_peak_time_s','R_peak_value_ADC'} ...
);

R_peaks_file = fullfile( ...
    record_folder, ...
    "R_peaks_" + record_name + ".csv" ...
);
writetable( ...
    R_peaks_table, ...
    R_peaks_file ...
);

%% ============================================================
% CALCUL RR + HR + HRV
% ============================================================
if length(r_times) >= 3
% Intervalele RR reprezinta timpul dintre doua R-peaks consecutive.
    RR = diff(r_times);
% Frecventa cardiaca pentru fiecare interval RR:
% HR [bpm] = 60 / RR [s].
    HR = 60 ./ RR;

    HR_mean = mean(HR);
    HR_min = min(HR);
    HR_max = max(HR);

    RR_mean = mean(RR);

    %% ========================================================
    % HRV - dupa primele 5 secunde
    % ========================================================
    hrv_start_time = 5;
    rr_times = r_times(1:end-1);
    valid_rr = rr_times >= hrv_start_time;
    RR_HRV = RR(valid_rr);
    rr_times_hrv = rr_times(valid_rr);
    RR_ms = RR_HRV * 1000;

    %% ========================================================
    % SDNN
    % ========================================================

    if length(RR_ms) >= 2
        % SDNN este abaterea standard a intervalelor RR exprimate in ms
% si descrie variabilitatea globala a ritmului cardiac.
        SDNN = std(RR_ms);
    else
        SDNN = NaN;
    end

    %% ========================================================
    % RMSSD
    % ========================================================

    if length(RR_ms) >= 2

        diff_RR_ms = diff(RR_ms);
        % RMSSD cuantifica variabilitatea pe termen scurt a intervalelor RR.
        RMSSD = sqrt(mean(diff_RR_ms.^2));
    else
        RMSSD = NaN;
    end

    %% ========================================================
    % pNN50
    % ========================================================

    if length(RR_ms) >= 2
% Numaram diferentele consecutive intre intervalele RR mai mari
% de 50 ms pentru calculul indicatorului pNN50.
        NN50 = sum(abs(diff_RR_ms) > 50);
        pNN50 = ...
            (NN50 / length(diff_RR_ms)) * 100;
    else
        pNN50 = NaN;
    end
else
    RR = [];
    HR = [];

    HR_mean = NaN;
    HR_min = NaN;
    HR_max = NaN;
    RR_mean = NaN;

    hrv_start_time = 5;
    RR_HRV = [];

    SDNN = NaN;
    RMSSD = NaN;
    pNN50 = NaN;

end

%% ============================================================
% EXTRAGERE CARACTERISTICI PENTRU RANDOM FOREST V4
% ============================================================

% Datasetul AI:
% 200 ms inainte de R-peak
% 400 ms dupa R-peak
% 217 esantioane ECG / bataie
%
% 217 caracteristici ECG
% + RR precedent
% + RR urmator
% + HR
% + amplitudinea R
% = 221 caracteristici

% Pentru fiecare bataie extragem o fereastra ECG de la 200 ms
% inaintea R-peak pana la 400 ms dupa R-peak.
% Fiecare bataie este apoi reprezentata prin 217 esantioane.
PRE_MS = 200;
POST_MS = 400;
N_ECG = 217;

if length(r_locs) >= 3
    RR = diff(r_times);
    valid_beats = 2:(length(r_locs)-1);
    AI_features = [];

    for k = valid_beats

        %% ----------------------------------------------------
        % FEREASTRA ECG
        % -----------------------------------------------------
        peak_time = time(r_locs(k));
        start_time_beat = ...
            peak_time - PRE_MS/1000;
        end_time_beat = ...
            peak_time + POST_MS/1000;
        idx = ...
            time >= start_time_beat & ...
            time <= end_time_beat;
        segment_ecg = ecg_filtered(idx);
        if length(segment_ecg) < 10
            continue;
        end

        %% ----------------------------------------------------
        % RESAMPLARE LA 217 ESANTIOANE
        % -----------------------------------------------------
        original_time = linspace( ...
            0, ...
            1, ...
            length(segment_ecg) ...
        );
        target_time = linspace( ...
            0, ...
            1, ...
            N_ECG ...
        );

        % Resamplam fiecare bataie la exact 217 valori.
% Astfel, toate bataile au aceeasi dimensiune si pot fi introduse
% in modelul Random Forest.
        segment_resampled = interp1( ...
            original_time, ...
            segment_ecg, ...
            target_time, ...
            'linear' ...
        );

        %% ----------------------------------------------------
        % RR PRECEDENT
        % -----------------------------------------------------
        rr_prev_ms = ...
            (r_times(k) - r_times(k-1)) * 1000;

        %% ----------------------------------------------------
        % RR URMATOR
        % -----------------------------------------------------
        rr_next_ms = ...
            (r_times(k+1) - r_times(k)) * 1000;

        %% ----------------------------------------------------
        % HR
        % -----------------------------------------------------

        % Calculam HR-ul asociat bataii pe baza intervalului RR precedent.
% 60000 transforma milisecundele in batai pe minut.
        hr_bpm = 60000 / rr_prev_ms;

        %% ----------------------------------------------------
        % AMPLITUDINE R
        % -----------------------------------------------------
        r_amplitude = ecg(r_locs(k));

        %% ----------------------------------------------------
        % RAND FINAL
        % -----------------------------------------------------

        % Construim randul final de caracteristici pentru o bataie:
% 217 valori ECG + RR precedent + RR urmator + HR + amplitudinea R
% = 221 caracteristici.
        new_row = [ ...
            segment_resampled, ...
            rr_prev_ms, ...
            rr_next_ms, ...
            hr_bpm, ...
            r_amplitude ...
        ];

        AI_features = [ ...
            AI_features; ...
            new_row ...
        ];

    end
else
    AI_features = zeros(0, N_ECG + 4);
end

%% ============================================================
% NUME CARACTERISTICI AI
% ============================================================
ecg_names = strings(1, N_ECG);

for i = 1:N_ECG
    ecg_names(i) = "ecg_" + string(i-1);
end
extra_names = [ ...
    "rr_prev_ms", ...
    "rr_next_ms", ...
    "hr_bpm", ...
    "r_amplitude" ...
];
feature_names = [ ...
    ecg_names, ...
    extra_names ...
];

%% ============================================================
% VERIFICARE 221 CARACTERISTICI
% ============================================================

% Verificam explicit compatibilitatea cu modelul Random Forest.
% Daca numarul de caracteristici nu este 221, programul se opreste
% pentru a evita trimiterea unor date incompatibile catre Python.
if size(AI_features, 2) ~= 221
    error( ...
        "Numarul de caracteristici AI este %d, dar modelul asteapta 221.", ...
        size(AI_features, 2) ...
    );
end

%% ============================================================
% CREARE TABEL AI
% ============================================================
AI_table = array2table( ...
    AI_features, ...
    'VariableNames', ...
    feature_names ...
);

%% ============================================================
% SALVARE AI FEATURES
% ============================================================
ai_file = fullfile( ...
    record_folder, ...
    "AI_features_" + record_name + ".csv" ...
);
writetable( ...
    AI_table, ...
    ai_file ...
);

%% ============================================================
% SALVARE REZUMAT ECG PENTRU PYTHON
% ============================================================

% Python foloseste acest fisier pentru HR/HRV.
% Activitatea este completata ulterior de utilizator in Python.

% Construim un rezumat cu valorile principale ale inregistrarii.
% Acest fisier este citit ulterior de aplicatia Python.
ECG_summary = table( ...
    string(record_name), ...
    "Pending", ...
    height(AI_table), ...
    length(r_times), ...
    height(AI_table), ...
    HR_mean, ...
    HR_min, ...
    HR_max, ...
    RR_mean, ...
    min_or_nan(RR), ...
    max_or_nan(RR), ...
    SDNN, ...
    RMSSD, ...
    pNN50, ...
    'VariableNames', { ...
        'Record', ...
        'Activitate', ...
        'Numar_batai_AI', ...
        'Numar_R_peaks', ...
        'Numar_batai_utilizate', ...
        'HR_mediu_bpm', ...
        'HR_min_bpm', ...
        'HR_max_bpm', ...
        'RR_mediu_s', ...
        'RR_min_s', ...
        'RR_max_s', ...
        'SDNN_ms', ...
        'RMSSD_ms', ...
        'pNN50_percent' ...
    } ...
);
summary_file = fullfile( ...
    record_folder, ...
    "ECG_analysis_summary_" + record_name + ".csv" ...
);
writetable( ...
    ECG_summary, ...
    summary_file ...
);

%% ============================================================
% ACTUALIZARE DATABASE.CSV
% ============================================================
database_file = fullfile( ...
    database_folder, ...
    "database.csv" ...
);

Record_ID = string(record_name);
Date = datetime("now");
Requested_Duration_s = durata;
Measured_Duration_s = elapsed_time;
Samples = length(ecg);
Sampling_Frequency_Hz = Fs;
AI_Result = "Pending";

new_row = table( ...
    Record_ID, ...
    Date, ...
    Requested_Duration_s, ...
    Measured_Duration_s, ...
    Samples, ...
    Sampling_Frequency_Hz, ...
    AI_Result ...
);

% Daca baza database.csv exista, adaugam noul record.
% Daca nu exista, cream baza pornind de la primul record.
if isfile(database_file)
    database = readtable(database_file);
    database = [
        database;
        new_row
    ];
else
    database = new_row;
end

writetable(database,database_file);

%% ============================================================
% GRAFIC DIAGNOSTIC - ECG RAW SI FILTRAT
% ============================================================

% Grafic diagnostic pentru compararea semnalului ECG brut cu cel filtrat.
figure;
plot( ...
    time, ...
    ecg, ...
    'LineWidth', 0.8 ...
);
hold on;
plot( ...
    time, ...
    ecg_filtered, ...
    'LineWidth', 0.8 ...
);
xlabel("Timp [s]");
ylabel("ECG [ADC]");
title( ...
    "ECG RAW + FILTRAT - " + record_name ...
);
grid on;
legend( ...
    "ECG RAW", ...
    "ECG filtrat" ...
);
xlim([0 time(end)]);
hold off;

%% ============================================================
% AFISARE REZULTATE
% ============================================================
fprintf("\n============================================================\n");
fprintf("              ECG_READER_FINAL - FINALIZAT\n");
fprintf("============================================================\n");

fprintf("Record: %s\n", record_name);

fprintf("\nFISIERE GENERATE:\n");
fprintf("ECG RAW:\n%s\n", ecg_file);
fprintf("\nECG FILTRAT:\n%s\n", filtered_file);
fprintf("\nR-PEAKS:\n%s\n", R_peaks_file);
fprintf("\nAI FEATURES:\n%s\n", ai_file);
fprintf("\nREZUMAT ECG:\n%s\n", summary_file);
fprintf("\nBAZA DE DATE:\n%s\n", database_file);

% Afisam in Command Window valorile finale ale analizei,
% astfel incat rezultatele MATLAB sa poata fi verificate rapid.
fprintf("\nREZULTATE ECG:\n");
fprintf("--------------------------------------------\n");
fprintf("R-peaks detectate : %d\n", length(r_times));
fprintf("Batai pentru AI   : %d\n", height(AI_table));
fprintf("HR mediu          : %.2f bpm\n", HR_mean);
fprintf("HR minim          : %.2f bpm\n", HR_min);
fprintf("HR maxim          : %.2f bpm\n", HR_max);
fprintf("RR mediu          : %.4f s\n", RR_mean);
fprintf("SDNN              : %.2f ms\n", SDNN);
fprintf("RMSSD             : %.2f ms\n", RMSSD);
fprintf("pNN50             : %.2f %%\n", pNN50);

fprintf("\nCaracteristici AI : %d\n", width(AI_table));

fprintf("\n============================================================\n");
fprintf("DATELE SUNT PREGATITE PENTRU PYTHON / RANDOM FOREST\n");
fprintf("============================================================\n");

%% ============================================================
% FUNCTII LOCALE
% ============================================================
function value = min_or_nan(x)
    if isempty(x)
        value = NaN;
    else
        value = min(x);
    end

end
function value = max_or_nan(x)
    if isempty(x)
        value = NaN;
    else
        value = max(x);
    end
end
