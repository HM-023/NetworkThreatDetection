# Evaluation protocol and open questions

1. Verify the dataset's provenance, permission to use, label definitions, and potential duplicate flows before training.
2. Perform a stratified train/test split before imputing or scaling features. The included pipeline does this.
3. Report support and per-class precision/recall/F1; do not rely only on overall accuracy for imbalanced traffic classes.
4. Investigate host-level, capture-level, and time-level correlations. A random holdout is an optimistic baseline when related flows can cross the split.
5. Use a truly independent capture, measure inference throughput and false alarms, and compare against benign traffic shifts before deployment.
6. Consider leakage from target-correlated features, not just preprocessing leakage. Document whether class labels came from attack schedule, host identifiers, or engineered records.
7. No historical experiment scores are reproduced here; conclusions require results from a fully documented rerun.
