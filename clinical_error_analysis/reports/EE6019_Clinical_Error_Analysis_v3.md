# EE6019 Clinical Error Analysis v3

## 1. Scope
- This v3 notebook continues from the v2 guard-passing direction and iterates only on proxy-feature design.
- Artifact suppression is not extended here because the earlier suppression branch reduced global sensitivity too aggressively.
- The v3 question is narrower: can a smaller proxy set keep the FAR gains while reducing collateral damage on non-focus patients?

## 2. Baseline reconciliation
- Three baselines are compared side by side: the legacy baseline notebook output, the original clinical notebook output, and the freshly executed v3 baseline.
Patient,legacy_baseline_Hours,legacy_baseline_True_Seizures,legacy_baseline_Sensitivity,legacy_baseline_FAR_per_Hour,legacy_baseline_Mean_Delay_s,legacy_baseline_Median_Delay_s,legacy_baseline_Median_Threshold,legacy_clinical_Hours,legacy_clinical_True_Seizures,legacy_clinical_Sensitivity,legacy_clinical_FAR_per_Hour,legacy_clinical_Mean_Delay_s,legacy_clinical_Median_Delay_s,legacy_clinical_Median_Threshold,current_v3_Hours,current_v3_True_Seizures,current_v3_Sensitivity,current_v3_FAR_per_Hour,current_v3_Mean_Delay_s,current_v3_Median_Delay_s,current_v3_Median_Threshold,legacy_baseline_minus_current_v3_Hours,legacy_baseline_minus_current_v3_True_Seizures,legacy_baseline_minus_current_v3_Sensitivity,legacy_baseline_minus_current_v3_FAR_per_Hour,legacy_baseline_minus_current_v3_Mean_Delay_s,legacy_baseline_minus_current_v3_Median_Delay_s,legacy_baseline_minus_current_v3_Median_Threshold,legacy_clinical_minus_current_v3_Hours,legacy_clinical_minus_current_v3_True_Seizures,legacy_clinical_minus_current_v3_Sensitivity,legacy_clinical_minus_current_v3_FAR_per_Hour,legacy_clinical_minus_current_v3_Mean_Delay_s,legacy_clinical_minus_current_v3_Median_Delay_s,legacy_clinical_minus_current_v3_Median_Threshold

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
- v3 uses the TP-vs-FP effect-size table to define smaller proxy subsets.
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
- `proxy_augmented_rf` keeps the full five-feature proxy stack.
- `proxy_hybrid_rf` keeps `epoch_ptp_max`, `line_length_median`, and `broadband_lowfreq_ratio`.
- `proxy_compact_rf` keeps only `line_length_median` and `broadband_lowfreq_ratio`.
Patient,Model,TopK,Hours,True_Seizures,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,Median_Threshold,FP_events,Variant,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Baseline_Sensitivity,Baseline_FAR_per_Hour,Baseline_Mean_Delay_s,Baseline_Median_Delay_s,Baseline_FP_events,SensitivityDelta_vs_Baseline,FARDelta_vs_Baseline,DelayDelta_vs_Baseline,FPEventDelta_vs_Baseline

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5918867669464123,35.5,15.0,0.551,89,baseline_rf_top30,False,baseline,0,1.0,0.5918867669464123,35.5,15.0,89,0.0,0.0,0.0,0

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7497709033350921,11.2,12.0,0.464,15,baseline_rf_top30,False,baseline,0,1.0,0.7497709033350921,11.2,12.0,15,0.0,0.0,0.0,0

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.618192845477364,35.5,15.0,0.603,94,proxy_augmented_rf,True,full_proxy_stack,5,1.0,0.5918867669464123,35.5,15.0,89,0.0,0.026306078530951682,0.0,5

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.6498014495570799,9.6,10.0,0.36,13,proxy_augmented_rf,True,full_proxy_stack,5,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.09996945377801225,-1.5999999999999996,-2

