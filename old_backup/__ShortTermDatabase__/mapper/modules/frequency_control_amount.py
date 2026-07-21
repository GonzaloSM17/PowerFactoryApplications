"""Vector processor: formats processed distribution data into Excel sheets."""

import pandas as pd
from typing import Dict

from mapper.manager.sh_term_data import ShTermDataManager
from mapper.manager.assets_mapping import AssetsMapper


class PrimaryFrequencyControlCalculator:
    """Formats pre-processed distribution data into vector and balance sheets."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]
    ALLOC_COLUMNS = [f"alloc_{i}" for i in range(1, 25)]

    def __init__(
        self,
        shts_handler: ShTermDataManager,
        assets_mapper: AssetsMapper,
    ):
        self.shts_handler = shts_handler
        self.assets_mapper = assets_mapper

    def calculate(self) -> Dict[str, pd.DataFrame]:

        self.pfc_rise = self.shts_handler.shts_data.get("shTSCpfRs", pd.DataFrame())
        self.pfc_low = self.shts_handler.shts_data.get("shTSCpfLw", pd.DataFrame())

        # To bias matrix ----
        self.pf_unit = (
            self.assets_mapper.assets_data["queries"]
            .get("Query_pfUnit", pd.DataFrame())
            .loc[:, ["pfUnitName", "nUnit"]]
        )
        self.pf_mapping = self.assets_mapper.assets_data["queries"].get(
            "Query_pfUnit-PlexosUnit_pfc", pd.DataFrame()
        )

        _temp_merging = (
            pd.merge(
                self.pf_unit,
                self.pf_mapping,
                on="pfUnitName",
                how="right",
            )
            .loc[:, ["pfUnitName", "nUnit", "frequencyBias"]]
            .drop_duplicates()
        )
        self.bias_mapping = _temp_merging
        # To bias matrix---

        self.pfc_rise_processed = self._process_pfc(self.pfc_rise, "pfc_rise")
        self.pfc_low_processed = self._process_pfc(self.pfc_low, "pfc_low")

        self.pfc_amount = {
            "pfc_rise": self.pfc_rise_processed,
            "pfc_low": self.pfc_low_processed,
        }

        self._frequency_bias_processed = self._frequency_bias()
        self.pfc_amount["frequency_bias"] = self._frequency_bias_processed

        return self.pfc_amount

    def _process_pfc(self, pfc_data: pd.DataFrame, label: str) -> pd.DataFrame:
        """Distribute PFC values proportionally by cennom and frequencyBias, then group by pfUnitName."""
        if pfc_data.empty:
            return pd.DataFrame()

        # Merge pfc_data with pf_mapping to get frequencyBias
        merged = pd.merge(
            pfc_data,
            self.pf_mapping,
            left_on="cennom",
            right_on="plexosUnitName",
            how="left",
        )

        if merged.empty or "frequencyBias" not in merged.columns:
            return pd.DataFrame()

        # Identify numeric columns (hours) - exclude non-numeric and key columns
        numeric_cols = merged.select_dtypes(include=["number"]).columns.tolist()
        # Remove frequencyBias from numeric columns
        numeric_cols = [col for col in numeric_cols if col != "frequencyBias"]

        if not numeric_cols:
            return pd.DataFrame()

        # Calculate total frequencyBias per cennom
        cennom_totals = merged.groupby("cennom")["frequencyBias"].sum()

        # Calculate weight for each row: frequencyBias / total_frequencyBias_in_cennom
        merged["weight"] = merged.apply(
            lambda row: (
                row["frequencyBias"] / cennom_totals[row["cennom"]]
                if row["cennom"] in cennom_totals and cennom_totals[row["cennom"]] > 0
                else 0
            ),
            axis=1,
        )

        # Distribute numeric columns proportionally
        for col in numeric_cols:
            merged[col] = merged[col] * merged["weight"]

        # Group by pfUnitName and sum numeric columns
        result = merged.groupby("pfUnitName")[numeric_cols].sum().reset_index()

        return result

    def _frequency_bias(self):
        """Replace hour columns with frequencyBias/nUnit value if hour column > 0."""
        if self.pfc_amount["pfc_rise"].empty or self.bias_mapping.empty:
            return pd.DataFrame()

        # Merge pfc_rise with bias_mapping to get frequencyBias and nUnit
        merged = pd.merge(
            self.pfc_amount["pfc_rise"],
            self.bias_mapping,
            on="pfUnitName",
            how="left",
        )

        if merged.empty or "frequencyBias" not in merged.columns:
            return pd.DataFrame()

        # Identify numeric columns (hours) - exclude frequencyBias and nUnit
        numeric_cols = merged.select_dtypes(include=["number"]).columns.tolist()
        numeric_cols = [
            col for col in numeric_cols if col not in ["frequencyBias", "nUnit"]
        ]

        # Replace values in hour columns: if value > 0, replace with frequencyBias/nUnit
        for col in numeric_cols:
            merged[col] = merged.apply(
                lambda row: (
                    (row["frequencyBias"] / row["nUnit"])
                    if (row[col] > 0 and row["nUnit"] > 0)
                    else 0
                ),
                axis=1,
            )

        # Drop frequencyBias and nUnit columns before returning
        result = merged.drop(["frequencyBias", "nUnit"], axis=1)

        return result


if __name__ == "__main__":

    shts_handler = ShTermDataHandler(scenario="E4")
    assets_mapper = AssetsMapper()

    shts_handler.materialize()
    assets_mapper.materialize()

    calculator = PrimaryFrequencyControlCalculator(shts_handler, assets_mapper)
    calculator.calculate()
