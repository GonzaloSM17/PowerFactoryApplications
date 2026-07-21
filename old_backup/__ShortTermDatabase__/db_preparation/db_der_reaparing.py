der_new_capacity = {
    "PMGD_CALAMA 110": 78.94737,
    "PMGD_CRUCERO 220": 35.78947,
    "PMGD_ESMERALDA 110": 83.78947,
    "PMGD_LAGUNAS 220": 47.36842,
    "PMGD_POZO ALMONTE 110_1": 56.68421,
    "PMGD_POZO ALMONTE 110_2": 56.68421,
    "PMGD_CARDONES 110": 138.73684,
    "PMGD_DIEGO DE ALMAGRO 110": 43.15789,
    "PMGD_MAITENCILLO 110": 65.15789,
    "PMGD_EL PEÑON 110": 246.21053,
    "PMGD_LOS VILOS 110": 130.52632,
    "PMGD_PAN DE AZUCAR 66": 115.78947,
    "PMGD_QUILLOTA 110": 32.84211,
    "PMGD_AGUA SANTA 110": 149.15789,
    "PMGD_LAS VEGAS 110": 135.05263,
    "PMGD_BATUCO 110": 29.26316,
    "PMGD_BATUCO 110_2": 29.26316,
    "PMGD_CERRO NAVIA 110": 48.21053,
    "PMGD_CHENA 110": 82.31579,
    "PMGD_FLORIDA 110": 80.52632,
    "PMGD_RENCA 110": 51.68421,
    "PMGD_ALTO JAHUEL 110": 73.68421,
    "PMGD_ALTO MELIPILLA 110": 200.00000,
    "PMGD_POLPAICO 220": 129.36842,
    "PMGD_RAPEL 220": 212.73684,
    "PMGD_CHILLAN 66": 244.31579,
    "PMGD_ITAHUE 66": 111.15789,
    "PMGD_LINARES 66": 131.89474,
    "PMGD_MALLOA 66_1": 72.94737,
    "PMGD_MALLOA 66_2": 72.94737,
    "PMGD_PAINE 66_1": 111.94737,
    "PMGD_PAINE 66_2": 111.94737,
    "PMGD_PARRAL 66": 134.31579,
    "PMGD_PUNTA DE CORTES_1": 10.17544,
    "PMGD_PUNTA DE CORTES_2": 10.17544,
    "PMGD_PUNTA DE CORTES_3": 10.17544,
    "PMGD_RANCAGUA 66_1": 110.47368,
    "PMGD_RANCAGUA 66_2": 110.47368,
    "PMGD_SAN JAVIER 66": 52.10526,
    "PMGD_TALCA 66": 135.36842,
    "PMGD_TENO 66": 194.31579,
    "PMGD_TINGUIRIRICA 154": 71.89474,
    "PMGD_CHARRUA 66": 251.15789,
    "PMGD_HORCONES 66": 43.15789,
    "PMGD_CHILOE 110": 50.52632,
    "PMGD_DUQUECO": 32.52632,
    "PMGD_MULCHEN 220": 95.78947,
    "PMGD_TEMUCO 66": 34.10526,
}

import unicodedata


