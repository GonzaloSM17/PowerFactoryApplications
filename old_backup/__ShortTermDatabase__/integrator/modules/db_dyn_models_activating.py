"""
Dynamic Models Activation Module
Activates/deactivates dynamic models (c_pmod) based on unit state, capacity, and exclusion lists.
"""

from typing import List, Any

from integrator.managers.assest_manager import UnitAssetManager

# Constants
MIN_CAPACITY = {
    "ElmSym": 10,
    "ElmGenstat": 12,
    "ElmAsm": 0,
}


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


class IncludeListBuilder:
    """Builds inclusion list from PowerFactory SetSelect in __Models_Handling folder"""

    def __init__(self, app):
        self.app = app
        self.project = app.GetActiveProject()

    def build(self) -> List[Any]:
        """Build and return inclusion list from PowerFactory"""
        include_list = []
        try:
            database_folder = self.project.GetContents("__Database_ShortTerm*")
            if not database_folder:
                raise IndexError("Database folder not found.")

            folder_tool = database_folder[-1].GetContents("__Models_Handling*")
            if not folder_tool:
                raise IndexError("ModelsH folder not found.")

            set_select = folder_tool[-1].GetContents("includeList*.SetSelect")
            if not set_select:
                raise IndexError("includeList SetSelect not found.")

            for obj_type in ["ElmGenstat", "ElmAsm", "ElmSym"]:
                include_list.extend(set_select[-1].GetAll(obj_type))

        except (IndexError, AttributeError) as e:
            print(f"Warning: Could not retrieve include list. Error: {e}")

        return include_list


class DynamicModelActivator:
    """Business logic for activating/deactivating a dynamic model (c_pmod)"""

    def __init__(self, unit, capacity_threshold=None, exclude_list=None):
        self.unit = unit
        self.model_unit = unit.c_pmod
        self.total_capacity = None
        self.exclude_list = exclude_list

        try:
            if self.unit.cCategory == "Reactive Power Compensation":
                self.total_capacity = 999
            else:
                self.total_capacity = unit.P_max * unit.ngnum
        except AttributeError:
            pass

        self.capacity_threshold = (
            capacity_threshold if capacity_threshold is not None else 0
        )

    def _is_out_of_service(self):
        return self.unit.outserv != 0

    def _is_below_capacity_threshold(self):
        return (
            self.total_capacity is not None
            and self.total_capacity <= self.capacity_threshold
            and "PMGD_" not in self.unit.loc_name
        )

    def _is_genstat_and_not_reactive(self):
        return (
            self.unit.GetClassName() == "ElmGenstat"
            and self.unit.cCategory != "Reactive Power Compensation"
        )

    def _is_constant_impedance(self):
        return self.unit.iSimModel == 3

    def _check_outservice_conditions(self):
        if self._is_out_of_service():
            return True

        if self._is_below_capacity_threshold():
            return True

        if self._is_genstat_and_not_reactive():
            if self._is_constant_impedance():
                return True

        return False

    def update_ppc_status(self):
        """Updates PPC (Power Plant Controller) status based on model state"""
        ppc_direct = self.model_unit.GetContents(
            "PPC*.ElmComp"
        ) + self.model_unit.GetContents("PPC*.ElmDsl")

        if ppc_direct:
            self.ppc = ppc_direct[-1]

            if self.exclude_list is not None and self.ppc in self.exclude_list:
                self.ppc.outserv = 1
            else:
                self.ppc.outserv = self.model_unit.outserv

            superior_ppc_references = self.ppc.GetReferences("*.ElmComp")
            if superior_ppc_references:
                superior_ppc_ref_last = superior_ppc_references[-1]
                if (
                    self.exclude_list is not None
                    and superior_ppc_ref_last in self.exclude_list
                ):
                    superior_ppc_ref_last.outserv = 1
                else:
                    superior_ppc_ref_last.outserv = self.ppc.outserv
            return

        ppc_references_composite = self.model_unit.GetReferences("PPC*.ElmComp")
        if ppc_references_composite:
            ppc_ref = ppc_references_composite[-1]
            ppc_ref.outserv = self.model_unit.outserv

            superior_ppc_references = ppc_ref.GetReferences("*.ElmComp")
            if superior_ppc_references:
                superior_ppc_references[-1].outserv = ppc_ref.outserv

    def activate(self):
        """Set dynamic model outservice status and update PPC"""
        if self.model_unit:
            outserv = self._check_outservice_conditions()
            self.model_unit.outserv = 1 if outserv else 0
            self.update_ppc_status()


