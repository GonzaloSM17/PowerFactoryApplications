import pandas as pd

from mapper.manager.sh_term_data import ShTermDataManager
from mapper.manager.assets_mapping import AssetsMapper


class UnitMapper:
    """Extracts and prepares Plexos dispatch and PowerFactory unit mapping for merging."""

    def __init__(
        self,
        shts_handler: ShTermDataManager,
        assets_mapper: AssetsMapper,
    ):
        """Initialize with handlers."""
        self.shts_handler = shts_handler
        self.assets_mapper = assets_mapper

        self.dispatch: pd.DataFrame = None
        self.unit_mapping: pd.DataFrame = None

    def materialize(self) -> pd.DataFrame:
        """Load handlers and prepare DataFrames for merging."""

        self.dispatch = self.shts_handler.shts_data.get(
            "shTSDispatch", pd.DataFrame()
        ).copy()

        # Get the unit mapping query from assets
        unit_mapping = self.assets_mapper.assets_data["queries"].get(
            "Query_pfUnit-plexosUnit_mapping", pd.DataFrame()
        )

        self.unit_mapping = self._prepare_unit_mapping(unit_mapping)

        return self.unit_mapping

    def _prepare_unit_mapping(self, mapping: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate absolute constraints and clean up columns.

        Args:
            mapping: Raw unit mapping DataFrame

        Returns:W
            Mapping with pMin_absolute, pMax_absolute and only needed columns
        """
        if mapping.empty:
            return mapping

        mapping = mapping.copy()

        # pMax_absolute = min(pRated, pMax, sNom) * nUnit
        pmax_calc = mapping[["pRated", "pMax", "sNom"]].min(axis=1)
        mapping["pMax_absolute"] = (pmax_calc * mapping["nUnit"]).round(2)

        # pMin_absolute = pMin * nUnit
        mapping["pMin_absolute"] = (mapping["pMin"] * mapping["nUnit"]).round(2)

        # Drop old columns, keep only what's needed
        drop_cols = ["nUnit", "pMin", "pRated", "pMax", "sNom", "h"]
        mapping = mapping.drop(columns=drop_cols, errors="ignore")

        return mapping


if __name__ == "__main__":
    shts_handler = ShTermDataHandler(scenario="E4")
    assets_mapper = AssetsMapper()

    shts_handler.materialize()
    assets_mapper.materialize()

    mapper = UnitMapper(shts_handler, assets_mapper)
    mapper.materialize()
