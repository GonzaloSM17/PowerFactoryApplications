import time
import logging

logger = logging.getLogger(__name__)


class TapGroupManager:

    def __init__(self, app=None):

        if app is None:
            logger.error("No PowerFactory application instance provided.")
            return

        else:
            self.app = app

        self.project = self.app.GetActiveProject()

        self._get_or_create_tap_group_folder()
        self._get_relevant_units()
        self._create_set_selects()

    def _get_or_create_tap_group_folder(self):

        tool_folder = self.project.GetContents("__Database_ShortTerm*.IntFolder")
        if not tool_folder:
            tool_folder = self.project.CreateObject(
                "IntFolder", "__Database_ShortTerm__"
            )[-1]
        else:
            tool_folder = tool_folder[-1]

        tap_group_folder = tool_folder.GetContents("__Tap_Grouping*.IntFolder")

        if not tap_group_folder:
            tap_group_folder = tool_folder.CreateObject("IntFolder", "__Tap_Grouping")
        else:
            tap_group_folder[-1].Delete()
            tap_group_folder = tool_folder.CreateObject("IntFolder", "__Tap_Grouping")
            self.tap_group_folder = tap_group_folder

    def _get_relevant_units(self):

        nosyn_units = self.app.GetCalcRelevantObjects("*.ElmGenstat")
        self.relevant_units = [
            unit
            for unit in nosyn_units
            if unit.cCategory
            in ["Photovoltaic", "Wind", "Storage", "Renewable generation"]
            and any(
                prefix in unit.loc_name
                for prefix in ["PFV_", "PE_", "BESS_", "PMGD_", "_GEN"]
            )
        ]

    def _create_set_selects(self):

        def _find_site(unit):

            parent = unit
            while parent and parent.GetClassName() != "ElmSite":
                parent = parent.GetParent()
            # If no site is found, just print a warning and continue
            if not parent:
                logger.warning(
                    "Site not found for unit %s. Continuing with other groupings.",
                    unit.loc_name,
                )
                return None
            return parent

        def _add_objects_to_group(unit, site):
            grouping = [unit]
            if site is None:
                return grouping

            try:
                if "_GEN" in unit.loc_name:
                    unit_loc_name = unit.loc_name.replace("_GEN", "")

                    transformer = site.GetContents(f"{unit_loc_name}_TR.ElmTr2")[-1]
                    lv_bus = site.GetContents(f"{unit_loc_name}_BT.ElmTerm")[-1]
                    grouping.extend([transformer, lv_bus])

                else:
                    transformer = site.GetContents(f"TR_{unit.loc_name}*.ElmTr2")[-1]
                    lv_bus = site.GetContents(f"BT_{unit.loc_name}*.ElmTerm")[-1]
                    grouping.extend([transformer, lv_bus])

            except IndexError:

                raise ValueError(
                    f"Missing objects (transformer/LV bus) for unit {unit.loc_name}"
                )

            return grouping

        def _create_set_select(unit, grouping):

            set_select_name = f"set{unit.loc_name}"
            set_select = self.tap_group_folder.GetContents(
                f"{set_select_name}.SetSelect"
            )
            if not set_select:
                set_select = self.tap_group_folder.CreateObject(
                    "SetSelect", set_select_name
                )
            else:
                set_select = set_select[-1]
            set_select.AddRef(grouping)

        for unit in self.relevant_units:
            site = _find_site(unit)
            grouping = _add_objects_to_group(unit, site)

            _create_set_select(unit, grouping)


# Standalone execution
if __name__ == "__main__":

    import _powerfactory_app_

    # Running time...
    start_time = time.time()

    taps_manager = TapGroupManager(app=_powerfactory_app_.app)

    # End timing
    end_time = time.time()
    minutes, seconds = divmod(end_time - start_time, 60)
    logger.info(
        "Time taken to process units: %d minutes and %.2f seconds",
        int(minutes),
        seconds,
    )
