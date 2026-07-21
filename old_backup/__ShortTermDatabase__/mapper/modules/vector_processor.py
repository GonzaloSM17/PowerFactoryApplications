"""Vector processor: formats processed distribution data into Excel sheets."""

import pandas as pd
from typing import Dict


class VectorProcessor:
    """Formats pre-processed distribution data into vector and balance sheets."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]
    ALLOC_COLUMNS = [f"alloc_{i}" for i in range(1, 25)]

    def __init__(
        self,
        pfunit_table: pd.DataFrame,
        dispatch_distribution: pd.DataFrame,
        der_distribution: pd.DataFrame,
        demand_distribution: pd.DataFrame,
        pfc_rise: pd.DataFrame,
        pfc_low: pd.DataFrame,
        frequency_bias: pd.DataFrame,
    ):
        """Initialize with pre-processed distribution data.

        Args:
            pfunit_table: Unit properties with columns [pfUnitName, pfClassName, nUnit, sNom, h].
            dispatch_distribution: Dispatch data with columns [pfUnitName, alloc_1...alloc_24].
            der_distribution: DER distribution with columns [alloc_1...alloc_24].
            demand_distribution: Demand distribution with columns [alloc_1...alloc_24].
        """
        self.dispatch_dist = dispatch_distribution.copy()
        self.der_dist = der_distribution.copy()
        self.demand_dist = demand_distribution.copy()
        self.pfunit_table = pfunit_table.copy()
        self.pfc_rise = pfc_rise.copy()
        self.pfc_low = pfc_low.copy()
        self.frequency_bias = frequency_bias.copy()

        # Drop plexosUnitName if it exists
        if "plexosUnitName" in self.pfunit_table.columns:
            self.pfunit_table = self.pfunit_table.drop(columns=["plexosUnitName"])

        self.vectors: Dict[str, pd.DataFrame] = {}

    def materialize(self) -> Dict[str, pd.DataFrame]:
        """Format pre-processed distributions into vector sheets by pfClass."""
        # Process dispatch by pfClass
        if not self.dispatch_dist.empty and not self.pfunit_table.empty:
            self._process_dispatch_by_class()
            self._process_inertia()

        if not self.der_dist.empty:
            self._process_der()

        if not self.demand_dist.empty:
            self._process_demand()

        if not self.pfc_rise.empty and not self.pfc_low.empty:
            self._process_pfc()

        self._process_balance()

        return self.vectors

    def _process_dispatch_by_class(self) -> None:
        """Split dispatch by pfClass (Sym/Sym-CC, noSym, aSym)."""
        if self.dispatch_dist.empty or self.pfunit_table.empty:
            return

        # Check required columns
        if "pfUnitName" not in self.dispatch_dist.columns:
            return
        if "pfClassName" not in self.pfunit_table.columns:
            return

        # Merge dispatch with ALL pfunit_table columns
        merged = self.dispatch_dist.merge(
            self.pfunit_table,
            on="pfUnitName",
            how="left",
        )

        if (
            merged.empty
            or "pfClassName" not in merged.columns
            or merged["pfClassName"].isna().all()
        ):

            return

        # Group pfClassName: Sym/Sym-CC -> "Sym", others as-is
        merged["pfClass_group"] = (
            merged["pfClassName"]
            .fillna("Unknown")
            .apply(lambda x: "Sym" if x in ["Sym", "Sym-CC"] else x)
        )

        # Create vector sheets for each class type
        for class_type in ["Sym", "noSym", "aSym"]:
            class_data = merged[merged["pfClass_group"] == class_type].copy()
            if class_data.empty:
                continue

            # Keep all pfunit_table columns and allocation columns (alloc_1 to alloc_24)
            alloc_cols = [f"alloc_{i}" for i in range(1, 25)]
            pfunit_cols = self.pfunit_table.columns.tolist()
            cols_to_keep = pfunit_cols + alloc_cols
            cols_available = [c for c in cols_to_keep if c in class_data.columns]

            if not cols_available or "pfUnitName" not in cols_available:
                continue

            result = class_data[cols_available].copy()

            # Divide allocation columns by nUnit if nUnit exists
            if "nUnit" in result.columns:
                for col in alloc_cols:
                    if col in result.columns:
                        result[col] = result[col] / result["nUnit"]

            # Rename allocation columns to hour numbers (alloc_1 -> "1", alloc_2 -> "2", etc)
            rename_dict = {f"alloc_{i}": str(i) for i in range(1, 25)}
            result = result.rename(columns=rename_dict)

            self.vectors[f"_{class_type}_"] = result.reset_index(drop=True)

    def _process_inertia(self) -> None:
        """Calculate inertia matrix: (h * sNom * nUnit) / 1000 for each dispatch > 0."""
        if self.dispatch_dist.empty or self.pfunit_table.empty:
            return

        required_cols = ["nUnit", "sNom", "h"]
        if not all(col in self.pfunit_table.columns for col in required_cols):
            return

        # Merge dispatch with pfunit_table to get inertia parameters
        merged = self.dispatch_dist.merge(
            self.pfunit_table[["pfUnitName"] + required_cols],
            on="pfUnitName",
            how="left",
        )

        # Start with pfUnitName column
        inertia = merged[["pfUnitName"]].copy()

        # Calculate inertia for each hour: (h * sNom * nUnit) / 1000 if dispatch > 0
        for i, h in enumerate(self.HOUR_COLUMNS, 1):
            alloc_col = f"alloc_{i}"
            hour_str = str(i)

            if alloc_col in merged.columns:
                inertia[hour_str] = merged.apply(
                    lambda row: (
                        (row["h"] * row["sNom"] * row["nUnit"]) / 1000
                        if row[alloc_col] > 0
                        else 0
                    ),
                    axis=1,
                ).round(2)
            else:
                inertia[hour_str] = 0

        self.vectors["_inertia_"] = inertia.reset_index(drop=True)

    def _process_der(self) -> None:
        """Format DER distribution data - rename alloc_X to X."""
        if self.der_dist.empty:
            return

        # Rename allocation columns to hour numbers (alloc_1 -> "1", alloc_2 -> "2", etc)
        rename_dict = {f"alloc_{i}": str(i) for i in range(1, 25)}
        der_df = self.der_dist.rename(columns=rename_dict)

        self.vectors["_der_"] = der_df.reset_index(drop=True)

    def _process_demand(self) -> None:
        """Create balance sheet with correct order of rows."""
        if self.dispatch_dist.empty:
            return

        self.vectors["_demandDistribution_"] = self.demand_dist.reset_index(drop=True)

    def _process_pfc(self) -> None:
        self.vectors["_pfcRise_"] = self.pfc_rise.reset_index(drop=True)
        self.vectors["_pfcLow_"] = self.pfc_low.reset_index(drop=True)
        self.vectors["_frequencyBias_"] = self.frequency_bias.reset_index(drop=True)

    def _process_balance(self) -> None:
        """Create balance sheet with aggregated metrics by hour."""
        balance_rows = {}
        hours = self.HOUR_COLUMNS

        # Get all vectors
        inertia_data = self.vectors.get("_inertia_", pd.DataFrame())
        sym_data = self.vectors.get("_Sym_", pd.DataFrame())
        nosym_data = self.vectors.get("_noSym_", pd.DataFrame())
        asym_data = self.vectors.get("_aSym_", pd.DataFrame())
        der_data = self.vectors.get("_der_", pd.DataFrame())
        demand_data = self.vectors.get("_demandDistribution_", pd.DataFrame())

        # 1. inertiaTotal - Sum of inertia excluding pfUnitName column
        if not inertia_data.empty:
            inertia_numeric = inertia_data[hours].sum()
            balance_rows["inertiaTotal(GVAs)"] = inertia_numeric.round(1)
        else:
            balance_rows["inertiaTotal(GVAs)"] = pd.Series(0, index=hours)

        # 2. generationTotal - Sum of POSITIVE values from Sym + noSym + aSym + DER, multiplied by nUnit
        generation_total = pd.Series(0.0, index=hours)
        for data in [sym_data, nosym_data, asym_data, der_data]:
            if not data.empty:
                for h in hours:
                    if h in data.columns:
                        # Filter only positive values in this hour column
                        positive_values = data[data[h] > 0]
                        # Multiply by nUnit if it exists
                        if "nUnit" in positive_values.columns:
                            generation_total[h] += (
                                positive_values[h] * positive_values["nUnit"]
                            ).sum()
                        else:
                            generation_total[h] += positive_values[h].sum()
        balance_rows["generationTotal(MW)"] = generation_total.round(1)

        # 3. demandaTotal
        if not demand_data.empty:
            demand_total = demand_data[hours].sum()
            balance_rows["demandTotal(MW)"] = demand_total.round(1)
        else:
            balance_rows["demandTotal(MW)"] = pd.Series(0, index=hours)

        # 4. bess(-)charging - Sum of NEGATIVE values from Sym + noSym, multiplied by nUnit
        unit_charging = pd.Series(0.0, index=hours)
        for data in [sym_data, nosym_data, der_data]:
            if not data.empty:
                for h in hours:
                    if h in data.columns:
                        negative_values = data[data[h] < 0]
                        # Multiply by nUnit if it exists
                        if "nUnit" in negative_values.columns:
                            unit_charging[h] += (
                                negative_values[h] * negative_values["nUnit"]
                            ).sum()
                        else:
                            unit_charging[h] += negative_values[h].sum()
        balance_rows["unit(-)Charging(MW)"] = unit_charging.round(1) * (-1)

        # 4a. Estimated losses % - (generationTotal - (demandTotal + unitCharging)) / generationTotal * 100
        losses_estimated = pd.Series(0.0, index=hours)
        for h in hours:
            gen = balance_rows["generationTotal(MW)"][h]
            demand = balance_rows["demandTotal(MW)"][h]
            charging = balance_rows["unit(-)Charging(MW)"][h]
            if gen > 0:
                losses_estimated[h] = ((gen - (demand + charging)) / gen) * 100
            else:
                losses_estimated[h] = 0
        balance_rows["lossesEstimated(%)"] = losses_estimated.round(1)

        # 4b. Validation warning - Check if generationTotal >= demandTotal + unitCharging
        validation = pd.Series("", index=hours)
        for h in hours:
            gen = balance_rows["generationTotal(MW)"][h]
            demand = balance_rows["demandTotal(MW)"][h]
            charging = balance_rows["unit(-)Charging(MW)"][h]
            if gen < (demand + charging):
                validation[h] = "⚠ INSUFFICIENT"
        balance_rows["balance_check"] = validation

        # Blank row above pFrequencyControl
        balance_rows["   "] = pd.Series("", index=hours)

        # pFrequencyControl(+) - Sum of pfc_rise data
        pfc_rise_data = self.vectors.get("_pfcRise_", pd.DataFrame())
        pfc_rise_total = pd.Series(0.0, index=hours)

        if not pfc_rise_data.empty:
            for h in hours:
                if h in pfc_rise_data.columns:
                    pfc_rise_total[h] = pfc_rise_data[h].sum()

        balance_rows["pFrequencyControl(+)(MW)"] = pfc_rise_total.round(1)

        # 5. Blank row
        balance_rows[""] = pd.Series("", index=hours)

        # 6-9. Sym and noSym breakdown (multiplied by nUnit)
        sym_pos = pd.Series(0.0, index=hours)
        sym_neg = pd.Series(0.0, index=hours)
        nosym_pos = pd.Series(0.0, index=hours)
        nosym_neg = pd.Series(0.0, index=hours)

        if not sym_data.empty:
            for h in hours:
                if h in sym_data.columns:
                    sym_pos_data = sym_data[sym_data[h] > 0]
                    sym_neg_data = sym_data[sym_data[h] < 0]
                    if "nUnit" in sym_pos_data.columns:
                        sym_pos[h] = (sym_pos_data[h] * sym_pos_data["nUnit"]).sum()
                        sym_neg[h] = (sym_neg_data[h] * sym_neg_data["nUnit"]).sum()
                    else:
                        sym_pos[h] = sym_pos_data[h].sum()
                        sym_neg[h] = sym_neg_data[h].sum()

        if not nosym_data.empty:
            nosym_data_ = pd.concat(
                [nosym_data, der_data], ignore_index=True
            )  # Combine noSym and DER for charging calculation

            for h in hours:
                if h in nosym_data_.columns:
                    nosym_pos_data = nosym_data_[nosym_data_[h] > 0]
                    nosym_neg_data = nosym_data_[nosym_data_[h] < 0]
                    if "nUnit" in nosym_pos_data.columns:
                        nosym_pos[h] = (
                            nosym_pos_data[h] * nosym_pos_data["nUnit"]
                        ).sum()
                        nosym_neg[h] = (
                            nosym_neg_data[h] * nosym_neg_data["nUnit"]
                        ).sum()
                    else:
                        nosym_pos[h] = nosym_pos_data[h].sum()
                        nosym_neg[h] = nosym_neg_data[h].sum()

        balance_rows["Sym(+)(MW)"] = sym_pos.round(1)
        balance_rows["Sym(-)(MW)"] = sym_neg.round(1) * (-1)
        balance_rows["noSym(+)(MW)"] = nosym_pos.round(1)
        balance_rows["noSym(-)(MW)"] = nosym_neg.round(1) * (-1)

        # 10. Blank row
        balance_rows["  "] = pd.Series("", index=hours)

        # 11. derTotal(+) and derTotal(-) (multiplied by nUnit)
        der_pos = pd.Series(0.0, index=hours)
        der_neg = pd.Series(0.0, index=hours)

        if not der_data.empty:
            for h in hours:
                if h in der_data.columns:
                    der_pos_data = der_data[der_data[h] > 0]
                    der_neg_data = der_data[der_data[h] < 0]
                    if "nUnit" in der_pos_data.columns:
                        der_pos[h] = (der_pos_data[h] * der_pos_data["nUnit"]).sum()
                        der_neg[h] = (der_neg_data[h] * der_neg_data["nUnit"]).sum()
                    else:
                        der_pos[h] = der_pos_data[h].sum()
                        der_neg[h] = der_neg_data[h].sum()

        balance_rows["derTotal(+)(MW)"] = der_pos.round(1)
        balance_rows["derTotal(-)(MW)"] = der_neg.round(1) * (-1)

        # Create balance DataFrame preserving row order
        balance_df = pd.DataFrame(balance_rows).T
        balance_df.insert(0, "-", balance_df.index)
        balance_df.columns.name = None
        balance_df = balance_df.reset_index(drop=True)

        self.vectors["_balance_"] = balance_df

        """Create balance sheet with correct order of rows."""
        if self.dispatch_dist.empty:
            return


if __name__ == "__main__":

    from mapper.pipelines.sh_term_orchestrating import (
        ShTermVectorOrchestrator,
    )

    orchestrator = ShTermVectorOrchestrator("E4")
    (
        assets_mapper,
        dispatch_agg,
        der_agg,
        demand_agg,
        pfc_rise,
        pfc_low,
        frequency_bias,
    ) = orchestrator.execute()

    pfunit_table = assets_mapper.assets_data["queries"].get(
        "Query_pfUnit", pd.DataFrame()
    )

    vector_processor = VectorProcessor(
        pfunit_table=pfunit_table,
        dispatch_distribution=dispatch_agg,
        der_distribution=der_agg,
        demand_distribution=demand_agg,
        pfc_rise=pfc_rise,
        pfc_low=pfc_low,
        frequency_bias=frequency_bias,
    )
    vector_processor.materialize()
