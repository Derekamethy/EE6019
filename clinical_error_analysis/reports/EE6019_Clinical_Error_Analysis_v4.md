# EE6019 Clinical Error Analysis v4

## 1. Scope
- This v4 notebook does not reopen the broader search space. It only tests two minimal add-back variants around the v3 `proxy_hybrid_rf` idea.
- The purpose is narrow: recover the single missed `chb04` seizure without giving away the FAR gains already seen on `chb08` and `chb06`.
- No DL branch, no parameter scan, and no new multi-model comparison are introduced here.

## 2. Baseline reconciliation
- Three baselines are compared side by side: the legacy baseline notebook output, the original clinical notebook output, and the freshly executed v4 baseline.
Patient,legacy_baseline_Hours,legacy_baseline_True_Seizures,legacy_baseline_Sensitivity,legacy_baseline_FAR_per_Hour,legacy_baseline_Mean_Delay_s,legacy_baseline_Median_Delay_s,legacy_baseline_Median_Threshold,legacy_clinical_Hours,legacy_clinical_True_Seizures,legacy_clinical_Sensitivity,legacy_clinical_FAR_per_Hour,legacy_clinical_Mean_Delay_s,legacy_clinical_Median_Delay_s,legacy_clinical_Median_Threshold,current_v4_Hours,current_v4_True_Seizures,current_v4_Sensitivity,current_v4_FAR_per_Hour,current_v4_Mean_Delay_s,current_v4_Median_Delay_s,current_v4_Median_Threshold,legacy_baseline_minus_current_v4_Hours,legacy_baseline_minus_current_v4_True_Seizures,legacy_baseline_minus_current_v4_Sensitivity,legacy_baseline_minus_current_v4_FAR_per_Hour,legacy_baseline_minus_current_v4_Mean_Delay_s,legacy_baseline_minus_current_v4_Median_Delay_s,legacy_baseline_minus_current_v4_Median_Threshold,legacy_clinical_minus_current_v4_Hours,legacy_clinical_minus_current_v4_True_Seizures,legacy_clinical_minus_current_v4_Sensitivity,legacy_clinical_minus_current_v4_FAR_per_Hour,legacy_clinical_minus_current_v4_Mean_Delay_s,legacy_clinical_minus_current_v4_Median_Delay_s,legacy_clinical_minus_current_v4_Median_Threshold

MACRO,580.57,55.0,0.98,0.245475,10.644524,5.0,0.5855,564.563333,54.0,0.977778,0.390748,9.955238,5.0,0.525,564.5633333333333,54.0,0.977777777777778,0.3907476071881233,9.955238095238096,5.0,0.525,16.006666666666774,1.0,0.0022222222222221,-0.1452726071881233,0.6892859047619044,0.0,0.0605,-3.333333324917476e-07,0.0,2.2222222217926915e-07,3.928118766372002e-07,-9.523809652023375e-08,0.0,0.0

chb01,40.551667,7.0,1.0,0.665817,4.285714,2.0,0.499,40.551667,7.0,1.0,0.665817,4.285714,2.0,0.499,40.55166666666667,7.0,1.0,0.6658172701491923,4.285714285714286,2.0,0.499,3.333333324917476e-07,0.0,0.0,-2.70149192349578e-07,-2.857142860079876e-07,0.0,0.0,3.333333324917476e-07,0.0,0.0,-2.70149192349578e-07,-2.857142860079876e-07,0.0,0.0

chb02,35.266111,3.0,1.0,0.255203,3.333333,4.0,0.308,35.266111,3.0,1.0,0.255203,3.333333,4.0,0.308,35.26611111111111,3.0,1.0,0.2552025079160037,3.333333333333333,4.0,0.308,-1.1111110609363096e-07,0.0,0.0,4.92083996272985e-07,-3.33333333379926e-07,0.0,0.0,-1.1111110609363096e-07,0.0,0.0,4.92083996272985e-07,-3.33333333379926e-07,0.0,0.0

chb03,38.001667,7.0,1.0,0.526293,4.0,2.0,0.672,38.001667,7.0,1.0,0.526293,4.0,2.0,0.672,38.001666666666665,7.0,1.0,0.526292706460243,4.0,2.0,0.672,3.333333324917476e-07,0.0,0.0,2.935397570569265e-07,0.0,0.0,0.0,3.333333324917476e-07,0.0,0.0,2.935397570569265e-07,0.0,0.0,0.0

