# Axis: Data and ML Pipelines

Load when the change transforms datasets (dataframes, Spark, dbt, ETL or orchestration jobs) or trains, evaluates or serves a model. Use with `review-angles.md`.

- Training/serving skew: a feature computed one way where the model is trained and another where it is served (different missing-value fill, scaling, tokenizer, category mapping, time window). Both sides should call the same code or the same saved transform.
- Schema drift: a pipeline step that reads columns by position, or silently drops, renames or retypes a column a downstream job reads.
- Leakage: a feature built from data that would not be known at prediction time (future rows, the label itself, a split shuffled across time).
- Silent data loss: joins that drop unmatched rows, `dropna` or filters that remove more than intended, with no row-count check or metric.
- Reproducibility: unseeded randomness, unpinned data snapshots or model artifacts.
