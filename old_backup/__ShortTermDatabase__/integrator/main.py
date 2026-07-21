"""
Main Orchestrator for Short-Term Database Integration
Entry point for integrating scenarios into PowerFactory.
"""

import logging
import sys
from pathlib import Path

# Add ShortTermDatabase root to path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from integrator.models.scenario_context import ScenarioContext
from integrator.pipelines.db_integration import IntegrationPipeline
from integrator.pipelines.db_convergence import ConvergencePipeline
from integrator.utils.scenario_bootstrap import ScenarioMaterializer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# -------------------------
# Scenario Orchestrator
# -------------------------
class ScenarioIntegrateOrchestrator:
    """Orchestrates the execution of pipelines for multiple scenarios."""

    def __init__(self, app, pipelines: list):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.pipelines = pipelines        
        self.materializer = ScenarioMaterializer(app)

    def run(self, contexts: list):
        """Execute pipelines for all scenario contexts."""
        self.contexts = contexts

        for idx, context in enumerate(self.contexts, 1):
            logger.info(f"[{idx}/{len(self.contexts)}] {context.name}")

            try:
                self.materializer.materialize(context)

                desktop = self.app.GetDesktop()
                desktop.Close()

                for pipeline in self.pipelines:
                    pipeline.execute(context)

                desktop.Show()

            except Exception as e:
                logger.error(f"Failed: {e}")
                continue


# -------------------------
# Example Usage
# -------------------------
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app
    app.Show()

    scenarios = [
        ScenarioContext(
            name="E5",
            scenario_to_use="E5",
            hour=6,
            day=30,
            month=4,
            year=2027,
            demand_level="DB",
            hydrology_level="HM",
        ),
    ]

    pipelines = [
        IntegrationPipeline(app),
        # ConvergencePipeline(app),
    ]

    orchestrator = ScenarioIntegrateOrchestrator(
        app, pipelines=pipelines
    )
    orchestrator.run(scenarios)