class DynamicModelsActivationStep:
    """
    Step that activates/deactivates dynamic models (c_pmod) based on:
    - Unit service status
    - Capacity thresholds
    - Exclusion/inclusion lists
    """

    def __init__(self, app=None):
        if app is None:
            raise ValueError("PowerFactory app instance is required.")

        self.app = app
        self.asset_manager = UnitAssetManager(app)

        # Build lists
        self.exclude_list = ExcludeListBuilder(app).build()
        self.include_list = IncludeListBuilder(app).build()

    def _get_capacity_threshold(self, unit, unit_class):
        """Get capacity threshold for a unit"""
        activator = DynamicModelActivator(unit, exclude_list=self.exclude_list)
        if activator._is_genstat_and_not_reactive():
            return 0
        return MIN_CAPACITY.get(unit_class)

    def _process_unit(self, unit):
        """Process a single unit's dynamic model"""
        unit_class = unit.GetClassName()

        # Handle exclusion list
        if unit in self.exclude_list:
            if unit.c_pmod:
                unit.c_pmod.outserv = 1

            capacity_threshold = self._get_capacity_threshold(unit, unit_class)
            activator = DynamicModelActivator(
                unit,
                capacity_threshold=capacity_threshold,
                exclude_list=self.exclude_list,
            )
            activator.update_ppc_status()
            return

        # Handle inclusion list
        if unit in self.include_list:
            if unit.c_pmod and unit.outserv == 0:
                unit.c_pmod.outserv = 0
            else:
                unit.c_pmod.outserv = 1

            capacity_threshold = self._get_capacity_threshold(unit, unit_class)
            activator = DynamicModelActivator(
                unit,
                capacity_threshold=capacity_threshold,
                exclude_list=self.exclude_list,
            )
            activator.update_ppc_status()
            return

        # Normal processing by unit type
        if unit_class == "ElmSym":
            capacity_threshold = MIN_CAPACITY["ElmSym"]
        elif unit_class == "ElmGenstat":
            if unit.cCategory == "Reactive Power Compensation":
                capacity_threshold = 0
            else:
                capacity_threshold = MIN_CAPACITY["ElmGenstat"]
        elif unit_class == "ElmAsm":
            capacity_threshold = MIN_CAPACITY["ElmAsm"]
        elif unit_class == "ElmSvs":
            capacity_threshold = None
        else:
            capacity_threshold = self._get_capacity_threshold(unit, unit_class)

        activator = DynamicModelActivator(
            unit, capacity_threshold, exclude_list=self.exclude_list
        )
        activator.activate()

    def apply(self, context=None):
        """
        Apply dynamic model activation to all generation assets.

        Args:
            context: ScenarioContext (optional for now, for future compatibility)
        """
        # Process sync assets
        for asset in self.asset_manager.sym_assets:
            if "HVDC" not in asset.pf_name:
                self._process_unit(asset.pf_obj)

        # Process IBR assets
        for asset in self.asset_manager.no_sym_assets:
            if "HVDC" not in asset.pf_name:
                self._process_unit(asset.pf_obj)

        # Process async assets
        for asset in self.asset_manager.a_sym_assets:
            if "HVDC" not in asset.pf_name:
                self._process_unit(asset.pf_obj)

        # Process reactive assets
        for asset in self.asset_manager.reactive_assets:
            self._process_unit(asset.pf_obj)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_
    import time

    app = _powerfactory_app_.app

    start_time = time.time()

    step = DynamicModelsActivationStep(app)
    step.apply()

    end_time = time.time()
    minutes, seconds = divmod(end_time - start_time, 60)
    print(
        f"Time taken to activate models: {int(minutes)} minutes and {seconds:.2f} seconds"
    )
