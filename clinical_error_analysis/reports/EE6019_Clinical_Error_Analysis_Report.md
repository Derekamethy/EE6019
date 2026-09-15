# EE6019 Clinical Error Analysis and Targeted Refinement Report

## 1. Known limitations of the current detector
- Artifact robustness currently comes mainly from band-pass filtering and the minimum-duration rule; no dedicated artifact classifier is used.
- High sensitivity therefore does not automatically imply robust event detection: some patients can still show substantial delay or non-trivial false alarms.
- This analysis focuses on delayed detections in `chb04` and false alarms in `chb08`.

## 2. Summary of delayed detections in chb04
- Detected delayed true-positive events: **2**
- Maximum delay: **104.00 s**
- Median delay: **62.00 s**
- These cases show that detecting an event eventually does not guarantee timely detection; the alarm can occur substantially later than the preferred event onset.

## 3. Summary of false alarms in chb08
- False-alarm events in chb08: **15**
- Most common heuristic false-alarm label: **uncertain**
- This analysis asks whether errors are associated with rhythmic non-seizure activity, suspected artifacts, or transition states.

### 3.1 chb08 false-alarm classification summary
fp_reason,Count,Share

uncertain,14,0.9333333333333333

transition_state,1,0.06666666666666667



## 4. TP / FP / FN feature differences
- These comparisons are diagnostic rather than retraining steps; they identify systematic differences in spectral, synchrony, artifact-proxy, and score behaviour across successful and failed events.

### 4.1 Event-type feature summary (selected rows)
EventType,Feature,N,Mean,Median,IQR

FN,delta_power_mean_mean,2,406547850.20958436,406547850.20958436,57440236.58131689

FN,theta_power_mean_mean,2,209431128.71718562,209431128.71718562,103439673.97909617

FN,alpha_power_mean_mean,2,64565847.59274955,64565847.59274955,29697889.395351864

FN,beta_power_mean_mean,2,59984943.17503936,59984943.17503936,39143840.40714102

FN,gamma_power_mean_mean,2,20326591.161468633,20326591.161468633,17098128.856314324

FN,synchrony_mean_mean,2,0.38540623788693706,0.38540623788693706,0.03602384521050167

FN,epoch_ptp_median_mean,2,371.43849016858695,371.43849016858695,107.32424507340932

FN,epoch_ptp_max_mean,2,725.9169173902451,725.9169173902451,224.15493087977075

FN,high_amp_channel_count_mean,2,15.155844155844157,15.155844155844157,5.7012987012987

FN,line_length_median_mean,2,10.109172217989176,10.109172217989176,4.176235843823548

FN,broadband_lowfreq_ratio_mean,2,0.11444866653816861,0.11444866653816861,0.06726075614774804

FN,score_mean,2,0.09655815395369291,0.09655815395369291,0.08147645927114883



### 4.2 Event-type effect-size ranking (selected rows)
Comparison,Feature,Mean_Left,Mean_Right,StdDiff,AbsStdDiff

TP vs FN,score_peak,0.9162750488592728,0.1485148497347037,5.465089323227287,5.465089323227287

TP vs FN,score_mean,0.7525817427166999,0.09655815395369291,4.181988745751156,4.181988745751156

TP vs FN,duration_s,78.34615384615384,18.0,1.7186954663899137,1.7186954663899137

TP vs FN,delta_power_mean_mean,1352604668.440553,406547850.20958436,1.5380542024742792,1.5380542024742792

TP vs FN,epoch_ptp_max_mean,1162.6566938621193,725.9169173902451,1.1287618702217022,1.1287618702217022

TP vs FN,epoch_ptp_median_mean,616.2785756577122,371.43849016858695,1.0974754407261476,1.0974754407261476

TP vs FN,line_length_median_mean,19.081886570357376,10.109172217989176,1.0400214573341837,1.0400214573341837

TP vs FN,theta_power_mean_mean,782365188.3366026,209431128.71718562,0.9146513738869626,0.9146513738869626



## 5. Targeted refinement experiments
- Candidate variants keep the final tuned RF configuration (`top_k=30` and RF hyperparameters) fixed and change only input features or post-processing.
- Variants are first screened on `chb04 / chb08`, then the selected candidate is checked across all 10 patients.

### 5.1 Focus-patient comparison
Patient,Model,TopK,Hours,True_Seizures,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,Median_Threshold,FP_events,Variant

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5918867669464123,35.5,15.0,0.551,89,baseline_rf_top30

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7497709033350921,11.2,12.0,0.464,15,baseline_rf_top30

chb04,random_forest,30,156.06333333333333,4.0,1.0,0.37805164569939553,51.0,50.0,0.724,59,sync_expanded_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7997556302240982,9.2,10.0,0.412,15,sync_expanded_rf

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.24333122641130286,35.5,15.0,0.603,37,artifact_aware_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.6498014495570799,9.6,10.0,0.36,13,artifact_aware_rf

chb04,random_forest,30,156.06333333333333,4.0,0.75,0.44212819581793716,36.666666666666664,8.0,0.759,69,clean_subset_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.5998167226680736,10.0,10.0,0.464,11,clean_subset_rf



### 5.2 Variant ranking
Variant,chb08_far_improvement,chb04_delay_improvement,focus_fp_event_improvement,passes_sensitivity_guard

artifact_aware_rf,0.09996945377801225,0.0,54,True

sync_expanded_rf,-0.049984726889006126,-15.5,30,True



### 5.3 All 10 patients: baseline vs selected variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,Selected_Best_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False

artifact_aware_rf,MACRO,10,0.7873015873015873,0.1853784372906424,8.452910052910052,6.0,125,True



## 6. Should the refinement be adopted into the main model?
- Automatically selected single best variant: **artifact_aware_rf**
- Relative to baseline, the selected variant changes macro Sensitivity by -0.1905, FAR/hr by -0.2054, and Mean Delay by -1.5023 s.
- This result is better interpreted as a locally effective targeted repair; adoption into the main model still requires caution.

## 7. Critical interpretation
- Aggregate sensitivity alone can hide patient-specific failure modes.
- `chb04` shows that detecting a seizure is not equivalent to detecting it promptly; delay is itself an important event-level error.
- `chb08` shows that false alarms are not always simple noise; some may correspond to rhythmic non-seizure activity, transition states, or high-amplitude artifacts.
- A more useful next step is therefore explicit artifact handling, improved synchrony features, and case-level interpretation rather than blind RF hyperparameter tuning.

## 8. Exported evidence index
- chb04_delay_events_df: <LOCAL_EXPORT_PATH>
- chb08_fp_events_df: <LOCAL_EXPORT_PATH>
- clinical_case_export_df: <LOCAL_EXPORT_PATH>
- chb08_fp_labeled_df: <LOCAL_EXPORT_PATH>
- fp_reason_summary_df: <LOCAL_EXPORT_PATH>
- event_type_feature_summary_df: <LOCAL_EXPORT_PATH>
- event_type_effect_size_df: <LOCAL_EXPORT_PATH>
- focus_variant_compare_df: <LOCAL_EXPORT_PATH>
- focus_variant_macro_df: <LOCAL_EXPORT_PATH>
- variant_ranking_df: <LOCAL_EXPORT_PATH>
- best_variant_global_df: <LOCAL_EXPORT_PATH>
- best_variant_vs_baseline_df: <LOCAL_EXPORT_PATH>
- Markdown report: <LOCAL_EXPORT_PATH>
