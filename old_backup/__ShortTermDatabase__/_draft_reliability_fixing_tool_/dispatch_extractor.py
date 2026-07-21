import common_libs.user_tools as user_tools
import pandas as pd
from typing import Dict, Any


class DispatchExtractor:
    """
    Extracts dispatch data for all generators in a PowerFactory project.
    """

    def __init__(self, app=None):
        self.app = app
        if not self.app:
            raise ValueError("PowerFactory application object (app) must be provided.")
        # Get all types of generators: synchronous (ElmSym), asynchronous (ElmAsm), and static (ElmGenstat)
        nosyn = self.app.GetCalcRelevantObjects("ElmSym")
        syn = self.app.GetCalcRelevantObjects("ElmAsm")
        asyn = self.app.GetCalcRelevantObjects("ElmGenstat")

        self.generators = nosyn + syn + asyn
        self.dispatch_data: Dict[str, Dict[str, Any]] = {}

    def extract_dispatch(self) -> Dict[str, Dict[str, Any]]:
        """
        Iterates through all generators and extracts their active power dispatch.
        Assumes the simulation has been run and results are available.
        """
        if not self.generators:
            print("No generators found in the project.")
            return {}

        print(f"Found {len(self.generators)} generators. Extracting dispatch data...")

        for gen in self.generators:
            try:
                # pgini + ngnum + outserv (all of it is needed to get de real dispatch)
                # This assumes a calculation has been performed and results are available.
                # Depending on the PowerFactory version and project setup,
                # you might need to access specific result variables (e.g., from a ComRes object).
                # Calculate dispatch as pgini * ngnum
                pgini_value = gen.GetAttribute("pgini")
                ngnum_value = gen.GetAttribute("ngnum")
                # Ensure values are not None before multiplication
                dispatch_value = (
                    (pgini_value * ngnum_value)
                    if (pgini_value is not None and ngnum_value is not None)
                    else 0.0
                )

                # Get in-service status (0 for in service, 1 for out of service)
                in_service_status = gen.GetAttribute("outserv") == 0

                self.dispatch_data[gen.loc_name] = {
                    "Element Name": gen.loc_name,
                    "Parent Name": (
                        gen.GetParent().loc_name if gen.GetParent() else "N/A"
                    ),
                    "Active Power (MW)": dispatch_value,
                    "In Service": in_service_status,
                }
            except Exception as e:
                print(f"Could not extract dispatch for {gen.loc_name}: {e}")
                self.dispatch_data[gen.loc_name] = {
                    "Element Name": gen.loc_name,
                    "Parent Name": (
                        gen.GetParent().loc_name if gen.GetParent() else "N/A"
                    ),
                    "Active Power (MW)": "Error",
                    "In Service": "Error",
                }
        print("Dispatch data extraction complete.")
        return self.dispatch_data

    def export_to_excel(
        self, output_path: str = "generator_dispatch_report.xlsx"
    ) -> None:
        """
        Exports the extracted dispatch data to an Excel file.
        """
        if not self.dispatch_data:
            print("No dispatch data to export. Run extract_dispatch first.")
            return

        df = pd.DataFrame.from_dict(self.dispatch_data, orient="index")
        df.to_excel(output_path, index=False)
        print(f"Dispatch report exported to {output_path}")


if __name__ == "__main__":

    user = user_tools.User("DefaultUser")
    app = user.start_powerfactory()

    # Ensure a project is active and a calculation (e.g., Load Flow) has been run
    # for dispatch values to be available.
    # Example:
    # project = app.GetActiveProject()
    # if project:
    #     load_flow = app.Get  # Get the load flow command object
    #     load_flow.Execute() # Execute load flow

    extractor = DispatchExtractor(app=app)

    desktop = app.GetDesktop()
    desktop.Close()

    extractor.extract_dispatch()
    extractor.export_to_excel(output_path="dispatch_night_report.xlsx")

    desktop.Show()

    print("Script finished. PowerFactory application remains open.")