chb04,156.063333,4.0,1.0,0.422905,41.0,25.0,0.742,152.056111,4.0,1.0,0.591887,35.5,15.0,0.551,152.0561111111111,4.0,1.0,0.5918867669464123,35.5,15.0,0.551,4.007221888888893,0.0,0.0,-0.1689817669464123,5.5,10.0,0.1909999999999999,-1.1111112030448569e-07,0.0,0.0,2.330535877614892e-07,0.0,0.0,0.0

chb05,39.002778,5.0,1.0,0.179474,12.4,6.0,0.482,39.002778,5.0,1.0,0.179474,12.4,6.0,0.482,39.00277777777778,5.0,1.0,0.179474396410512,12.4,6.0,0.482,2.222222192926893e-07,0.0,0.0,-3.964105120546346e-07,0.0,0.0,0.0,2.222222192926893e-07,0.0,0.0,-3.964105120546346e-07,0.0,0.0,0.0

chb06,66.734444,10.0,0.8,0.089909,4.25,4.0,0.308,62.734444,9.0,0.777778,0.79701,2.857143,4.0,0.204,62.73444444444444,9.0,0.7777777777777778,0.7970103257115532,2.857142857142857,4.0,0.204,3.9999995555555534,1.0,0.0222222222222222,-0.7071013257115532,1.3928571428571428,0.0,0.1039999999999999,-4.444444385853785e-07,0.0,2.2222222217926915e-07,-3.257115531729582e-07,1.4285714300399377e-07,0.0,-2.775557561562892e-17

chb07,67.051667,3.0,1.0,0.089483,15.333333,18.0,0.69,67.051667,3.0,1.0,0.089483,15.333333,18.0,0.69,67.05166666666666,3.0,1.0,0.0894832343217916,15.333333333333334,18.0,0.69,3.333333324917476e-07,0.0,0.0,-2.3432179166449354e-07,-3.333333342681044e-07,0.0,0.0,3.333333324917476e-07,0.0,0.0,-2.3432179166449354e-07,-3.333333342681044e-07,0.0,0.0

chb08,20.006111,5.0,1.0,0.749771,11.2,12.0,0.464,20.006111,5.0,1.0,0.749771,11.2,12.0,0.464,20.00611111111111,5.0,1.0,0.7497709033350921,11.2,12.0,0.464,-1.1111110964634464e-07,0.0,0.0,9.666490785598115e-08,0.0,0.0,0.0,-1.1111110964634464e-07,0.0,0.0,9.666490785598115e-08,0.0,0.0,0.0

chb09,67.869444,4.0,1.0,0.235747,7.5,6.0,0.69,59.87,4.0,1.0,0.217137,7.5,6.0,0.811,59.87,4.0,1.0,0.2171371304493068,7.5,6.0,0.811,7.999444000000004,0.0,0.0,0.0186098695506931,0.0,0.0,-0.1210000000000001,0.0,0.0,0.0,-1.3044930685657266e-07,0.0,0.0,0.0

chb10,50.022778,7.0,1.0,0.119945,3.142857,4.0,0.811,50.022778,7.0,1.0,0.119945,3.142857,4.0,0.811,50.022777777777776,7.0,1.0,0.1199453582256971,3.142857142857143,4.0,0.811,2.2222222639811667e-07,0.0,0.0,-3.5822569718901853e-07,-1.4285714300399377e-07,0.0,0.0,2.2222222639811667e-07,0.0,0.0,-3.5822569718901853e-07,-1.4285714300399377e-07,0.0,0.0



- Inference: the mismatch is still most consistent with evaluation-path drift rather than cache-schema drift, because the parser and cache builder appear aligned while `evaluate_patient_loso` differs between notebooks.
- Diagnostic checks:
Check,LegacyBaseline,LegacyClinical,Match,Interpretation

CACHE_SCHEMA_VERSION,v2_summary_parser_fix,v2_summary_parser_fix,True,Same schema assignment argues against a parser-schema mismatch.

parse_summary_to_dict,present,present,True,Summary parser alignment

build_patient_cache,present,present,True,Cache construction alignment

sample_rows_from_matrix_index,missing,present,False,Training row sampling helper alignment

collect_rows_from_matrix_index,present,present,True,Evaluation row collection helper alignment

evaluate_patient_loso,present,present,False,Fold evaluation logic alignment



## 3. Error-analysis anchors
- `chb04` late-TP cases above the delay threshold: **2**
- `chb08` FP events under review: **15**
- Interpretation target: `chb04` is still treated as a delayed-detection problem, while `chb08` is treated as an FP-burden problem.

## 4. FP taxonomy quality
fp_reason,Count,Share

