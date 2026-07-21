"""
PPC Activation Module
Activates/deactivates Power Plant Controllers (PPCs) and synchronizes them with Power System Stabilizers (P/S).
"""

from typing import List, Any, Dict


class ExcludeListBuilder:
    """Builds exclusion list from PowerFactory SetSelect in __Models_Handling folder"""

    def __init__(self, app):
        self.app = app
        self.project = app.GetActiveProject()

    def build(self) -> List[Any]:
        """Build and return exclusion list from PowerFactory"""
        exclude_list = []
        try:
            database_folder = self.project.GetContents("__Database_ShortTerm*")
            if not database_folder:
                raise IndexError("Database folder not found.")

            folder_tool = database_folder[-1].GetContents("__Models_Handling*")
            if not folder_tool:
                raise IndexError("ModelsH folder not found.")

            set_select = folder_tool[-1].GetContents("excludeList*.SetSelect")
            if not set_select:
                raise IndexError("excludeList SetSelect not found.")

            for obj_type in ["ElmGenstat", "ElmAsm", "ElmSym", "ElmDsl", "ElmComp"]:
                exclude_list.extend(set_select[-1].GetAll(obj_type))

        except (IndexError, AttributeError) as e:
            print(f"Warning: Could not retrieve exclude list. Error: {e}")

        return exclude_list


class PowerPlantController:
    """Business logic for a Power Plant Controller (PPC) synchronization"""

    def __init__(self, ppc_object):
        self.ppc_object = ppc_object

    def sync_with_ps(self, ps_names_map: Dict[str, Any]):
        """
        Synchronize PPC with Power System Stabilizers (P/S).
        First tries direct reference, then fallback to name matching.
        """
        # First priority: Direct P/S reference
        ps_references = self.ppc_object.GetReferences("P/S*.ElmComp")
        if ps_references:
            ps_reference = ps_references[-1]
            self.ppc_object.outserv = ps_reference.outserv
            return

        # Second priority: Name matching
        ppc_name_cleaned = self.ppc_object.loc_name
        if ppc_name_cleaned.startswith("PPC_"):
            ppc_name_cleaned = ppc_name_cleaned.replace("PPC_", "")
        elif ppc_name_cleaned.startswith("PPC "):
            ppc_name_cleaned = ppc_name_cleaned.replace("PPC ", "")
        elif ppc_name_cleaned.startswith("PPC"):
            ppc_name_cleaned = ppc_name_cleaned.replace("PPC", "")

        if ppc_name_cleaned in ps_names_map:
            self.ppc_object.outserv = ps_names_map[ppc_name_cleaned].outserv


class PPCActivationStep:
    """
    Step that activates PPCs and synchronizes them with Power System Stabilizers (P/S).

    Single responsibility: Configure PPC states based on P/S references and exclusion lists.
    """

    def __init__(self, app):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app

        # Get PPC composites
        self.ppc_composites = self._get_ppc_composites()

        # Get P/S composites and build name map
        self.ps_composites = self._get_ps_composites()
        self.ps_names_map = self._build_ps_names_map()

        # Build exclusion list
        self.exclude_list = ExcludeListBuilder(app).build()

    def _get_ppc_composites(self) -> List[Any]:
        """Get and filter PPC composite models"""
        ppc_all = self.app.GetCalcRelevantObjects(
            "PPC*.ElmComp"
        ) + self.app.GetCalcRelevantObjects("PPC*.ElmDsl")

        # Filter out PPCs with "PPC_" prefix (internal naming convention)
        filtered_ppc = [ppc for ppc in ppc_all if "PPC_" not in ppc.loc_name]

        return filtered_ppc

    def _get_ps_composites(self) -> List[Any]:
        """Get and filter P/S (Power System Stabilizer) composite models"""
        ps_all = self.app.GetCalcRelevantObjects("P/S*.ElmComp")

        # Filter out P/S with "P/S_" prefix (internal naming convention)
        filtered_ps = [ps for ps in ps_all if "P/S_" not in ps.loc_name]

        return filtered_ps

    def _build_ps_names_map(self) -> Dict[str, Any]:
        """Build name-to-object map for P/S units"""
        return {ps.loc_name.replace("P/S ", ""): ps for ps in self.ps_composites}

    def apply(self, context=None):
        """
        Apply PPC activation and synchronization with P/S.

        Args:
            context: ScenarioContext (optional for now, for future compatibility)
        """
        for ppc in self.ppc_composites:
            # Handle exclusion list
            if ppc in self.exclude_list:
                ppc.outserv = 1
                continue

            # Sync with P/S
            controller = PowerPlantController(ppc)
            controller.sync_with_ps(self.ps_names_map)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_
    import time

    app = _powerfactory_app_.app

    start_time = time.time()

    step = PPCActivationStep(app)
    step.apply()

    end_time = time.time()
    minutes, seconds = divmod(end_time - start_time, 60)
    print(
        f"Time taken to activate PPCs: {int(minutes)} minutes and {seconds:.2f} seconds"
    )
