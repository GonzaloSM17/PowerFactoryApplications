import common_libs.user_tools as user_tools
import pandas as pd
from typing import Dict, Any


class ClassChanger:
    """
    Extracts dispatch data for all generators in a PowerFactory project.
    """

    def __init__(self, app=None):

        self.app = app
        if not self.app:
            raise ValueError("PowerFactory application object (app) must be provided.")

        # Get all types of generators: synchronous (ElmSym), asynchronous (ElmAsm), and static (ElmGenstat)
        nosyn = self.app.GetCalcRelevantObjects("ElmGenstat")

        self.generators = nosyn
        self.to_modify = {}

    def classify_generation(self):

        for gen in self.generators:
            if any(tag in gen.loc_name for tag in ["PFV_"]):
                try:
                    stages = self.app.GetTouchingExpansionStages(gen)
                    if stages:
                        min_stage_date = None
                        min_stage = None
                        for stage in stages:
                            stage_date_timestamp = stage.GetAttribute("tAcTime")

                            if (
                                min_stage_date is None
                                or stage_date_timestamp < min_stage_date
                            ):
                                min_stage_date = stage_date_timestamp
                                min_stage = stage

                        if min_stage:
                            # print(
                            #     f"Generator: {gen.loc_name}, Stage : {min_stage.loc_name}"
                            # )
                            pass

                    if any(tag in min_stage.loc_name for tag in ["PFV "]):
                        self.to_modify[gen.loc_name] = (gen, min_stage)

                except Exception as e:
                    print(f"Error processing generator {gen.loc_name}: {e}")

    def modify_model(self):

        count = 0

        for _, (gen, stage) in self.to_modify.items():

            # stage.Activate()

            gen_class = gen.GetAttribute("className")
            print(gen_class)
            count += 1
            if count == 3:
                break


if __name__ == "__main__":

    user = user_tools.User("DefaultUser2024SP7")
    app = user.start_powerfactory()

    desktop = app.GetDesktop()
    # desktop.Close()

    tool = ClassChanger(app=app)
    tool.classify_generation()
    tool.modify_model()

    # desktop.Show()

    # print("Script finished. PowerFactory application remains open.")
