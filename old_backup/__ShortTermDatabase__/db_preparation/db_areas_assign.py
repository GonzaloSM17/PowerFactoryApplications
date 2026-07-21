import time


class AreaAssignmentOperator:

    def __init__(self, app=None) -> None:

        if not app:
            print("Error: PowerFactory application instance is required.")
            return

        self.app = app
        self.project = self.app.GetActiveProject()

        # Check if __Areas_Base__ folder exists, create if not
        self.areas_folder = self._get_or_create_folder("__Areas_Base__")

        # Categories and sets
        self.categories = {
            "setPV": ("Photovoltaic", None),
            "setWind": ("Wind", None),
            "setBESS": ("Storage", "Battery"),
            "setBESS+PV": ("Photovoltaic", "Solar + Storage"),
            "setHidroStorage": ("Hydro", "Storage"),
            "setHidroRunOfRiver": ("Hydro", "Run of river"),
            "setGeothermal": ("Geothermal", None),
            "setSolarConcentration": ("Solar", None),
            "setSyncronousCondensor": ("Reactive power compensation", None),
        }

        self.thermal_set = "setTThermal"
        self.pmgd_set = "setDer"

        # Create sets for categorizing generators
        self.sets = self._create_selection_sets()

        # Initialize object containers for each set
        self.objects = self._initialize_objects()

        self._collect_generators()
        self._categorize_generators()
        self._add_objects_to_sets()

    def _get_or_create_folder(self, folder_name) -> object:

        folder = self.project.GetContents(f"{folder_name}.IntFolder")
        return (
            folder[0] if folder else self.project.CreateObject("IntFolder", folder_name)
        )

    def _create_selection_sets(self) -> dict:

        sets = {}
        for set_name in list(self.categories.keys()) + [
            self.thermal_set,
            self.pmgd_set,
        ]:
            set_select = self.areas_folder.GetContents(f"{set_name}.SetSelect")
            sets[set_name] = (
                set_select[0]
                if set_select
                else self.areas_folder.CreateObject("SetSelect", set_name)
            )
        return sets

    def _initialize_objects(self) -> dict:

        return {set_name: [] for set_name in self.sets}

    def _collect_generators(self) -> list:

        units = (
            [
                unit
                for unit in self.app.GetCalcRelevantObjects("*.ElmGenstat")
                if unit.cCategory != "Reactive power compensation"
            ]
            + self.app.GetCalcRelevantObjects("*.ElmAsm")
            + self.app.GetCalcRelevantObjects("*.ElmSym")
        )

        self.units = units

    def _categorize_generators(self) -> None:

        units = self.units

        for unit in units:
            cubicle = unit.GetAttribute("bus1")
            terminal = cubicle.GetParent() if cubicle else None
            assigned = False

            # Treatment for PMGD
            if "PMGD_" in unit.loc_name and unit.cCategory == "Renewable generation":
                self.objects[self.pmgd_set].append(unit)
                if terminal:
                    self.objects[self.pmgd_set].append(terminal)
                assigned = True
            else:
                # Loop through defined categories and subcategories
                for set_name, (category, subcategory) in self.categories.items():
                    # Treatment for wind parks
                    if category == "Wind" and unit.cCategory == "Wind":
                        self.objects["setWind"].append(unit)
                        if terminal:
                            self.objects["setWind"].append(terminal)
                        assigned = True
                        break
                    # Treatment for other generators
                    elif (
                        category == "Photovoltaic" and unit.cCategory == "Photovoltaic"
                    ):
                        if (
                            subcategory == "Solar + Storage"
                            and unit.cSubCategory == subcategory
                        ):
                            self.objects["setBESS+PV"].append(unit)
                            if terminal:
                                self.objects["setBESS+PV"].append(terminal)
                            assigned = True
                            break

                        elif (
                            category == "Photovoltaic" and subcategory is None
                        ) and unit.cSubCategory != "Solar + Storage":
                            self.objects["setPV"].append(unit)
                            if terminal:
                                self.objects["setPV"].append(terminal)
                            assigned = True

                    else:
                        if unit.cCategory == category and (
                            subcategory is None or unit.cSubCategory == subcategory
                        ):
                            self.objects[set_name].append(unit)
                            if terminal:
                                self.objects[set_name].append(terminal)
                            assigned = True
                            break

            # Assign to thermal set if not categorized
            if not assigned and "TER " in unit.loc_name:
                self.objects[self.thermal_set].append(unit)
                if terminal:
                    self.objects[self.thermal_set].append(terminal)

    def _add_objects_to_sets(self) -> None:
        for set_name, obj_list in self.objects.items():
            self.sets[set_name].AddRef(obj_list)


# Stand-alone execution
if __name__ == "__main__":

    import _powerfactory_app_

    _powerfactory_app_.app.Show()

    start_time = time.time()
    operator = AreaAssignmentOperator(app=_powerfactory_app_.app)

    finish_time = time.time()

    print(
        f"--- Area assignment completed in {finish_time - start_time:.2f} seconds ---"
    )
