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

from integrator.main import ScenarioIntegrateOrchestrator

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
# Example Usage
# -------------------------
if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app
    app.Show()

    scenarios = [
        ScenarioContext(
            name="Test1",
            scenario_to_use="E4",
            hour=12,
            day=15,
            month=12,
            year=2027,
            demand_level="DA",
            hydrology_level="HM",
        ),
        ScenarioContext(
            name="Test2",
            scenario_to_use="E4",
            hour=12,
            day=15,
            month=12,
            year=2027,
            demand_level="DA",
            hydrology_level="HM",
        ),
        ScenarioContext(
            name="Test3",
            scenario_to_use="E4",
            hour=12,
            day=15,
            month=12,
            year=2027,
            demand_level="DA",
            hydrology_level="HM",
        )
    ]

    pipelines = [
        IntegrationPipeline(app),
        # ConvergencePipeline(app),
    ]

    for scenario in scenarios:
        logger.info(f"Prepared scenario context: {scenario}")

        orchestrator = ScenarioIntegrateOrchestrator(
            app, pipelines=pipelines
        )
        orchestrator.run(contexts=scenarios)
