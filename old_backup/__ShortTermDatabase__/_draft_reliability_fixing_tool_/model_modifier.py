# t99.../...draft

import common_libs.user_tools as user_tools
import pandas as pd

from typing import Dict, Tuple

User = user_tools.User


# ///
class GeneratorExplorer:
    """
    Explores PowerFactory generator models to identify and report specific types.
    """

    def __init__(self, app=None):
        self.app = app
        # Assuming 'app' is a PowerFactory application object
        self.nosyn = self.app.GetCalcRelevantObjects("*.ElmGenstat")
        self.gen_filtered: Dict[str, Tuple] = {}
        self.to_report: Dict[str, Tuple] = {}

    def filter_old_models(self) -> Tuple[Dict[str, Tuple], Dict[str, Tuple]]:
        """
        Filters generator models based on naming conventions and parent class.
        Populates self.gen_filtered and self.to_report.
        """
        count = 0
        for element in self.nosyn:

            stage = self.app.GetTouchingExpansionStages(element)

            if stage is not None:
                if element.GetParent().GetClassName() == "ElmSite":
                    count += 1
                    # Get the last expansion stage touching the element
                    stages = self.app.GetTouchingExpansionStages(element)
                    stage = stages[-1] if stages else None

                    self.gen_filtered[element.loc_name] = (
                        element,
                        element.GetParent(),
                        stage,
                    )

                    self.to_report[element.loc_name] = (
                        element.loc_name,
                        element.GetParent().loc_name,
                        stage.loc_name if stage else "N/A",
                    )

                    print(element.loc_name)

        print(f"Found {count} relevant generators.")
        return self.gen_filtered, self.to_report

    def export_report(self, output_path: str = "report.xlsx") -> None:
        """
        Exports the filtered generator data to an Excel report.
        """
        if self.to_report:
            df = pd.DataFrame.from_dict(
                self.to_report,
                orient="index",
                columns=["Element Name", "Parent Name", "Stage Name"],
            )
            df.to_excel(output_path, index=False)
            print(f"Report exported to {output_path}")
        else:
            print("No data to report.")


class GetTemplate:
    """
    Placeholder class, currently unused.
    """

    def __init__(self, app=None):

        self.models = {
            "Photovoltaic": "WECC_PV",
            "Wind": "WECC_WT_Type4B",
            "Storage": "WECC_BESS_GridFollowing",
        }

        self.app = app
        self.templates = self.app.self.app.GetProjectFolder("templ").GetContents(
            "00-IBR_Model*"
        )

    def consult_model(self, cCategory=None):
        self.template = self.templates.GetContents("{cCategory}")

        if self.template is None:
            return None
        else:
            return self.template


class GeneratorModifier(GeneratorExplorer):
    """
    Extends GeneratorExplorer to provide modification capabilities.
    """

    def __init__(self, app=None):
        super().__init__(app=app)
        # Call filter_old_models to populate gen_filtered and to_report
        self.filter_old_models()

    def explore_generator(self) -> None:
        """
        Example method to iterate and print filtered generators.
        """

        # ///
        def get_template(generator=None):
            template = GetTemplate(app=app).consult_model(cCategory=generator.cCategory)
            return template

        # ///

        if not self.gen_filtered:
            print("No generators filtered yet. Run filter_old_models first.")
            return

        for gen_name, (element, parent, stage) in self.gen_filtered.items():

            # stage.Active()
            try:
                # Elemnts
                bus_hv = parent.GetContents("*POI.ElmTerm")[-1]
                transformer_hv = parent.GetContents("*TR.ElmTr2")[-1]
                colector = parent.GetContents("*CE.ElmLne")[-1]
                generator = parent.GetContents("*.ElmGenstat")[-1]

                model = parent.GetContents("*.ElmComp")[-1]

                # Parameters
                hv = bus_hv.uknom
                power = generator.sgn * generator.ngnum

                # Cubiculos
                cub_hv = transformer_hv.bushv_bar
                cub_mv = colector.bus2_bar

                # print(model)

                if "_Modelo" in model.loc_name:
                    print(model.loc_name)
                    # model.Delete()

            except:
                print(f"generador: {gen_name} not possible")


if __name__ == "__main__":

    user = user_tools.User("DefaultUser")
    app = user.start_powerfactory()

    # It's generally better to keep the desktop open for interactive use
    desktop = app.GetDesktop()
    desktop.Close()  # Commented out to keep PowerFactory GUI open

    tool = GeneratorModifier(app=app)
    # tool.export_report(output_path="report.xlsx")
    tool.explore_generator()

    desktop.Show()  # Commented out as desktop is not closed initially
    print("Script finished. PowerFactory application remains open.")
