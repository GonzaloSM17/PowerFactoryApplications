import common_libs.user_tools as user_tools
import pandas as pd
from typing import Dict, Any
from datetime import datetime


class DispatchExtractor:
    """
    Extracts dispatch data for all generators in a PowerFactory project.
    """

    def __init__(self, app=None):

        self.app = app
        if not self.app:
            raise ValueError("PowerFactory application object (app) must be provided.")

        # Get all types of generators: synchronous (ElmSym), asynchronous (ElmAsm), and static (ElmGenstat)
        asyn = self.app.GetCalcRelevantObjects("ElmAsm")
        nosyn = self.app.GetCalcRelevantObjects("ElmGenstat")

        self.generators = nosyn + asyn
        self.extracted_data = []  # Initialize a list to store extracted data

    def extract_generation(self) -> list[Dict[str, Any]]:
        """
        Iterates through all generators and extracts their active power dispatch.
        Assumes the simulation has been run and results are available.
        """
        if not self.generators:
            print("No generators found in the project.")
            return []

        print(f"Found {len(self.generators)} generators. Extracting dispatch data...")

        for gen in self.generators:

            if "PMGD" not in gen.loc_name:
                try:
                    stages = self.app.GetTouchingExpansionStages(gen)
                    if stages:  # Check if stages is not empty
                        min_date_stage = None
                        min_date = None
                        for stage in stages:
                            stage_date = stage.GetAttribute(
                                "tAcTime"
                            )  # 'tAcTime' is an integer, as clarified by the user
                            if min_date_stage is None or stage_date < min_date:
                                min_date = stage_date
                                min_date_stage = stage

                        # Data needed
                        name_gen = gen.loc_name
                        power_gen = gen.Pnom * gen.ngnum

                        if gen.c_pmod:
                            model = gen.c_pmod.loc_name
                        else:
                            model = None

                        variation = min_date_stage.GetParent()
                        variation_name = variation.loc_name if variation else None

                        # Find the parent ElmNet (grid class)
                        current_obj = gen
                        grid_name = None
                        while current_obj:
                            if current_obj.GetClassName() == "ElmNet":
                                grid_name = current_obj.loc_name
                                break
                            current_obj = current_obj.GetParent()

                        site = gen.GetParent()
                        if (
                            site.GetClassName() == "ElmSite"
                        ):  # Corrected GetClassName to be a call
                            try:
                                bus = site.GetContents("*_LAT.ElmLne")[-1]
                                cub = bus.bus2

                                bus_at = cub.GetParent()

                                while bus_at.GetClassName() != "ElmSubstat":
                                    bus_at = bus_at.GetParent()

                                bus_at = cub.GetParent().loc_name
                            except (
                                Exception
                            ):  # Catch specific exception or general for robustness
                                bus_at = None
                        else:
                            bus_at = None

                        self.extracted_data.append(
                            {
                                "Generator Name": name_gen,
                                "Generator Power": power_gen,
                                "Model": model,
                                "Min Stage Name": min_date_stage.loc_name,
                                "Min Stage Date (tAcTime)": min_date,
                                "Min Stage Date (Formatted)": datetime.fromtimestamp(
                                    min_date
                                ).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),  # Convert Unix timestamp to human-readable date
                                "Variation Parent Name": variation_name,
                                "Grid Name": grid_name,  # Storing the name, not the object
                                "Bus": bus_at,
                            }
                        )
                except Exception as e:
                    print(f"Error processing generator {gen.loc_name}: {e}")
                    pass
        return self.extracted_data

    def export_to_excel(self, output_path: str = "report_renewables.xlsx") -> None:
        if self.extracted_data:
            df = pd.DataFrame(self.extracted_data)
            df.to_excel(output_path, index=False)
            print(f"Extracted data exported to {output_path}")
        else:
            print("No data to export.")


if __name__ == "__main__":

    user = user_tools.User("DefaultUser2024SP7")
    app = user.start_powerfactory()

    desktop = app.GetDesktop()
    desktop.Close()

    extractor = DispatchExtractor(app=app)
    extracted_info = extractor.extract_generation()
    extractor.export_to_excel(output_path="report_renewables.xlsx")

    desktop.Show()

    print("Script finished. PowerFactory application remains open.")