class DerRepairingOperator:

    def __init__(self, app=None) -> None:
        if not app:
            print("Error: PowerFactory application instance is required.")
            return

        self.app = app

        self.project = self.app.GetActiveProject()
        self.set_select = None
        self.repaired_elements = {}

    def _remove_accents(self, text: str) -> str:
        return "".join(
            c
            for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )

    def process_all_variations(self, elements_to_repair: dict) -> dict:

        self._load_set_select()

        if not self.set_select:
            return {}

        all_repairs = {}
        variations = self._get_variations()

        for variation in variations:
            all_repairs[variation.loc_name] = {}
            stages = self._get_variation_stages(variation)

            variation.Activate()

            for stage in stages:
                if "PMGD" not in stage.loc_name:
                    continue

                stage.Activate()
                stage_repairs = self._repair_elements_in_stage(
                    stage, elements_to_repair
                )
                all_repairs[variation.loc_name][stage.loc_name] = stage_repairs

            variation.Deactivate()

        return all_repairs

    def _load_set_select(self) -> bool:
        try:
            # Navigate to __Database_ShortTerm__ > _Der_Redimensioning > derVariations
            database = self.project.GetContents("__Database_ShortTerm*.IntFolder")
            if not database:
                return False

            der_folder = database[0].GetContents("__Der_Redimensioning*.IntFolder")
            if not der_folder:
                return False

            set_select = der_folder[0].GetContents("toRedimensioning*.SetSelect")
            if set_select:
                self.set_select = set_select[0]
                return True
            return False

        except Exception as e:
            print(f"Error loading SetSelect: {e}")
            return False

    def _get_variations(self) -> list:
        if not self.set_select:
            return []

        try:

            return self.set_select.GetAll("IntScheme") or []

        except Exception as e:
            print(f"Error getting variations: {e}")
            return []

    def _get_variation_stages(self, variation) -> list:
        try:
            return variation.GetContents("*.IntSstage") or []
        except Exception as e:
            print(f"Error getting stages: {e}")
            return []

    def _repair_elements_in_stage(self, stage, elements_to_repair: dict) -> dict:
        stage_repairs = {}

        stage_name = stage.loc_name
        search_name = stage_name.replace("PMGD ", "PMGD_")
        search_name = self._remove_accents(search_name).upper()
        search_name_75 = search_name[: int(len(search_name) * 0.75)]

        try:
            elements = self.app.GetCalcRelevantObjects(f"{search_name_75}*.ElmGenstat")
            if not elements:
                print(
                    f"  Stage: {stage.loc_name} | Element not found in grid: {search_name}"
                )
                return stage_repairs

            for element in elements:
                element_name = element.loc_name

                if element_name not in elements_to_repair:
                    print(
                        f"  Stage: {stage.loc_name} | Element not in repair dict: {element_name}"
                    )
                    continue

                if self._is_element_repaired(element_name):
                    print(
                        f"  Stage: {stage.loc_name} | Already repaired: {element_name}"
                    )
                    continue

                power_value = elements_to_repair[element_name]

                if self._set_element_power(element, power_value):
                    self._mark_element_as_repaired(element_name, power_value)
                    stage_repairs[element_name] = power_value
                    print(
                        f"  Stage: {stage.loc_name} | ✓ Modified: {element_name} -> {power_value} MVA"
                    )
                else:
                    print(
                        f"  Stage: {stage.loc_name} | ✗ Failed to modify: {element_name}"
                    )

        except Exception as e:
            print(f"  Stage: {stage.loc_name} | Error: {e}")

        return stage_repairs

    def _find_elements_in_grid(self, element_name: str) -> list:
        try:
            search_name = element_name.replace("PMGD ", "PMGD_")
            units = self.app.GetCalcRelevantObjects(f"{search_name}*.ElmGenstat")
            return units or []
        except Exception as e:
            print(f"Error finding elements: {e}")
            return []

    def _is_element_repaired(self, element_name: str) -> bool:
        return element_name in self.repaired_elements

    def _mark_element_as_repaired(self, element_name: str, power_value: float) -> None:
        self.repaired_elements[element_name] = power_value

    def _set_element_power(self, element, power_value: float) -> bool:
        try:

            prated_actual = element.sgn
            factor = power_value / prated_actual if prated_actual else 1

            site = element.GetParent()
            while site and site.GetClassName() == "ElmSite":
                site = site.GetParent()
                if not site:
                    break

            trf = site.GetContents("*.ElmTr2") if site else []
            trf = trf[0] if trf else None

            line = site.GetContents("*.ElmLne") if site else []
            line = line[0] if line else None

            power_trf = trf.typ_id.strn if trf else None
            trf.typ_id.strn = power_trf * factor

            power_line = line.typ_id.sline
            line.typ_id.sline = power_line * factor

            element.sgn = power_value
            element.Pmax_ucPu = 1

            element.Pmax_uc = element.Pnom
            element.Pmax_ucPu = 1

            return True

        except Exception as e:
            print(f"Error setting power: {e}")
            return False

    def _get_repaired_elements_summary(self) -> dict:
        return self.repaired_elements

    def _reset_repairs(self) -> None:
        self.repaired_elements.clear()


if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app
    app.Show()

    desktop = app.GetDesktop()
    desktop.Close()

    der_repair_operator = DerRepairingOperator(app)
    der_repair_operator.process_all_variations(der_new_capacity)

    desktop.Show()
