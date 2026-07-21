"""
Integration Pipeline
Orchestrates the sequence of steps to integrate a scenario into PowerFactory.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from integrator.modules.db_dispatch_integrating import (
    DispatchIntegrationStep,
)
from integrator.modules.db_units_activating import UnitsActivationStep
from integrator.modules.db_dyn_models_activating import (
    DynamicModelsActivationStep,
)
from integrator.modules.db_ppc_activating import PPCActivationStep
from integrator.modules.db_govs_activating import GovernorsActivationStep

from integrator.managers.assest_manager import UnitAssetManager


class IntegrationPipeline:
    """
    Pipeline that integrates a scenario into PowerFactory by:
    1. Integrating dispatch vectors (pgini, Kpf)
    2. Activating/deactivating units based on dispatch
    3. Activating dynamic models based on unit state
    4. Activating PPCs and syncing with P/S
    5. Activating governors based on unit bias
    """

    def __init__(self, app=None):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.steps = [
            DispatchIntegrationStep(app),
            UnitsActivationStep(app),
            DynamicModelsActivationStep(app),
            PPCActivationStep(app),
            GovernorsActivationStep(app),  # Warning:IBR. TO DO
        ]

    def execute(self, context):
        """
        Execute all steps in sequence.

        Args:
            context: ScenarioContext with scenario parameters
        """
        for step in self.steps:
            step.apply(context)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app

    pipeline = IntegrationPipeline(app=app)
    pipeline.execute(context=None)

    print("✅ Integration pipeline completed")
