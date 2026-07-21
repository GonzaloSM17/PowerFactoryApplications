import pandas as pd

from mapper.modules.unit_mapper import UnitMapper
from mapper.manager.sh_term_data import ShTermDataManager
from mapper.manager.assets_mapping import AssetsMapper


class DispatchMerger:
    """Merges Plexos dispatch with PowerFactory unit constraints."""

    def __init__(self, unit_mapper: UnitMapper):
        """Initialize with UnitMapper."""
        self.unit_mapper = unit_mapper
        self.merged: pd.DataFrame = None

    def merge(self) -> pd.DataFrame:
        """Merge dispatch with unit mapping on cennom."""
        merged = self.unit_mapper.dispatch.merge(
            self.unit_mapper.unit_mapping,
            left_on="cennom",
            right_on="plexosUnitName",
            how="left",
            # validate="m:1",
        )

        unmerged = merged[merged["plexosUnitName"].isnull()]
        merged = merged[merged["plexosUnitName"].notnull()]

        self.merged = merged
        self.unmerged = unmerged

        return self.merged, self.unmerged


if __name__ == "__main__":
    shts_data_handler = ShTermDataManager(scenario="E4")
    assets_mapper = AssetsMapper()

    mapper = UnitMapper(shts_data_handler, assets_mapper)
    mapper.materialize()

    merger = DispatchMerger(mapper)
    merged, unmerged = merger.merge()