uncertain,14,0.9333333333333333

transition_state,1,0.06666666666666667


- The taxonomy is still descriptive only, because the uncertain share remains too high for direct model-selection use.

## 5. Feature-level contrast between TP / FP / FN
- v4 uses the same TP-vs-FP and TP-vs-FN effect-size evidence from v3, but only for targeted add-back design.
Comparison,Feature,Mean_Left,Mean_Right,StdDiff,AbsStdDiff

TP vs FN,score_peak,0.9162750488592728,0.1485148497347037,5.465089323227287,5.465089323227287

TP vs FN,score_mean,0.7525817427166999,0.09655815395369291,4.181988745751156,4.181988745751156

TP vs FN,duration_s,78.34615384615384,18.0,1.7186954663899137,1.7186954663899137

TP vs FN,delta_power_mean_mean,1352604668.440553,406547850.20958436,1.5380542024742792,1.5380542024742792

TP vs FN,epoch_ptp_max_mean,1162.6566938621193,725.9169173902451,1.1287618702217022,1.1287618702217022

TP vs FN,epoch_ptp_median_mean,616.2785756577122,371.43849016858695,1.0974754407261476,1.0974754407261476

TP vs FN,line_length_median_mean,19.081886570357376,10.109172217989176,1.0400214573341837,1.0400214573341837

TP vs FN,theta_power_mean_mean,782365188.3366026,209431128.71718562,0.9146513738869626,0.9146513738869626



## 6. Proxy subset ablation on focus patients
- `proxy_hybrid_plus_median_rf` adds back `epoch_ptp_median` to the three-feature v3 hybrid core.
- `proxy_hybrid_plus_count_rf` adds back `high_amp_channel_count` to the same hybrid core.
- Both variants are intentionally minimal so that the v4 question stays focused on `chb04` recovery.
Patient,Model,TopK,Hours,True_Seizures,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,Median_Threshold,FP_events,Variant,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Baseline_Sensitivity,Baseline_FAR_per_Hour,Baseline_Mean_Delay_s,Baseline_Median_Delay_s,Baseline_FP_events,SensitivityDelta_vs_Baseline,FARDelta_vs_Baseline,DelayDelta_vs_Baseline,FPEventDelta_vs_Baseline

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5918867669464123,35.5,15.0,0.551,89,baseline_rf_top30,False,baseline,0,1.0,0.5918867669464123,35.5,15.0,89,0.0,0.0,0.0,0

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7497709033350921,11.2,12.0,0.464,15,baseline_rf_top30,False,baseline,0,1.0,0.7497709033350921,11.2,12.0,15,0.0,0.0,0.0,0

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5063920117208195,53.0,49.0,0.568,77,proxy_hybrid_plus_median_rf,True,hybrid_plus_ptp_median,4,1.0,0.5918867669464123,35.5,15.0,89,0.0,-0.0854947552255928,17.5,-12

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.349893088223043,10.4,10.0,0.482,7,proxy_hybrid_plus_median_rf,True,hybrid_plus_ptp_median,4,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.3998778151120491,-0.7999999999999989,-8

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5063920117208195,53.0,49.0,0.568,77,proxy_hybrid_plus_count_rf,True,hybrid_plus_amp_count,4,1.0,0.5918867669464123,35.5,15.0,89,0.0,-0.0854947552255928,17.5,-12

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.24992363444503068,10.8,12.0,0.499,5,proxy_hybrid_plus_count_rf,True,hybrid_plus_amp_count,4,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.4998472688900614,-0.3999999999999986,-10



## 7. Focus ranking and global transfer
- Best focus-only candidate: **proxy_hybrid_plus_count_rf**
Variant,passes_focus_sensitivity_guard,focus_fp_event_improvement,chb08_far_improvement,chb04_delay_improvement,focus_macro_sensitivity_delta,focus_macro_far_delta,focus_macro_delay_delta,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount

proxy_hybrid_plus_count_rf,True,22,0.4998472688900614,-17.5,0.0,-0.2926710120578271,8.549999999999997,True,hybrid_plus_amp_count,4

proxy_hybrid_plus_median_rf,True,20,0.3998778151120491,-17.5,0.0,-0.24268628516882096,8.349999999999998,True,hybrid_plus_ptp_median,4



### 7.1 Global guard results
Variant,MacroSensitivity,MacroFAR_per_Hour,MacroMeanDelay_s,MacroSensitivityDelta,MacroFARDelta,chb08_far_delta,chb04_delay_delta,new_zero_sensitivity_count,new_zero_sensitivity_patients,passes_zero_guard,passes_macro_sensitivity_guard,passes_macro_far_guard,passes_chb08_far_guard,passes_chb04_delay_guard,passes_global_guard,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount

