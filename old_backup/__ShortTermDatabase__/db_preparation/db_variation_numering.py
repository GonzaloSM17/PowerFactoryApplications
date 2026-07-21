import re


class VariationEnumerating:

    def __init__(self, app=None) -> None:
        if not app:
            print("Error: PowerFactory application instance is required.")
            return

        self.app = app
        self.project = self.app.GetActiveProject()
        self.set_select = None
        self.variations = []

    def load_set_select(self) -> bool:
        try:
            database = self.project.GetContents("__Database_ShortTerm*")
            if not database:
                return False

            var_folder = database[0].GetContents("__Variations_Enumerating*")
            if not var_folder:
                return False

            set_select = var_folder[0].GetContents("*.SetSelect")
            if set_select:
                self.set_select = set_select[0]
                return True
            return False
        except Exception as e:
            print(f"Error loading SetSelect: {e}")
            return False

    def get_variations(self) -> list:
        if not self.set_select:
            return []
        try:
            int_folders = self.set_select.GetAll("IntFolder") or []
            for folder in int_folders:
                int_schemes = folder.GetContents("*.IntScheme") or []
                self.variations.extend(int_schemes)
            return self.variations
        except Exception as e:
            print(f"Error getting variations: {e}")
            return []

    def _get_from_act(self, variation) -> float:
        try:
            return float(variation.GetAttribute("tFromAct"))
        except:
            return float("inf")

    def sort_variations_by_time(self, variations: list) -> list:
        return sorted(variations, key=self._get_from_act)

    def _is_numeric_prefix(self, name: str) -> bool:
        match = re.match(r"^(\d+)", name)
        return match is not None

    def _has_double_x(self, name: str) -> bool:
        return "xx" in name.lower()

    def _extract_numeric_prefix(self, name: str) -> str:
        match = re.match(r"^(\d+)", name)
        return match.group(1) if match else None

    def _replace_numeric_prefix(self, name: str, new_number: str) -> str:
        return re.sub(r"^\d+", new_number, name)

    def _replace_double_x(self, name: str, new_number: str) -> str:
        return re.sub(r"xx", new_number, name, flags=re.IGNORECASE)

    def generate_number_string(self, index: int) -> str:
        return f"{index + 1:02d}"

    def update_variation_name(self, variation, number_str: str) -> bool:
        try:
            current_name = variation.loc_name

            if self._is_numeric_prefix(current_name):
                new_name = self._replace_numeric_prefix(current_name, number_str)
            elif self._has_double_x(current_name):
                new_name = self._replace_double_x(current_name, number_str)
            else:
                new_name = f"{number_str} {current_name}"

            variation.loc_name = new_name
            return True
        except Exception as e:
            print(f"Error updating variation name: {e}")
            return False

    def enumerate_variations(self) -> dict:
        if not self.load_set_select():
            print("Error: Could not load SetSelect.")
            return {}

        if not self.get_variations():
            print("No variations found.")
            return {}

        int_folders = self.set_select.GetAll("IntFolder") or []
        results = {}

        for folder in int_folders:
            int_schemes = folder.GetContents("*.IntScheme") or []
            sorted_variations = self.sort_variations_by_time(int_schemes)

            for index, variation in enumerate(sorted_variations):
                number_str = self.generate_number_string(index)
                old_name = variation.loc_name

                if self.update_variation_name(variation, number_str):
                    results[old_name] = variation.loc_name
                else:
                    results[old_name] = f"Error updating {old_name}"

        return results

    def get_enumeration_summary(self) -> dict:
        if not self.set_select:
            return {}

        variations = self.get_variations()
        sorted_variations = self.sort_variations_by_time(variations)

        summary = {}
        for index, var in enumerate(sorted_variations):
            summary[f"{index + 1:02d}"] = {
                "name": var.loc_name,
                "tFromAct": var.GetAttribute("tFromAct"),
            }

        return summary


if __name__ == "__main__":

    import _powerfactory_app_

    app = _powerfactory_app_.app
    app.Show()

    variation_enumerator = VariationEnumerating(app)
    variation_enumerator.enumerate_variations()
