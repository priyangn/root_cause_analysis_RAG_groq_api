"""Memory-safe limits for Render free tier (~512MB) and similar hosts."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Hard upload cap (bytes). Larger files OOM on free Render before analysis starts.
MAX_UPLOAD_BYTES = 80 * 1024 * 1024  # 80 MB

# Cap rows loaded from CSV/Excel into memory
MAX_PARSE_ROWS = 80_000

# Cap rows used for ML / SHAP (much cheaper than full file)
MAX_ML_ROWS = 12_000
MAX_SHAP_ROWS = 8_000
MAX_FEATURE_COLS = 40

# ML timeout (seconds) — if exceeded, fall back to mock/light results
ML_TIMEOUT_SECONDS = 90
CAUSAL_TIMEOUT_SECONDS = 60


def sample_dataframe(df: pd.DataFrame, max_rows: int, seed: int = 42) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if len(df) <= max_rows:
        return df
    logger.info("Sampling dataframe from %s to %s rows for memory safety", len(df), max_rows)
    return df.sample(n=max_rows, random_state=seed).reset_index(drop=True)


def limit_numeric_features(df: pd.DataFrame, max_cols: int = MAX_FEATURE_COLS) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] <= max_cols:
        return numeric
    # Prefer columns with highest variance (more signal)
    variances = numeric.var(numeric_only=True).sort_values(ascending=False)
    keep = variances.head(max_cols).index.tolist()
    logger.info("Limiting features from %s to %s columns", numeric.shape[1], len(keep))
    return numeric[keep]


def prepare_xy(
    df: pd.DataFrame,
    max_rows: int = MAX_ML_ROWS,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
    """Build X,y for classification from numeric columns, with sampling."""
    try:
        if df is None or df.empty or len(df) < 20:
            return None, None

        numeric = limit_numeric_features(df)
        if numeric.shape[1] < 2:
            return None, None

        sampled = sample_dataframe(numeric, max_rows)
        X = sampled.fillna(sampled.mean(numeric_only=True))

        X.columns = [
            f"col_{i}"
            if not isinstance(col, str)
            else col.replace("[", "").replace("]", "").replace("<", "").replace(">", "")
            for i, col in enumerate(X.columns)
        ]

        threshold = X.iloc[:, 0].quantile(0.75)
        y = (X.iloc[:, 0] > threshold).astype(int)
        X = X.iloc[:, 1:]
        return X, y
    except Exception as e:
        logger.error("prepare_xy failed: {0}".format(e))
        return None, None


def read_tabular(file_path: str, extension: str) -> pd.DataFrame:
    """Read CSV/Excel with row caps to avoid OOM on large files."""
    path = Path(file_path)
    size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
    try:
        if extension == ".csv":
            df = pd.read_csv(file_path, nrows=MAX_PARSE_ROWS, low_memory=False)
        elif extension in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, nrows=MAX_PARSE_ROWS)
        else:
            return pd.DataFrame()

        if len(df) >= MAX_PARSE_ROWS:
            logger.warning(
                "File %s (%.1f MB) truncated to %s rows for memory limits",
                path.name,
                size_mb,
                MAX_PARSE_ROWS,
            )
        return df
    except Exception as e:
        logger.error("Error reading tabular file %s: %s", file_path, e)
        return pd.DataFrame()
