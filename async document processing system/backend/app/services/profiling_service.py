from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import ppscore as pps


class ProfilingService:
    def prepare_dataframe(
        self,
        file_path: str,
    ) -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
        dataframe = pd.read_csv(file_path)

        numeric_columns = self._get_numeric_columns(dataframe)
        date_columns = self._get_date_columns(dataframe, numeric_columns)
        categorical_columns = [
            column
            for column in dataframe.columns
            if column not in numeric_columns and column not in date_columns
        ]

        profiled_frame = dataframe.copy()
        for column in date_columns:
            profiled_frame[column] = pd.to_datetime(profiled_frame[column], errors="coerce")

        return profiled_frame, numeric_columns, categorical_columns, date_columns

    def profile_csv(self, file_path: str) -> dict[str, Any]:
        profiled_frame, numeric_columns, categorical_columns, date_columns = self.prepare_dataframe(
            file_path
        )

        return {
            "numeric_stats": self.compute_numeric_stats(profiled_frame, numeric_columns),
            "categorical_stats": self.compute_categorical_stats(profiled_frame, categorical_columns),
            "date_stats": self.compute_date_stats(profiled_frame, date_columns),
            "correlation_stats": self.compute_correlation_stats(profiled_frame, numeric_columns),
            "pps_stats": self.compute_pps_stats(profiled_frame, numeric_columns, categorical_columns),
        }

    def compute_numeric_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
    ) -> list[dict[str, Any]]:
        return self._compute_numeric_stats(dataframe, numeric_columns)

    def compute_categorical_stats(
        self,
        dataframe: pd.DataFrame,
        categorical_columns: list[str],
    ) -> list[dict[str, Any]]:
        return self._compute_categorical_stats(dataframe, categorical_columns)

    def compute_date_stats(
        self,
        dataframe: pd.DataFrame,
        date_columns: list[str],
    ) -> list[dict[str, Any]]:
        return self._compute_date_stats(dataframe, date_columns)

    def compute_correlation_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
    ) -> dict[str, dict[str, float]]:
        return self._compute_correlation_stats(dataframe, numeric_columns)

    def compute_pps_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
        categorical_columns: list[str],
    ) -> dict[str, dict[str, float]]:
        return self._compute_pps_stats(dataframe, numeric_columns, categorical_columns)

    def _get_numeric_columns(self, dataframe: pd.DataFrame) -> list[str]:
        numeric_frame = dataframe.apply(pd.to_numeric, errors="coerce")
        numeric_columns: list[str] = []

        for column in dataframe.columns:
            converted = numeric_frame[column]
            if converted.notna().sum() == 0:
                continue
            if converted.notna().sum() >= max(1, int(len(dataframe) * 0.6)):
                dataframe[column] = converted
                numeric_columns.append(column)

        return numeric_columns

    def _get_date_columns(
        self,
        dataframe: pd.DataFrame,
        excluded_columns: list[str],
    ) -> list[str]:
        date_columns: list[str] = []

        for column in dataframe.columns:
            if column in excluded_columns:
                continue

            converted = pd.to_datetime(dataframe[column], errors="coerce")
            if converted.notna().sum() == 0:
                continue

            if converted.notna().sum() >= max(1, int(len(dataframe) * 0.6)):
                date_columns.append(column)

        return date_columns

    def _compute_numeric_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
    ) -> list[dict[str, Any]]:
        numeric_stats: list[dict[str, Any]] = []

        for column in numeric_columns:
            series = pd.to_numeric(dataframe[column], errors="coerce")
            non_null = series.dropna()
            if non_null.empty:
                continue

            numeric_stats.append(
                {
                    "column_name": column,
                    "count": int(non_null.count()),
                    "mean": self._round_or_none(non_null.mean()),
                    "std_dev": self._round_or_none(non_null.std()),
                    "min": self._value_or_none(non_null.min()),
                    "q1": self._round_or_none(non_null.quantile(0.25)),
                    "median": self._round_or_none(non_null.median()),
                    "q3": self._round_or_none(non_null.quantile(0.75)),
                    "max": self._value_or_none(non_null.max()),
                    "null_count": int(series.isna().sum()),
                }
            )

        return numeric_stats

    def _compute_categorical_stats(
        self,
        dataframe: pd.DataFrame,
        categorical_columns: list[str],
    ) -> list[dict[str, Any]]:
        categorical_stats: list[dict[str, Any]] = []

        for column in categorical_columns:
            series = dataframe[column]
            non_null = series.dropna().astype(str)
            if non_null.empty:
                continue

            counts = non_null.value_counts()
            top_values = [
                {"value": index, "count": int(value)}
                for index, value in counts.head(5).items()
            ]

            categorical_stats.append(
                {
                    "column_name": column,
                    "count": int(non_null.count()),
                    "cardinality": int(non_null.nunique()),
                    "min_count_freq": int(counts.min()),
                    "max_count_freq": int(counts.max()),
                    "lowest_freq_value": str(counts.idxmin()),
                    "highest_freq_value": str(counts.idxmax()),
                    "null_count": int(series.isna().sum()),
                    "top_values": top_values,
                }
            )

        return categorical_stats

    def _compute_date_stats(
        self,
        dataframe: pd.DataFrame,
        date_columns: list[str],
    ) -> list[dict[str, Any]]:
        date_stats: list[dict[str, Any]] = []

        for column in date_columns:
            series = pd.to_datetime(dataframe[column], errors="coerce")
            non_null = series.dropna()
            if non_null.empty:
                continue

            date_stats.append(
                {
                    "column_name": column,
                    "count": int(non_null.count()),
                    "min_date": non_null.min().isoformat(),
                    "max_date": non_null.max().isoformat(),
                    "null_count": int(series.isna().sum()),
                }
            )

        return date_stats

    def _compute_correlation_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
    ) -> dict[str, dict[str, float]]:
        if len(numeric_columns) < 2:
            return {}

        numeric_frame = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce")
        numeric_frame = numeric_frame.dropna(axis=1, how="all")
        if numeric_frame.shape[1] < 2:
            return {}

        numeric_frame = numeric_frame.fillna(numeric_frame.mean())
        correlation_matrix = numeric_frame.corr().round(3)

        return {
            row: {
                column: float(value) if pd.notna(value) else 0.0
                for column, value in values.items()
            }
            for row, values in correlation_matrix.to_dict().items()
        }

    def _compute_pps_stats(
        self,
        dataframe: pd.DataFrame,
        numeric_columns: list[str],
        categorical_columns: list[str],
    ) -> dict[str, dict[str, float]]:
        candidate_columns = numeric_columns + categorical_columns
        if len(candidate_columns) < 2:
            return {}

        candidate_frame = dataframe[candidate_columns].copy()
        candidate_frame = candidate_frame.dropna(axis=1, how="all")
        if candidate_frame.shape[1] < 2:
            return {}

        matrix = pps.matrix(candidate_frame)[["x", "y", "ppscore"]]
        pps_map: dict[str, dict[str, float]] = {}

        for _, row in matrix.iterrows():
            predictor = str(row["x"])
            target = str(row["y"])
            score = float(round(row["ppscore"], 3))
            pps_map.setdefault(predictor, {})[target] = score

        return pps_map

    def _round_or_none(self, value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(round(value, 3))

    def _value_or_none(self, value: Any) -> float | int | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (np.integer, int)):
            return int(value)
        return float(round(float(value), 3))
