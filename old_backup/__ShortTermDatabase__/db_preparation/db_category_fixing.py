from integrator.managers import UnitManager


class CategoryFixer(UnitManager):

    def __init__(self, app):
        super().__init__(app=app)

        self._fix_categories()

    def _fix_categories(self):

        _ibr = self.ibr_units
        reactive_comp = self.reactive_compensators
        _sym = self.sym_units

        for unit in _ibr:
            if "PFV " in unit.pf_name.upper() and "BESS" in unit.pf_name.upper():
                # Move to DER units
                unit.pf_obj.cCategory = "Photovoltaic"
                unit.pf_obj.cSubCategory = "Solar + Storage"

            elif "PFV " in unit.pf_name.upper() and "BESS" not in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Photovoltaic"

            elif "PE " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Wind"

            elif "BESS" in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Storage"
                unit.pf_obj.cSubCategory = "Battery"

        for compensator in reactive_comp:
            compensator.pf_obj.cCategory = "Reactive power compensation"

        for unit in _sym:

            if "CSP " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Solar"

            elif "GEO " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Geothermal"

            elif "HE " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Hydro"
                unit.pf_obj.cSubCategory = "Storage"

            elif "HP " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Hydro"
                unit.pf_obj.cSubCategory = "Run of river"

            elif "CONDENSADOR " in unit.pf_name.upper():
                unit.pf_obj.cCategory = "Reactive power compensation"

            elif "TER " in unit.pf_name.upper():
                if unit.pf_obj.cSubCategory == "otros":
                    unit.pf_obj.cCategory = "Biomass"

                elif unit.pf_obj.cSubCategory == "Gas":
                    unit.pf_obj.cCategory = "Gas"

                elif unit.pf_obj.cSubCategory == "Diésel":
                    unit.pf_obj.cCategory = "Diesel"

                elif unit.pf_obj.cSubCategory == "Carbón":
                    unit.pf_obj.cCategory = "Coal"


if __name__ == "__main__":
    import time
    import PowerFactoryShortTermTools._powerfactory_app as _powerfactory_app

    start_time = time.time()

    category_fixer = CategoryFixer(app=_powerfactory_app.app)

    end_time = time.time()
    print(
        f"Time taken to create category fixer: "
        f"{round((end_time - start_time) / 60, 2)} minutes"
    )
