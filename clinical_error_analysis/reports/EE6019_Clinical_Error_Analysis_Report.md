# EE6019 临床误差分析与定向改进报告

## 1. 当前 detector 的已知局限
- 当前系统对工件的鲁棒性主要来自带通滤波和最短持续时间约束，并未引入专用工件分类器。
- 因此，高灵敏度并不自动意味着临床上更稳健：某些病人仍可能出现明显延迟或不可忽略的误报。
- 本次分析特别聚焦 `chb04` 的延迟检测问题和 `chb08` 的误报问题。

## 2. chb04 延迟案例总结
- 检出的延迟 TP 事件数量：**2**
- 最大延迟：**104.00 s**
- 中位延迟：**62.00 s**
- 这些案例说明：即使模型最终抓到了发作，报警时间也可能明显滞后于临床上更希望的告警时点。

## 3. chb08 误报案例总结
- chb08 误报事件数量：**15**
- 启发式分类里占比最高的误报原因：**uncertain**
- 这部分结果用来回答：模型到底是在被节律性非发作活动误导，还是在被疑似工件、边界过渡态误导。

### 3.1 chb08 误报分类统计
fp_reason,Count,Share

uncertain,14,0.9333333333333333

transition_state,1,0.06666666666666667



## 4. TP / FP / FN 特征差异
- 这里的比较不是为了重新训练模型，而是为了识别‘成功事件’和‘失败事件’在频带、同步、工件代理和分数行为上的结构性差异。

### 4.1 事件类型特征汇总（节选）
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



### 4.2 事件类型效应量排序（节选）
Comparison,Feature,Mean_Left,Mean_Right,StdDiff,AbsStdDiff

TP vs FN,score_peak,0.9162750488592728,0.1485148497347037,5.465089323227287,5.465089323227287

TP vs FN,score_mean,0.7525817427166999,0.09655815395369291,4.181988745751156,4.181988745751156

TP vs FN,duration_s,78.34615384615384,18.0,1.7186954663899137,1.7186954663899137

TP vs FN,delta_power_mean_mean,1352604668.440553,406547850.20958436,1.5380542024742792,1.5380542024742792

TP vs FN,epoch_ptp_max_mean,1162.6566938621193,725.9169173902451,1.1287618702217022,1.1287618702217022

TP vs FN,epoch_ptp_median_mean,616.2785756577122,371.43849016858695,1.0974754407261476,1.0974754407261476

TP vs FN,line_length_median_mean,19.081886570357376,10.109172217989176,1.0400214573341837,1.0400214573341837

TP vs FN,theta_power_mean_mean,782365188.3366026,209431128.71718562,0.9146513738869626,0.9146513738869626



## 5. 定向改进实验结果
- 候选变体固定保持最终 tuned RF 的 `top_k=30` 和 RF 超参数不变，只修改输入特征或后处理。
- 先在 `chb04 / chb08` 上选最优单一变体，再拿该变体回到全部 10 位病人做全局检查。

### 5.1 重点病人比较
Patient,Model,TopK,Hours,True_Seizures,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,Median_Threshold,FP_events,Variant

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.5918867669464123,35.5,15.0,0.551,89,baseline_rf_top30

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7497709033350921,11.2,12.0,0.464,15,baseline_rf_top30

chb04,random_forest,30,156.06333333333333,4.0,1.0,0.37805164569939553,51.0,50.0,0.724,59,sync_expanded_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.7997556302240982,9.2,10.0,0.412,15,sync_expanded_rf

chb04,random_forest,30,152.0561111111111,4.0,1.0,0.24333122641130286,35.5,15.0,0.603,37,artifact_aware_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.6498014495570799,9.6,10.0,0.36,13,artifact_aware_rf

chb04,random_forest,30,156.06333333333333,4.0,0.75,0.44212819581793716,36.666666666666664,8.0,0.759,69,clean_subset_rf

chb08,random_forest,30,20.00611111111111,5.0,1.0,0.5998167226680736,10.0,10.0,0.464,11,clean_subset_rf



### 5.2 最佳变体排序
Variant,chb08_far_improvement,chb04_delay_improvement,focus_fp_event_improvement,passes_sensitivity_guard

artifact_aware_rf,0.09996945377801225,0.0,54,True

sync_expanded_rf,-0.049984726889006126,-15.5,30,True



### 5.3 全体 10 位病人：baseline vs best variant
Variant,Patient,Patients,Sensitivity,FAR_per_Hour,Mean_Delay_s,Median_Delay_s,FP_events,Selected_Best_Variant

baseline_rf_top30,MACRO,10,0.9777777777777779,0.39074760718812335,9.955238095238096,5.0,233,False

artifact_aware_rf,MACRO,10,0.7873015873015873,0.1853784372906424,8.452910052910052,6.0,125,True



## 6. 改进是否值得纳入主模型
- 当前自动选出的最佳单一变体：**artifact_aware_rf**
- 相比 baseline，最佳变体的宏观变化为：Sensitivity -0.1905，FAR/hr -0.2054，Mean Delay -1.5023 s。
- 这一结果更适合作为“局部有效的定向修补策略”，是否纳入主模型仍需谨慎。

## 7. 论文级批判性反思
- 本次分析表明，单看总体灵敏度会掩盖病人特异性的失败模式。
- `chb04` 提醒我们：检测到发作并不等于足够及时，延迟本身就是临床意义上的误差。
- `chb08` 提醒我们：误报并不总是纯噪声，部分误报可能对应节律性非发作活动、边界过渡态，甚至是高振幅工件。
- 因此，后续工作更合理的路线不是盲目继续调 RF 超参数，而是加入更明确的工件处理、同步特征设计和病例级解释框架。

## 8. 导出文件索引
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
- Markdown 报告: <LOCAL_EXPORT_PATH>
