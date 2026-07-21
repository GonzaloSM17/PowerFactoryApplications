"""
Demand Adjustment Module
Adjusts electrical loads iteratively to match target generation from dispatch vectors.
"""

import logging
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from integrator.managers.assest_manager import (
    UnitAssetManager,
    LoadManager,
)
from integrator.utils.vector_io import VectorIO
from integrator.utils.routes import LOADS_DATABASE

logger = logging.getLogger(__name__)


class DemandAdjustmentStep:
    """
    Adjusts electrical loads to match dispatch target.
    Uses iterative load flow to converge generation to target value.
    """

    def __init__(self, app):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.asset_manager = UnitAssetManager(app)
        self.load_manager = LoadManager(app)
        self.ldf = app.GetFromStudyCase("ComLdf")

    def apply(self, context):
        """
        Apply demand adjustment using context parameters.

        Args:
            context: ScenarioContext with scenario_to_use and hour
        """
        # Get auxiliary loads
        self._load_aass_data()

        # Adjust special loads
        self._adjust_aass_loads()

        self._get_generation_target(context.scenario_to_use, context.hour)
        self._get_adjustable_loads()
        self._get_summary_grid()
        self._adjust_loads_iteratively()

        self._update_reference_machine()

    def _load_aass_data(self):
        """Load auxiliary services loads from Excel"""
        try:
            df = pd.read_excel(LOADS_DATABASE, sheet_name="AASS", usecols="A:D")
            df.columns = ["pf_name", "plini", "qlini", "pf_name_unit"]
            self.loads_aass = df
        except FileNotFoundError as e:
            logger.warning("Could not load AASS data: %s", e)
            self.loads_aass = None

    def _adjust_aass_loads(self):
        """Adjust auxiliary services loads based on unit status"""
        if self.loads_aass is None:
            return

        loads_dict = {asset.pf_name: asset.pf_obj for asset in self.load_manager.loads}
        units_dict = {
            **{asset.pf_name: asset.pf_obj for asset in self.asset_manager.sym_assets},
            **{
                asset.pf_name: asset.pf_obj
                for asset in self.asset_manager.no_sym_assets
            },
            **{
                asset.pf_name: asset.pf_obj for asset in self.asset_manager.a_sym_assets
            },
        }

        # Substation AASS
        ssaa_ssee = self.loads_aass.query("pf_name_unit == 'S/E'").dropna(
            subset=["pf_name_unit"]
        )

        for _, row in ssaa_ssee.iterrows():
            if row["pf_name"] in loads_dict:
                load = loads_dict[row["pf_name"]]
                try:
                    if load.plini == 0:
                        load.plini = row["plini"]
                        load.qlini = row["qlini"]
                    load.outserv = 0
                except Exception as e:
                    logger.exception("Error adjusting load %s: %s", row["pf_name"], e)

        # Unit-specific AASS
        ssaa_unit = self.loads_aass.query("pf_name_unit != 'S/E'").dropna(
            subset=["pf_name_unit"]
        )

        for _, row in ssaa_unit.iterrows():
            if row["pf_name"] in loads_dict and row["pf_name_unit"] in units_dict:
                load = loads_dict[row["pf_name"]]
                unit = units_dict[row["pf_name_unit"]]

                try:
                    load.plini = row["plini"]
                    load.qlini = row["qlini"]
                    load.outserv = unit.outserv
                except Exception as e:
                    logger.exception("Error adjusting load %s: %s", row["pf_name"], e)

    def _get_generation_target(self, scenario, hour):
        """Get total generation target from vector"""
        vector_io = VectorIO(scenario=scenario, hour=hour)
        balance = vector_io.get_vector("balance")

        # Defensive: ensure balance is a DataFrame with expected rows
        total_gen = None
        bess_gen = 0
        if balance is None or balance.empty:
            logger.warning("Balance vector missing or empty for %s H%d", scenario, hour)
            total_gen = 0
            bess_gen = 0
        else:
            try:
                total_row = balance[balance["-"] == "generationTotal(MW)"]
                if not total_row.empty:
                    total_gen = total_row["balance"].values[0]
                else:
                    total_gen = 0

                bess_row = balance[balance["-"] == "unit(-)Charging(MW)"]
                if not bess_row.empty:
                    bess_gen = bess_row["balance"].values[0]
                else:
                    bess_gen = 0

            except Exception as e:
                logger.exception("Malformed balance vector: %s", e)
                total_gen = 0
                bess_gen = 0

        # Adjust for BESS discharge (negative = charging)
        if bess_gen > 0:
            self.generation_target = total_gen - bess_gen
        else:
            self.generation_target = total_gen

        logger.info("Generation target: %.2f MW", self.generation_target)

    def _get_adjustable_loads(self):
        """Get in-service residential loads (Carga R), excluding UFLS loads"""
        self.adjustable_loads = []

        # # Get UFLS load names to exclude (if loaded)
        # ufls_names = []
        # if hasattr(self, "loads_ufls") and self.loads_ufls is not None:
        #     ufls_names = self.loads_ufls["pf_name"].tolist()

        for asset in self.load_manager.loads:
            load = asset.pf_obj
            typ_name = getattr(load.typ_id, "loc_name", "")

            # Include only in-service residential loads, excluding UFLS
            if (
                load.outserv == 0
                and "Carga R" in typ_name
                # and asset.pf_name not in ufls_names
            ):
                self.adjustable_loads.append(load)

    def _get_summary_grid(self):
        """Get summary grid for generation monitoring"""
        grids = self.app.GetCalcRelevantObjects("*.ElmNet")

        for grid in grids:
            if "Summary" in grid.loc_name:
                self.summary_grid = grid
                return

        raise RuntimeError("Summary grid not found")

    def _adjust_loads_iteratively(self):
        """Iteratively adjust loads to match generation target"""
        tolerance = 0.3  # MW
        max_iterations = 3
        alpha = 0.85  # Dampening factor

        for iteration in range(max_iterations):
            # Run load flow
            self.ldf.Execute()

            # Get current generation
            current_gen = self.summary_grid.GetAttribute("c:GenP")
            error = self.generation_target - current_gen

            if abs(error) <= tolerance:
                logger.info("Converged in %d iterations", (iteration + 1))
                return

            # Calculate load adjustment
            damped_error = error * alpha
            current_load_sum = sum(load.plini for load in self.adjustable_loads)
            target_load_sum = current_load_sum + damped_error
            scale_factor = target_load_sum / current_load_sum

            # Apply adjustment
            for load in self.adjustable_loads:
                load.plini *= scale_factor

            logger.info("Iteration %d: Error = %.2f MW", (iteration + 1), error)

        logger.warning("Maximum iterations reached (error = %.2f MW)", abs(error))

    def _update_reference_machine(self):
        """Update reference machine dispatch to match load flow result"""
        for asset in self.asset_manager.sym_assets:
            unit = asset.pf_obj

            if unit.ip_ctrl and unit.outserv == 0:
                self.ldf.Execute()

                original_pgini = unit.pgini
                lf_pgini = round(unit.GetAttribute("m:Psum:bus1") / unit.ngnum, 3)

                logger.info(
                    "Reference machine %s: %.3f -> %.3f MW",
                    unit.loc_name,
                    original_pgini,
                    lf_pgini,
                )

                unit.pgini = lf_pgini


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_
    from integrator.models.scenario_context import ScenarioContext

    app = _powerfactory_app_.app
    app.Show()

    context = ScenarioContext(
        name="Test",
        scenario_to_use="E4",
        hour=14,
        day=22,
        month=12,
        year=2027,
        demand_level="DA",
        hydrology_level="HM",
    )

    step = DemandAdjustmentStep(app)
    step.apply(context)

    logger.info("\u2705 Demand adjustment completed")
