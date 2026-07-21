"""
Convergence Pipeline
Orchestrates iterative adjustments to improve power flow convergence.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from integrator.modules.db_demand_adjusting import DemandAdjustmentStep
from integrator.modules.db_taps_adjustment import TapAdjustmentStep


class ConvergencePipeline:
    """
    Pipeline that improves convergence by:
    1. Adjusting demand to match dispatch target
    2. Adjusting transformer taps to improve voltage profile
    """

    def __init__(self, app):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.steps = [
            DemandAdjustmentStep(app),
            TapAdjustmentStep(app),
        ]

    def execute(self, context):
        """
        Execute all convergence steps in sequence.

        Args:
            context: ScenarioContext with scenario parameters
        """
        for step in self.steps:
            step.apply(context)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_
    from integrator.models.scenario_context import ScenarioContext

    app = _powerfactory_app_.app

    context = ScenarioContext(
        name="Test",
        scenario_to_use="E4",
        hour=15,
        day=15,
        month=6,
        year=2025,
        demand_level="High",
        hydrology_level="Normal",
    )

    pipeline = ConvergencePipeline(app)
    pipeline.execute(context)

    print("✅ Convergence pipeline completed")
