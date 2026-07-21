"""
Pipeline orchestrator for scenario processing.
Runs: handlers → unit_mapper → dispatch_merger → dispatch_distribution → DER → demand
"""

import pandas as pd
from pathlib import Path

from mapper.manager.sh_term_data import (
    ShTermDataManager,
)
from mapper.manager.assets_mapping import AssetsMapper

from mapper.modules.unit_mapper import UnitMapper
from mapper.modules.dispatch_merger import DispatchMerger
from mapper.modules.dispatch_distribution import (
    DispatchDistributionCalculator,
)
from mapper.modules.der_distribution import (
    DerDistributionCalculator,
)
from mapper.modules.demand_distribution import DemandProcessor
from mapper.modules.frequency_control_amount import (
    PrimaryFrequencyControlCalculator,
)


from mapper.modules.vector_processor import VectorProcessor
from mapper.utils.routes import VECTOR_FILES_PATH


class ShTermVectorOrchestrator:
    """Orchestrates the scenario processing pipeline."""

    def __init__(self, scenario_name):
        self.scenario_name = scenario_name
        self.scenario_data_handler = None
        self.assets_mapper = None
        self.unit_mapper = None
        self.merged_dispatch = None
        self.unmerged_dispatch = None
        self.dispatch_caculated = None
        self.der_mapping = None
        self.der_data = None
        self.demand_data = None

    def execute(self):
        """Execute the complete pipeline."""
        self._load_managers()
        self._load_mapper()
        self._merge_dispatch()
        self._distribute_dispatch()
        self._process_der()
        self._process_demand()
        self._process_pfrequency()
        self._format_and_export()

        # Just for vector
        return (
            self.assets_mapper,
            self.dispatch_aggregated,
            self.der_aggregated,
            self.demand_aggregated,
            self.pfc_rise,
            self.pfc_low,
            self.frequency_bias,
        )

    def _load_managers(self):
        """Load scenario and assets data."""
        self.shts_handler = ShTermDataManager(self.scenario_name)
        self.assets_mapper = AssetsMapper()

        self.shts_handler.materialize()
        self.assets_mapper.materialize()

    def _load_mapper(self):
        """Load unit mapping data."""
        self.unit_mapper = UnitMapper(self.shts_handler, self.assets_mapper)
        self.unit_mapper.materialize()

    def _merge_dispatch(self):
        """Merge dispatch with unit mapping constraints."""

        merger = DispatchMerger(self.unit_mapper)
        self.merged_dispatch, self.unmerged_dispatch = merger.merge()

    def _distribute_dispatch(self):
        """Calculate dispatch distribution from merged data."""
        dispatch_calculator = DispatchDistributionCalculator(self.merged_dispatch)
        self.dispatch_calculated = dispatch_calculator.calculate_all()

        self.dispatch_aggregated = self.dispatch_calculated.get(
            "aggregated", pd.DataFrame()
        )

    def _process_der(self):
        """Calculate DER distribution from unmerged data."""
        der_calculator = DerDistributionCalculator(
            self.unmerged_dispatch, self.assets_mapper
        )
        self.der_calculated = der_calculator.calculate_all()

        self.der_aggregated = self.der_calculated.get("aggregated", pd.DataFrame())

    def _process_demand(self):
        """Calculate demand distribution."""

        demand_calculator = DemandProcessor(self.shts_handler, self.assets_mapper)
        demand_calculated = demand_calculator.calculate()
        self.demand_aggregated = demand_calculated.get(
            "aggregated_by_zone", pd.DataFrame()
        )

    def _process_pfrequency(self):
        """Calculate frequency distribution."""
        frequency_calculator = PrimaryFrequencyControlCalculator(
            self.shts_handler, self.assets_mapper
        )
        frequency_calculated = frequency_calculator.calculate()

        self.pfc_rise = frequency_calculated.get("pfc_rise", pd.DataFrame())
        self.pfc_low = frequency_calculated.get("pfc_low", pd.DataFrame())
        self.frequency_bias = frequency_calculated.get("frequency_bias", pd.DataFrame())

    def _format_and_export(self):
        """Format vectors and export to Excel."""
        pfunit_table = self.assets_mapper.assets_data["queries"].get(
            "Query_pfUnit", pd.DataFrame()
        )

        processor = VectorProcessor(
            pfunit_table=pfunit_table,
            dispatch_distribution=self.dispatch_aggregated,
            der_distribution=self.der_aggregated,
            demand_distribution=self.demand_aggregated,
            pfc_rise=self.pfc_rise,
            pfc_low=self.pfc_low,
            frequency_bias=self.frequency_bias,
        )
        vectors = processor.materialize()

        output_path = VECTOR_FILES_PATH[self.scenario_name]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path) as writer:
            for sheet_name, df in vectors.items():
                clean_name = sheet_name
                df.to_excel(writer, sheet_name=clean_name, index=False)


if __name__ == "__main__":

    orchestrator = ShTermVectorOrchestrator("E4")
    orchestrator.execute()
