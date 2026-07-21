from dataclasses import dataclass
from datetime import datetime
import calendar
import time
import logging
from typing import Any

from integrator.models.scenario_context import ScenarioContext

logging.basicConfig(level=logging.INFO)


@dataclass
class ScenarioArtifacts:
    study_case: object
    scenario: object


class ScenarioMaterializer:
    """
    Materializes a study case and an operation scenario in PowerFactory
    from predefined base definitions.
    """

    def __init__(self, app: Any = None):

        if app is None:
            return

        self.app = app

        if self.app:
            self.project = app.GetActiveProject()

    # ---------- Public API ----------

    def materialize(self, context: ScenarioContext) -> ScenarioArtifacts:
        """
        Creates and activates the study case and scenario
        corresponding to the given ScenarioContext.
        """

        self._prepare_receiving_folders()
        self._load_bases()

        study_case = self._materialize_study_case(context)
        scenario = self._materialize_operation_scenario(context)

        return ScenarioArtifacts(
            study_case=study_case,
            scenario=scenario,
        )

    # ---------- Internal helpers ----------

    def _prepare_receiving_folders(self):
        study_folder = self.app.GetProjectFolder("study")
        scenario_folder = self.app.GetProjectFolder("scen")

        self.study_target = self._get_or_create_folder(
            study_folder, "__Scenarios_Integrated__"
        )
        self.scenario_target = self._get_or_create_folder(
            scenario_folder, "__Scenarios_Integrated__"
        )

    def _load_bases(self):
        try:
            db_shortterm_folder = self.project.GetContents("__Database_ShortTerm*")[-1]
            base_container = db_shortterm_folder.GetContents("__Scenarios_Integrated*")[
                -1
            ]

        except IndexError:
            raise RuntimeError("Base scenarios container not found.")

        try:
            self.base_study_case = base_container.GetContents(
                "baseStudyCase*.SetSelect"
            )[-1].GetAll("IntCase")[-1]
        except IndexError:
            raise RuntimeError("Base study case not found.")

        try:
            base_set = base_container.GetContents("baseScenarios*.SetSelect")[-1]
            self.base_scenarios = base_set.GetAll("IntScenario")
            self.base_folders = base_set.GetAll("IntFolder")
        except IndexError:
            self.base_scenarios = []
            self.base_folders = []

    def _materialize_study_case(self, context: ScenarioContext):
        last_day = calendar.monthrange(context.year, context.month)[1]
        timestamp = int(
            time.mktime(
                datetime(context.year, context.month, last_day, 23, 59, 59).timetuple()
            )
        )

        name = self._compose_name(context)

        self._delete_if_exists(self.study_target, name)

        study_case = self.study_target.PasteCopy(self.base_study_case)[-1]
        study_case.iStudyTime = timestamp
        study_case.loc_name = name
        study_case.Activate()

        logging.info(f"Study case materialized: {name}")
        return study_case

    def _materialize_operation_scenario(self, context: ScenarioContext):
        name = self._compose_name(context)

        for candidate in self._iter_base_scenarios():
            if context.name in candidate.loc_name:
                scenario = self.scenario_target.PasteCopy(candidate)[-1]
                scenario.loc_name = name
                scenario.Activate()

                logging.info(f"Scenario materialized: {name}")
                return scenario

        raise RuntimeError(f"Base scenario '{context.name}' not found.")

    # ---------- Utilities ----------

    def _compose_name(self, context: ScenarioContext) -> str:
        return (
            f"{context.name} "
            f"{context.year}.{context.month:02d}.{context.day} "
            f"{context.hour}hrs "
            f"{context.demand_level} "
            f"{context.hydrology_level}"
        )

    def _delete_if_exists(self, folder, name: str):
        for obj in folder.GetContents("*"):
            if obj.loc_name == name:
                obj.Deactivate()
                obj.Delete()

    def _iter_base_scenarios(self):
        yield from self.base_scenarios
        for folder in self.base_folders:
            yield from folder.GetContents("*.IntScenario")

    def _get_or_create_folder(self, parent, name: str):
        existing = parent.GetContents(f"{name}.IntFolder")
        return existing[-1] if existing else parent.CreateObject("IntFolder", name)


# Standalone execution
if __name__ == "__main__":

    import _powerfactory_app_

    context = ScenarioContext(
        name="Pepe",
        scenario_to_use="E4",
        hour=12,
        day=22,
        month=4,
        year=2027,
        demand_level="DA",
        hydrology_level="HM",
    )

    materializer = ScenarioMaterializer(app=_powerfactory_app_.app)
    artifacts = materializer.materialize(context)

    print("Scenario materialization completed successfully.")