chb04,random_forest,30,152.0561111111111,4.0,0.75,0.4998154920880815,34.666666666666664,10.0,0.586,76,proxy_hybrid_rf,True,ptp_plus_shape,3,1.0,0.5918867669464123,35.5,15.0,89,-0.25,-0.09207127485833078,-0.8333333333333357,-13

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.44986254200105524,10.0,12.0,0.482,9,proxy_hybrid_rf,True,ptp_plus_shape,3,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.29990836133403687,-1.1999999999999993,-6

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5918867669464123,53.5,51.0,0.62,90,proxy_compact_rf,True,shape_ratio_only,2,1.0,0.5918867669464123,35.5,15.0,89,0.0,0.0,18.0,1

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.49984726889006137,9.6,10.0,0.43,10,proxy_compact_rf,True,shape_ratio_only,2,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.24992363444503074,-1.5999999999999996,-5



## 7. Focus ranking and global transfer
- Best focus-only candidate: **proxy_compact_rf**
Variant,passes_focus_sensitivity_guard,focus_fp_event_improvement,chb08_far_improvement,chb04_delay_improvement,focus_macro_sensitivity_delta,focus_macro_far_delta,focus_macro_delay_delta,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount

proxy_compact_rf,True,4,0.24992363444503074,-18.0,0.0,-0.12496181722251543,8.2,True,shape_ratio_only,2

proxy_augmented_rf,True,-3,0.09996945377801225,0.0,0.0,-0.036831687623530285,-0.8000000000000007,True,full_proxy_stack,5

proxy_hybrid_rf,False,19,0.29990836133403687,0.8333333333333357,-0.125,-0.19598981809618382,-1.0166666666666693,True,ptp_plus_shape,3



### 7.1 Global guard results
Variant,MacroSensitivity,MacroFAR_per_Hour,MacroMeanDelay_s,MacroSensitivityDelta,MacroFARDelta,chb08_far_delta,chb04_delay_delta,new_zero_sensitivity_count,new_zero_sensitivity_patients,passes_zero_guard,passes_macro_sensitivity_guard,passes_macro_far_guard,passes_chb08_far_guard,passes_chb04_delay_guard,passes_global_guard,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount

proxy_augmented_rf,0.9777777777777779,0.2575420587025071,9.418571428571429,0.0,-0.13320554848561622,-0.09996945377801225,0.0,0,,True,True,True,True,True,True,True,full_proxy_stack,5

proxy_hybrid_rf,0.9527777777777778,0.2551229060718504,9.633809523809523,-0.025000000000000022,-0.13562470111627295,-0.29990836133403687,-0.8333333333333357,0,,True,False,True,True,True,False,True,ptp_plus_shape,3

proxy_compact_rf,0.9777777777777779,0.4036044353879532,11.34095238095238,0.0,0.012856828199829862,-0.24992363444503074,18.0,0,,True,True,False,True,False,False,True,shape_ratio_only,2



### 7.2 Focus-to-global transfer table
Variant,is_best_focus_variant,is_adopted_global_variant,focus_passes_sensitivity_guard,focus_chb08_far_improvement,focus_chb04_delay_improvement,focus_fp_event_improvement,focus_macro_sensitivity_delta,focus_macro_far_delta,global_macro_sensitivity_delta,global_macro_far_delta,global_chb08_far_delta,global_chb04_delay_delta,global_new_zero_sensitivity_count,passes_global_guard,ProxyRecipe,ProxyFeatureCount

proxy_compact_rf,True,False,True,0.24992363444503074,-18.0,4,0.0,-0.12496181722251543,0.0,0.012856828199829862,-0.24992363444503074,18.0,0,False,shape_ratio_only,2

proxy_augmented_rf,False,True,True,0.09996945377801225,0.0,-3,0.0,-0.036831687623530285,0.0,-0.13320554848561622,-0.09996945377801225,0.0,0,True,full_proxy_stack,5

proxy_hybrid_rf,False,False,False,0.29990836133403687,0.8333333333333357,19,-0.125,-0.19598981809618382,-0.025000000000000022,-0.13562470111627295,-0.29990836133403687,-0.8333333333333357,0,False,ptp_plus_shape,3