proxy_hybrid_plus_count_rf,0.9666666666666666,0.2809518484430014,11.074761904761903,-0.011111111111111294,-0.10979575874512193,-0.4998472688900614,17.5,0,,True,True,True,True,False,False,True,hybrid_plus_amp_count,4

proxy_hybrid_plus_median_rf,0.9666666666666666,0.3309036322824127,11.07047619047619,-0.011111111111111294,-0.05984397490571064,-0.3998778151120491,17.5,0,,True,True,True,True,False,False,True,hybrid_plus_ptp_median,4



### 7.2 Focus-to-global transfer table
Variant,is_best_focus_variant,is_adopted_global_variant,focus_passes_sensitivity_guard,focus_chb08_far_improvement,focus_chb04_delay_improvement,focus_fp_event_improvement,focus_macro_sensitivity_delta,focus_macro_far_delta,global_macro_sensitivity_delta,global_macro_far_delta,global_chb08_far_delta,global_chb04_delay_delta,global_new_zero_sensitivity_count,passes_global_guard,ProxyRecipe,ProxyFeatureCount

proxy_hybrid_plus_count_rf,True,False,True,0.4998472688900614,-17.5,22,0.0,-0.2926710120578271,-0.011111111111111294,-0.10979575874512193,-0.4998472688900614,17.5,0,False,hybrid_plus_amp_count,4

proxy_hybrid_plus_median_rf,False,False,True,0.3998778151120491,-17.5,20,0.0,-0.24268628516882096,-0.011111111111111294,-0.05984397490571064,-0.3998778151120491,17.5,0,False,hybrid_plus_ptp_median,4



## 8. Adoption decision
- Adopted global variant: **baseline_rf_top30**
- Guard policy: no new zero-sensitivity patient, macro sensitivity drop <= 0.02, macro FAR must decrease, chb08 FAR must decrease, and chb04 delay must not worsen.
- No proxy subset passed the full global guard, so the present conclusion remains diagnostic rather than deployable.

### 8.1 Baseline vs best focus variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Selected_Best_Focus_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False,baseline,0,False

proxy_hybrid_plus_count_rf,MACRO,10,0.9666666666666666,0.2809518484430014,11.074761904761903,5.0,182,True,hybrid_plus_amp_count,4,True



### 8.2 Baseline vs adopted global variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Selected_Adopted_Global_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False,baseline,0,True



### 8.3 Per-patient deltas for the adopted variant
_empty_

## 9. Code validity and leakage checks
- `top-k` features are still selected from inner-train files only.
- Threshold selection is still based on the inner-validation split only.
- No test-event labels are used to define the proxy subsets or the post-processing path.
- The main methodological risk in v4 is still not leakage but repeated focus-driven iteration around `chb04/chb08`.

## 10. Export index
- chb04_delay_events_df: <LOCAL_EXPORT_PATH>
- chb08_fp_events_df: <LOCAL_EXPORT_PATH>
- clinical_case_export_df: <LOCAL_EXPORT_PATH>
- chb08_fp_labeled_df: <LOCAL_EXPORT_PATH>
- fp_reason_summary_df: <LOCAL_EXPORT_PATH>
- event_type_feature_summary_df: <LOCAL_EXPORT_PATH>
- event_type_effect_size_df: <LOCAL_EXPORT_PATH>
- baseline_reconciliation_df: <LOCAL_EXPORT_PATH>
- baseline_reconciliation_notes_df: <LOCAL_EXPORT_PATH>
- focus_variant_compare_df: <LOCAL_EXPORT_PATH>
- focus_variant_macro_df: <LOCAL_EXPORT_PATH>
- variant_component_ablation_df: <LOCAL_EXPORT_PATH>
- variant_ranking_df: <LOCAL_EXPORT_PATH>
- global_variant_compare_df: <LOCAL_EXPORT_PATH>
- global_variant_macro_df: <LOCAL_EXPORT_PATH>
- global_guard_df: <LOCAL_EXPORT_PATH>
- focus_to_global_transfer_df: <LOCAL_EXPORT_PATH>
- best_variant_vs_baseline_df: <LOCAL_EXPORT_PATH>
- adopted_global_variant_vs_baseline_df: <LOCAL_EXPORT_PATH>
- adopted_global_patient_delta_df: not exported
- Markdown memo: <LOCAL_EXPORT_PATH>
