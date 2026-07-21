import pandas as pd
import numpy as np

from mapper.manager.assets_mapping import AssetsMapper


class DerDistributionCalculator:
    """Distributes unmerged Plexos dispatch to DER units by bus."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]

    def __init__(self, unmerged_df: pd.DataFrame, assets_mapper: AssetsMapper):
        """
        Initialize with unmerged dispatch and DER mapping.

        Args:
            unmerged_df: DataFrame with unmerged Plexos units (columns: cennom, dispatch columns)
            der_mapping: Query_derUnit-plexosUnit_mapping (columns: plexosUnitName, busReductionName, derUnitName, pRated)
        """
        self.unmerged = unmerged_df.copy()
        self.der_mapping = assets_mapper.assets_data["queries"].get(
            "Query_derUnit-plexosUnit_mapping", pd.DataFrame()
        )

        self.distribution = {}

    def calculate_all(self) -> dict[str, pd.DataFrame]:
        """Calculate all DER distributions."""
        der_allocated = self._calculate_der_distributions()
        der_aggregated = self._aggregate_by_der_unit()

        self.distribution["allocated"] = der_allocated.reset_index(drop=True)
        self.distribution["aggregated"] = der_aggregated.reset_index(drop=True)

        return self.distribution

    def _calculate_der_distributions(self) -> dict[str, pd.DataFrame]:
        """Calculate DER distributions from unmerged Plexos units."""
        all_results = []

        # Merge unmerged with der_mapping to get bus assignments
        unmerged_with_bus = self.unmerged.merge(
            self.der_mapping[["plexosUnitName", "busReductionName"]].drop_duplicates(),
            left_on="cennom",
            right_on="plexosUnitName",
            how="left",
        )

        # Separate matched and unmatched rows
        unmerged_matched = unmerged_with_bus.dropna(subset=["busReductionName"])
        unmerged_unmatched = unmerged_with_bus[
            unmerged_with_bus["busReductionName"].isna()
        ].copy()

        # Process matched unmerged units
        for bus_reduction, bus_group in unmerged_matched.groupby("busReductionName"):
            # Sum all Plexos units in this bus
            dispatch_values = bus_group[self.HOUR_COLUMNS].sum().values.astype(float)

            # Find all DERs connected to this bus
            ders_in_bus = self.der_mapping[
                self.der_mapping["busReductionName"] == bus_reduction
            ]

            if len(ders_in_bus) == 0:
                continue

            # Distribute dispatch proportionally by pRated
            allocations = self._allocate_proportional_by_rated(
                ders_in_bus, dispatch_values
            )

            # Store results for each DER
            ders_reset = ders_in_bus.reset_index(drop=True)
            for idx in range(len(ders_reset)):
                result_row = ders_reset.iloc[idx].copy()
                result_row["bus_reduction"] = bus_reduction
                for h, hour in enumerate(self.HOUR_COLUMNS):
                    result_row[f"alloc_{hour}"] = allocations[idx][h]
                all_results.append(result_row)

        # Process unmatched units: assign to DummyBus and DummyPMGD
        if len(unmerged_unmatched) > 0:
            dispatch_dummy = (
                unmerged_unmatched[self.HOUR_COLUMNS].sum().values.astype(float)
            )

            # Create a dummy DER row as a Series to match DataFrame rows
            dummy_row = pd.Series(
                {
                    "plexosUnitName": "DummyPlexos",
                    "busReductionName": "DummyBus",
                    "derUnitName": "DummyPMGD",
                    "pRated": 1.0,  # Dummy value
                }
            )

            # Add allocation columns
            for h, hour in enumerate(self.HOUR_COLUMNS):
                dummy_row[f"alloc_{hour}"] = dispatch_dummy[h]

            all_results.append(dummy_row)

        allocated = pd.DataFrame(all_results).reset_index(drop=True)
        self.distribution["allocated"] = allocated

        return allocated

    def _allocate_proportional_by_rated(
        self, ders: pd.DataFrame, dispatch: np.ndarray
    ) -> dict:
        """Allocate dispatch proportionally by pRated of DER units."""
        prated_values = ders["pRated"].values.astype(float)
        total_prated = prated_values.sum()

        allocations = {}

        for idx in range(len(ders)):
            prated_idx = prated_values[idx]
            allocation = np.zeros(24)

            for h in range(24):
                disp_h = dispatch[h]

                if total_prated > 1e-6:
                    weight = prated_idx / total_prated
                    alloc_h = disp_h * weight
                else:
                    alloc_h = disp_h / len(ders)

                allocation[h] = alloc_h

            allocations[idx] = allocation

        return allocations

    def _aggregate_by_der_unit(self) -> None:
        """Group allocated data by derUnitName and sum allocations."""
        allocated = self.distribution["allocated"]
        alloc_cols = [f"alloc_{h}" for h in self.HOUR_COLUMNS]

        # Group by derUnitName and sum the allocations
        aggregated = allocated.groupby("derUnitName")[alloc_cols].sum().reset_index()
        self.distribution["aggregated"] = aggregated

        return aggregated


if __name__ == "__main__":
    from mapper.modules.unit_mapper import UnitMapper
    from mapper.modules.dispatch_merger import DispatchMerger
    from mapper.manager.sh_term_data import (
        ShTermDataManager
    )
    from mapper.manager.assets_mapping import AssetsMapper

    shts_handler = ShTermDataManager(scenario="E4")
    assets_mapper = AssetsMapper()

    shts_handler.materialize()
    assets_mapper.materialize()

    mapper = UnitMapper(shts_handler, assets_mapper)
    mapper.materialize()

    merger = DispatchMerger(mapper)
    merged, unmerged = merger.merge()

    # Calculate DER distributions
    der_calculator = DerDistributionCalculator(unmerged, assets_mapper)
    der_results = der_calculator.calculate_all()
