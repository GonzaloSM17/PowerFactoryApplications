from dataclasses import dataclass
from typing import Optional
import pandas as pd

from mapper.manager.sh_term_data import ShTermDataManager
from mapper.manager.assets_mapping import AssetsMapper


@dataclass(frozen=True)
class LoadsConfig:
    """Configuration for loads processing."""

    zone_order: list[str]


class DemandProcessor:
    """Process and aggregate loads by zone from scenario data and assets mapping."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]

    DEFAULT_ZONE_ORDER = [
        "Norte Grande",
        "Norte Chico",
        "Enel",
        "Centro",
        "Centro-Sur",
        "Concepción",
        "Sur",
    ]

    def __init__(
        self,
        shts_handler: ShTermDataManager,
        assets_mapper: AssetsMapper,
        config: Optional[LoadsConfig] = None,
    ):
        """Initialize with UC scenario data and assets mapping."""
        self.shts_handler = shts_handler
        self.assets_mapper = assets_mapper
        self.config = config or LoadsConfig(zone_order=self.DEFAULT_ZONE_ORDER)

        self.demand_calculated: dict[str, pd.DataFrame] = {}

    def calculate(self) -> dict[str, pd.DataFrame]:
        """Load, process, and aggregate loads by zone."""

        # --- Demand Aggregation ---
        assets_data = self.assets_mapper.assets_data.get("queries", {})
        bus_mapping = assets_data.get("Query_plexosBus-zone_mapping", pd.DataFrame())
        shts_data = self.shts_handler.shts_data.get("shTSDemand", pd.DataFrame())

        demand_aggregated = self._process_demand(bus_mapping, shts_data)

        # --- BESS Incharge ---
        df_bess = self.shts_handler.shts_data.get("shTSLoadbess", pd.DataFrame())
        df_buses = self.assets_mapper.assets_data.get("queries", {}).get(
            "Query_plexosUnit-zone_mapping", pd.DataFrame()
        )
        bess_incharge = self._bess_incharge(df_bess, df_buses)

        # Deaggregate BESS in demand
        self.demand_total = self._deaggregated_bess_in_demand(
            demand_aggregated, bess_incharge
        )

        self.demand_calculated["aggregated_by_zone"] = self.demand_total

        return self.demand_calculated

    def _process_demand(
        self, bus_mapping: pd.DataFrame, shts_data: pd.DataFrame
    ) -> None:
        """Cross demand data with bus mapping and aggregate by zone."""

        if shts_data.empty:
            return

        if bus_mapping.empty:
            return

        # Merge demand with bus mapping on unit name
        merged = shts_data.merge(
            bus_mapping,
            left_on="barra",
            right_on="plexosBusName",
            how="left",
            validate="m:1",
        )

        # Aggregate by zone
        aggregated = (
            merged.groupby("zoneName")[self.HOUR_COLUMNS].sum().round(1).reset_index()
        )

        # Sort by zone order
        aggregated["zoneName"] = pd.Categorical(
            aggregated["zoneName"],
            categories=self.config.zone_order,
            ordered=True,
        )
        aggregated = aggregated.sort_values("zoneName").reset_index(drop=True)
        aggregated["zoneName"] = aggregated["zoneName"].astype(str)

        return aggregated

    def _bess_incharge(self, df_bess: pd.DataFrame, df_buses: pd.DataFrame):

        # Remove occurrences of "_LOAD" from df_bess["cennom"], preserving NaNs
        if "cennom" in df_bess.columns:
            mask = df_bess["cennom"].notna()
            df_bess.loc[mask, "cennom"] = (
                df_bess.loc[mask, "cennom"]
                .astype(str)
                .str.replace("_LOAD", "", regex=False)
                .str.strip()
            )

        df_merged = df_bess.merge(
            df_buses,
            left_on="cennom",
            right_on="plexosUnitName",
            how="left",
            suffixes=("_bess", "_buses"),
        )

        df_merged = df_merged.drop(columns=["cennom", "plexosUnitName"])
        df_merged = df_merged.groupby("zoneName").sum().reset_index()

        return df_merged

    def _deaggregated_bess_in_demand(
        self, demand_aggregated: pd.DataFrame, bess_incharge: pd.DataFrame
    ):

        if demand_aggregated.empty or bess_incharge.empty:
            return

        if (
            "zoneName" not in demand_aggregated.columns
            or "zoneName" not in bess_incharge.columns
        ):
            return

        # Determine hour columns present in demand_aggregated
        hours = [c for c in self.HOUR_COLUMNS if c in demand_aggregated.columns]
        if not hours:
            return

        # Prepare BESS dataframe: keep zoneName and hour columns, aggregate duplicates by zone
        bess = bess_incharge.copy()
        for c in hours:
            if c not in bess.columns:
                bess[c] = 0.0
        bess = bess[["zoneName"] + hours].groupby("zoneName")[hours].sum()

        # Reindex bess to match the order/rows of demand_aggregated zones, filling missing with 0
        demand_zones = demand_aggregated["zoneName"].astype(str).tolist()
        bess_reindexed = bess.reindex(demand_zones).fillna(0.0).reset_index(drop=True)

        # Subtract BESS incharge from aggregated demand, ensure numeric and round
        for c in hours:
            lhs = pd.to_numeric(demand_aggregated[c], errors="coerce").fillna(0.0)
            rhs = pd.to_numeric(bess_reindexed[c], errors="coerce").fillna(0.0)
            demand_aggregated[c] = (lhs - rhs).round(1)

        return demand_aggregated


if __name__ == "__main__":

    shts_handler = ShTermDataManager(scenario="E4")
    assets_mapper = AssetsMapper()

    shts_handler.materialize()
    assets_mapper.materialize()

    processor = DemandProcessor(shts_handler, assets_mapper)
    demand = processor.calculate()