## 8. Adoption decision
- Adopted global variant: **proxy_augmented_rf**
- Guard policy: no new zero-sensitivity patient, macro sensitivity drop <= 0.02, macro FAR must decrease, chb08 FAR must decrease, and chb04 delay must not worsen.
- At least one proxy subset passed the full global guard, so the error-analysis direction remains viable and more targeted than the v2 full-stack proxy branch.

### 8.1 Baseline vs best focus variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Selected_Best_Focus_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False,baseline,0,False

proxy_compact_rf,MACRO,10,0.9777777777777779,0.4036044353879532,11.34095238095238,5.0,201,True,shape_ratio_only,2,True



### 8.2 Baseline vs adopted global variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,UsesProxyFeatures,ProxyRecipe,ProxyFeatureCount,Selected_Adopted_Global_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False,baseline,0,False

proxy_augmented_rf,MACRO,10,0.9777777777777779,0.2575420587025071,9.418571428571429,6.0,213,True,full_proxy_stack,5,True



### 8.3 Per-patient deltas for the adopted variant
Patient,Sensitivity_adopted,FAR_per_Hour_adopted,Mean_Delay_s_adopted,Median_Delay_s_adopted,FP_events_adopted,Sensitivity_baseline,FAR_per_Hour_baseline,Mean_Delay_s_baseline,Median_Delay_s_baseline,FP_events_baseline,Sensitivity_delta,FAR_per_Hour_delta,Mean_Delay_s_delta,Median_Delay_s_delta,FP_events_delta

chb01,1.0,0.838436562410094,3.7142857142857144,2.0,31,1.0,0.6658172701491923,4.285714285714286,2.0,23,0.0,0.17261929226090167,-0.5714285714285712,0.0,8

chb02,1.0,0.25520250791600374,4.666666666666667,6.0,8,1.0,0.25520250791600374,3.3333333333333335,4.0,8,0.0,0.0,1.3333333333333335,2.0,0

chb03,1.0,0.6052366124292794,2.857142857142857,0.0,22,1.0,0.526292706460243,4.0,2.0,19,0.0,0.07894390596903644,-1.1428571428571428,-2.0,3

chb04,1.0,0.618192845477364,35.5,15.0,94,1.0,0.5918867669464123,35.5,15.0,89,0.0,0.026306078530951682,0.0,0.0,5

chb05,1.0,0.17947439641051205,10.8,6.0,7,1.0,0.17947439641051205,12.4,6.0,7,0.0,0.0,-1.5999999999999996,0.0,0

chb06,0.7777777777777778,0.19128247817077276,3.4285714285714284,4.0,10,0.7777777777777778,0.7970103257115532,2.857142857142857,4.0,50,0.0,-0.6057278475407804,0.5714285714285712,0.0,-40

chb07,1.0,0.10439710670875693,15.333333333333334,16.0,7,1.0,0.08948323432179166,15.333333333333334,18.0,6,0.0,0.014913872386965274,0.0,-2.0,1

chb08,1.0,0.6498014495570799,9.6,10.0,13,1.0,0.7497709033350921,11.2,12.0,15,0.0,-0.09996945377801225,-1.5999999999999996,-2.0,-2

chb09,1.0,0.20043427426089863,6.0,6.0,12,1.0,0.21713713044930685,7.5,6.0,13,0.0,-0.01670285618840822,-1.5,0.0,-1

chb10,1.0,0.25988160948901057,2.2857142857142856,2.0,9,1.0,0.11994535822569719,3.142857142857143,4.0,3,0.0,0.13993625126331338,-0.8571428571428572,-2.0,6



## 9. Code validity and leakage checks
- `top-k` features are still selected from inner-train files only.
- Threshold selection is still based on the inner-validation split only.
- No test-event labels are used to define the proxy subsets or the post-processing path.
- The main methodological risk in v3 is not leakage but variant-selection bias from repeated focus-driven iteration.

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
- adopted_global_patient_delta_df: <LOCAL_EXPORT_PATH>
- Markdown memo: <LOCAL_EXPORT_PATH>
