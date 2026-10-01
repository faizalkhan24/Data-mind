"""DataMind Train/Validation/Test Splitter.

Implements leak-free dataset partitioning strategies for IoT telemetry:
1. Group-aware Device Split (default): Partitions entire devices into disjoint sets,
   preventing device-level autocorrelation and intra-device temporal leakage.
2. Temporal Cutoff Split: Partitions data chronologically across time intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class DatasetSplits:
    """Container for partitioned DataFrames."""

    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    train_devices: List[str]
    val_devices: List[str]
    test_devices: List[str]

    @property
    def train_shape(self) -> Tuple[int, int]:
        return self.train.shape

    @property
    def val_shape(self) -> Tuple[int, int]:
        return self.val.shape

    @property
    def test_shape(self) -> Tuple[int, int]:
        return self.test.shape


def split_by_device(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    device_col: str = "device_id",
) -> DatasetSplits:
    """Splits dataset by device ID to prevent cross-device autocorrelation leakage.

    All observations for any given device reside exclusively within one partition.
    """
    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        raise ValueError(
            f"Ratios must sum to 1.0; got {train_ratio + val_ratio + test_ratio:.4f}"
        )

    unique_devices = np.sort(df[device_col].unique())
    num_devices = len(unique_devices)

    rng = np.random.default_rng(random_seed)
    shuffled_devices = rng.permutation(unique_devices)

    n_train = int(np.floor(train_ratio * num_devices))
    n_val = int(np.floor(val_ratio * num_devices))

    train_devs = list(shuffled_devices[:n_train])
    val_devs = list(shuffled_devices[n_train : n_train + n_val])
    test_devs = list(shuffled_devices[n_train + n_val :])

    train_df = df[df[device_col].isin(train_devs)].reset_index(drop=True)
    val_df = df[df[device_col].isin(val_devs)].reset_index(drop=True)
    test_df = df[df[device_col].isin(test_devs)].reset_index(drop=True)

    logger.info(
        "Device split: Train=%d devices (%d rows), Val=%d devices (%d rows), Test=%d devices (%d rows)",
        len(train_devs),
        len(train_df),
        len(val_devs),
        len(val_df),
        len(test_devs),
        len(test_df),
    )

    return DatasetSplits(
        train=train_df,
        val=val_df,
        test=test_df,
        train_devices=train_devs,
        val_devices=val_devs,
        test_devices=test_devs,
    )


def split_by_time(
    df: pd.DataFrame,
    train_end_time: str,
    val_end_time: str,
    timestamp_col: str = "timestamp",
) -> DatasetSplits:
    """Splits dataset chronologically across global timestamps.

    Ensures training occurs on historical data and evaluation evaluates on future periods.
    """
    df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)

    train_df = df_sorted[df_sorted[timestamp_col] <= train_end_time].reset_index(drop=True)
    val_df = df_sorted[
        (df_sorted[timestamp_col] > train_end_time)
        & (df_sorted[timestamp_col] <= val_end_time)
    ].reset_index(drop=True)
    test_df = df_sorted[df_sorted[timestamp_col] > val_end_time].reset_index(drop=True)

    return DatasetSplits(
        train=train_df,
        val=val_df,
        test=test_df,
        train_devices=list(train_df["device_id"].unique()),
        val_devices=list(val_df["device_id"].unique()),
        test_devices=list(test_df["device_id"].unique()),
    )
