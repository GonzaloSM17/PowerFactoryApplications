from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from mapper.manager.sh_term_data import ShTermDataManager
from mapper.manager.assets_mapping import AssetsMapper


@dataclass(frozen=True)
class DerConfig:
    """Configuration for DER (Distributed Energy Resources) dimensioning."""

    renewable_fuel_types: list[str] = field(
        # default_factory=lambda: ["SOLAR", "EOLICA"]
        default_factory=lambda: ["SOLAR", "EOLICA", "BATERIAS GEN"]
    )
    max_capacity_mw: float = 10.0


class DerDimensioner:
    """Analyze and dimension distributed energy resources from scenario data."""

    def __init__(
        self,
        scenario_handler: ShTermDataManager,
        assets_mapper: AssetsMapper,
        config: Optional[DerConfig] = None,
    ):
        """Initialize with scenario and assets data."""
        self.scenario_handler = scenario_handler
        self.assets_mapper = assets_mapper

        self.config = config or DerConfig()
        self.processed_der: dict[str, pd.DataFrame] = {}

    def materialize(self) -> dict[str, pd.DataFrame]:
        """Process DER data and return results."""
        # self.scenario_handler.materialize()
        assets_queries = self.assets_mapper.assets_data["queries"]

        self._process_der(assets_queries)
        return self.processed_der

    def _process_der(self, assets_queries: dict[str, pd.DataFrame]) -> None:
        """
        Process DER dimensioning:
        1. Get difference between two unit mappings
        2. Merge with scenario units
        3. Filter by fuel type and capacity
        4. Aggregate by bus reduction
        5. Sort by capacity
        """
        mapping_full = assets_queries.get(
            "Query_busReduction-auxiliaryUnit_mapping", pd.DataFrame()
        )
        mapping_with_pf = assets_queries.get(
            "Query_busReduction-auxiliaryUnit-pf_mapping", pd.DataFrame()
        )

        if mapping_full.empty or mapping_with_pf.empty:
            return

        mapping_diff = self._get_mapping_difference(mapping_full, mapping_with_pf)

        # self.report = mapping_diff.copy()  # Store intermediate result for reporting
        
        units = self.scenario_handler.shts_data.get("shTSUnits", pd.DataFrame())

        if units.empty or mapping_diff.empty:
            return

        merged = self._merge_with_units(mapping_diff, units)

        self.report = merged.copy()

        filtered = self._filter_by_fuel_and_capacity(merged)       

        aggregated = self._aggregate_by_bus_reduction(filtered)
        sorted_data = aggregated.sort_values(
            by="totalCapacity(MW)", ascending=False
        ).reset_index(drop=True)

        self.processed_der["der_dimensioning"] = sorted_data

    def _merge_with_units(
        self, mapping: pd.DataFrame, units: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge mapping with units data and remove duplicates."""
        merged = mapping.merge(
            units,
            left_on="auxialaryUnitName",
            right_on="unidadGeneradora",
            how="inner",
        )

        return merged.drop_duplicates(
            subset=["unidadGeneradora", "auxialaryUnitName"], keep="first"
        ).reset_index(drop=True)

    def _filter_by_fuel_and_capacity(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter DER by renewable fuel type and maximum capacity (< 10 MW)."""
        data = data.copy()
        data["potenciaBrutaMaxima(MW)"] = pd.to_numeric(
            data["potenciaBrutaMaxima(MW)"], errors="coerce"
        ).fillna(0.0)

        return data[
            (data["tipoDeCombustible"].isin(self.config.renewable_fuel_types))
            & (data["potenciaBrutaMaxima(MW)"] < 10.0)
        ]

    def _aggregate_by_bus_reduction(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate capacity by bus reduction and add total row."""
        aggregated = (
            data.groupby("busReductionName")["potenciaBrutaMaxima(MW)"]
            .sum()
            .round(1)
            .reset_index(name="totalCapacity(MW)")
        )

        total_capacity = aggregated["totalCapacity(MW)"].sum()
        total_row = pd.DataFrame(
            [{"busReductionName": "Total", "totalCapacity(MW)": total_capacity}]
        )

        return pd.concat([aggregated, total_row], ignore_index=True)

    def _get_mapping_difference(
        self, mapping_full: pd.DataFrame, mapping_with_pf: pd.DataFrame
    ) -> pd.DataFrame:
        """Get rows in mapping_full that are not in mapping_with_pf."""
        key_columns = ["busReductionName", "auxialaryUnitName"]

        mapping_full_keyed = mapping_full[key_columns].drop_duplicates()
        mapping_with_pf_keyed = mapping_with_pf[key_columns].drop_duplicates()

        difference = mapping_full_keyed.merge(
            mapping_with_pf_keyed,
            on=key_columns,
            how="left",
            indicator=True,
        )

        difference = difference[difference["_merge"] == "left_only"].drop(
            columns=["_merge"]
        )

        return mapping_full.merge(difference, on=key_columns, how="inner")


if __name__ == "__main__":

    scenario_handler = ShTermDataManager(scenario="E4")
    assets_mapper = AssetsMapper()

    scenario_handler.materialize()
    assets_mapper.materialize()

    dimensioner = DerDimensioner(scenario_handler, assets_mapper)
    der_data = dimensioner.materialize()

    der_data = der_data["der_dimensioning"]
