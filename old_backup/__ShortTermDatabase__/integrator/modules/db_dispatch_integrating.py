"""Dispatch Integration Module
Integrates generation dispatch vectors into PowerFactory units.
Applies pgini values from Excel vectors and adjusts based on technical limits.
"""

import os
import logging
import pandas as pd
from typing import Any
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from integrator.managers.assest_manager import UnitAssetManager
from integrator.utils.vector_io import VectorIO
from integrator.utils.routes import OUTPUT_REPORT_PATH
from integrator.utils.constants import (
    MINIMUM_TECHNICAL_DISPATCH,
    REFERENCE_MACHINES,
)
from config import Config

logger = logging.getLogger(__name__)


class DispatchIntegrationStep:
    """
    Integrates dispatch vectors into PowerFactory units.

    Applies generation setpoints (pgini) and bias factors (Kpf) from vectors,
    adjusts for technical limits, and generates integration reports.

    Requires an injected UnitAssetManager to decouple from PowerFactory dependency.
    """

    def __init__(
        self, app: Any = None, asset_manager: UnitAssetManager = None
    ):
        """Initialize dispatch integration step.

        Args:
            asset_manager: UnitAssetManager instance (injected dependency)
            app: optional PowerFactory application object
            config: Config instance (optional, defaults to global Config)
        """
        if asset_manager is None:
            self.asset_manager = UnitAssetManager(app)

        if app is not None:
            self.app = app

        
        # self.config = config or Config
        # self.app = asset_manager.app  # Access app through manager

        # Dispatch maps
        self.pgini_map = {}
        self.bias_map = {}

        # Report tracking
        self.unassigned_units = {}
        self.adjusted_units = {}
        self.minimum_adjusted_units = {}

    def apply(self, context):
        """
        Apply dispatch integration using context parameters.

        Args:
            context: ScenarioContext with scenario_to_use and hour
        """
        # Load dispatch vectors
        self._load_vectors(context.scenario_to_use, context.hour)

        # Apply dispatch to units
        self._apply_dispatch_to_units()

        # Select reference machine (swing bus)
        self._select_reference_machine()

        # Generate integration report
        self._generate_report(context.scenario_to_use, context.hour)

    def _load_vectors(self, scenario, hour):
        """Load dispatch and bias vectors from Excel"""
        vector_io = VectorIO(scenario=scenario, hour=hour)

        # Load pgini vectors
        for vector_type in ["symVector", "noSymVector", "aSymVector", "derVector"]:
            df = vector_io.get_vector(vector_type)
            if df is not None:
                for _, row in df.iterrows():
                    unit_name = row["pf_name"]
                    pgini = row["pgini"] if pd.notna(row["pgini"]) else 0
                    self.pgini_map[unit_name] = pgini

        # Load bias vector (Kpf)
        bias_df = vector_io.get_vector("biasVector")
        if bias_df is not None:
            for _, row in bias_df.iterrows():
                unit_name = row["pf_name"]
                kpf = row["Kpf"] if pd.notna(row["Kpf"]) else 0
                if kpf > 0:
                    self.bias_map[unit_name] = kpf

    def _apply_dispatch_to_units(self, minimum_threshold=0.2):
        """Apply dispatch to all units with adjustments"""
        total_adjustment = 0

        # Create unified units dictionary
        all_units = {}
        for asset in self.asset_manager.sym_assets:
            all_units[asset.pf_name] = asset.pf_obj
            # print(asset.pf_name)

        for asset in self.asset_manager.no_sym_assets:
            all_units[asset.pf_name] = asset.pf_obj
            # print(asset.pf_name)

        for asset in self.asset_manager.a_sym_assets:
            all_units[asset.pf_name] = asset.pf_obj
            # print(asset.pf_name)

        # for asset in self.asset_manager.der_assets:
        #     all_units[asset.pf_name] = asset.pf_obj
        #     print(asset.pf_name)

        for unit_name, pgini in self.pgini_map.items():
            if unit_name in all_units:

                unit = all_units[unit_name]

                # Apply bias (Kpf)
                try:
                    unit.Kpf = self.bias_map.get(unit_name, 0)
                except Exception:
                    # Some PF objects don't expose Kpf; ignore safely
                    pass

                # Apply dispatch based on unit type
                class_name = unit.GetClassName()
                if class_name == "ElmSym":
                    adjustment = self._apply_sync_dispatch(
                        unit, unit_name, pgini, minimum_threshold
                    )
                    total_adjustment += adjustment

                elif class_name == "ElmGenstat":
                    adjustment = self._apply_ibr_dispatch(unit, unit_name, pgini)
                    total_adjustment += adjustment

                else:
                    try:
                        unit.pgini = pgini
                    except Exception:
                        pass

                # Ensure no reference machine (will be set later)
                try:
                    unit.ip_ctrl = 0
                except Exception:
                    pass

            else:
                # Track unassigned units
                if pgini > 0:
                    self.unassigned_units[unit_name] = pgini

        logger.info("Total dispatch adjustment: %.2f MW", total_adjustment)

    def _apply_sync_dispatch(self, unit, unit_name, pgini, minimum_threshold):
        """Apply dispatch to synchronous machine with special handling"""
        # # Set minimum technical dispatch if defined
        # if unit_name in MINIMUM_TECHNICAL_DISPATCH:
        #     try:
        #         unit.Pmin_uc = MINIMUM_TECHNICAL_DISPATCH[unit_name]
        #     except Exception:
        #         pass

        # Check if dispatch is below minimum threshold
        # try:
        #     pmin = unit.Pmin_uc
        # except Exception:
        #     pmin = 0

        # if pgini > 0 and pmin > 0:
        #     ratio = abs(pgini / pmin)

        #     if ratio < minimum_threshold:
        #         # Adjust minimum to match dispatch
        #         old_pmin = pmin
        #         new_pmin = pgini
        #         delta = old_pmin - new_pmin

        #         self.minimum_adjusted_units[unit_name] = {
        #             "old_pmin": old_pmin,
        #             "new_pmin": new_pmin,
        #             "delta": delta,
        #         }

        #         try:
        #             unit.Pmin_uc = pgini
        #         except Exception:
        #             pass

        # Apply dispatch with limit checking
        return self._apply_dispatch_with_limits(unit, unit_name, pgini)

    def _apply_ibr_dispatch(self, unit, unit_name, pgini):
        """Apply dispatch to inverter-based resource"""
        return self._apply_dispatch_with_limits(unit, unit_name, pgini)

    def _apply_dispatch_with_limits(self, unit, unit_name, pgini):
        """Apply dispatch respecting technical limits (Pmin/Pmax)"""
        if pgini == 0:
            try:
                unit.pgini = 0
            except Exception:
                pass
            return 0

        # Get limits
        try:
            p_min = unit.Pmin_uc
        except Exception:
            p_min = 0
        try:
            p_max = min(unit.Pmax_uc, unit.Pnom)
        except Exception:
            p_max = unit.Pmax_uc

        # Adjust dispatch to limits
        original_pgini = pgini
        adjusted_pgini = max(p_min, min(original_pgini, p_max - 0.01))

        # Calculate adjustment
        try:
            ngnum = unit.ngnum
        except Exception:
            ngnum = 1

        adjustment = (adjusted_pgini - original_pgini) * ngnum

        if abs(adjustment) > 0.01:
            self.adjusted_units[unit_name] = {
                "original": original_pgini,
                "adjusted": adjusted_pgini,
                "delta": adjustment,
                "delta_abs": abs(adjustment),
            }

            logger.info(
                "Adjusted %s: %.2f -> %.2f MW",
                unit_name,
                original_pgini,
                adjusted_pgini,
            )

        try:
            unit.pgini = adjusted_pgini
        except Exception:
            pass
        return adjustment

    def _select_reference_machine(self):
        """Select reference machine (swing bus) from priority list"""
        all_units = {
            asset.pf_name: asset.pf_obj
            for asset in getattr(self.asset_manager, "sym_assets", [])
        }

        for ref_name in REFERENCE_MACHINES:
            if ref_name in all_units:
                unit = all_units[ref_name]

                try:
                    if unit.pgini > 0 and unit.outserv == 0:
                        unit.ip_ctrl = 1
                        logger.info(
                            "Reference machine selected: %s (dispatch=%.2f MW)",
                            ref_name,
                            unit.pgini,
                        )
                        return
                except Exception:
                    continue

        logger.warning("No suitable reference machine found in priority list")

    def _generate_report(self, scenario, hour):
        """Generate Excel report with integration details"""
        report_path = os.path.join(
            OUTPUT_REPORT_PATH,
            f"{scenario}_H{hour:02d}_dispatch_integration_report.xlsx",
        )

        with pd.ExcelWriter(report_path) as writer:
            # Sheet 1: Minimum technical dispatch adjustments
            if self.minimum_adjusted_units:
                df_min = pd.DataFrame.from_dict(
                    self.minimum_adjusted_units, orient="index"
                )
                df_min = df_min.sort_values(by="delta", ascending=False)
                df_min.to_excel(
                    writer, sheet_name="minimum_dispatch_adjusted", index=True
                )

            # Sheet 2: Dispatch adjustments (limits)
            if self.adjusted_units:
                df_adj = pd.DataFrame.from_dict(self.adjusted_units, orient="index")
                df_adj = df_adj.sort_values(by="delta_abs", ascending=False)
                df_adj.to_excel(writer, sheet_name="dispatch_adjusted", index=True)

            # Sheet 3: Unassigned units (not found in PowerFactory)
            if self.unassigned_units:
                df_una = pd.DataFrame.from_dict(
                    self.unassigned_units, orient="index", columns=["pgini"]
                )
                df_una = df_una.sort_values(by="pgini", ascending=False)
                df_una.to_excel(writer, sheet_name="unassigned_units", index=True)

        logger.info("Integration report saved: %s", report_path)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_
    from integrator.models.scenario_context import ScenarioContext

    app = _powerfactory_app_.app
    app.Show()

    desktop = app.GetDesktop()
    # desktop.Close()

    # Inject dependencies
    asset_manager = UnitAssetManager(app)

    context = ScenarioContext(
        name="Test",
        scenario_to_use="E4",
        hour=14,
        day=20,
        month=12,
        year=2027,
        demand_level="DA",
        hydrology_level="HM",
    )

    step = DispatchIntegrationStep(app=app, asset_manager=asset_manager)
    step.apply(context)

    logger.info("✅ Dispatch integration completed")

    # desktop.Show()
