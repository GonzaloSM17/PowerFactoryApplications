import common_libs.user_tools as user_tools
import pandas as pd
from typing import Dict, Any
from datetime import datetime
import math


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
        self.templates = self.app.GetProjectFolder("templ").GetContents(
            "IBR_Model_Templates_Updated"
        )[-1]

        # print(self.templates)

    def consult_model(self, cCategory=None):

        template_name = self.models[cCategory]
        self.template = self.templates.GetContents(template_name)[-1]

        if self.template is None:
            return None
        else:
            return self.template


class DispatchExtractor:
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
        self.template_getter = GetTemplate(app=self.app)

    def classify_generation(self):

        for gen in self.generators:
            if any(tag in gen.loc_name for tag in ["BESS_", "PFV_", "PE_"]):
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

                    if any(
                        tag in min_stage.loc_name for tag in ["PE ", "PFV ", "BESS "]
                    ):
                        self.to_modify[gen.loc_name] = (gen, min_stage)

                        # print(gen.loc_name, min_stage.loc_name)

                except Exception as e:
                    print(f"Error processing generator {gen.loc_name}: {e}")

    def modify_model(self):

        self.to_modify_new = {}

        def calculate_SCR(bus=None, activePower=None):

            shc = self.app.GetFromStudyCase("ComShc")
            shc.iopt_mde = 3
            shc.iopt_asc = 0
            shc.iopt_dfr = 0
            shc.ildfinit = 0
            shc.cfac_full = 1
            shc.shcobj = bus
            shc.Execute()

            scl_value = bus.GetAttribute("m:Skss")
            scr = scl_value / activePower

            return scr

        for _, (gen, stage) in self.to_modify.items():

            insite = gen.GetParent()

            line_at = insite.GetContents("LAT*.ElmLne")[-1]
            cub_at = line_at.bus2
            bus_at = cub_at.GetParent()

            power = gen.Pnom * gen.ngnum

            scr = calculate_SCR(bus=bus_at, activePower=power)

            self.to_modify_new[gen.loc_name] = (gen, stage, scr)

        for _, (gen, stage, scr) in self.to_modify_new.items():

            count = 0

            stage.Activate()

            # Insite
            site = gen.GetParent()

            model_insite = site.GetContents("*.ElmComp")[-1]

            ppc_insite = model_insite.GetContents("PPC*.ElmComp")[-1]
            ppc_dsl_insite = ppc_insite.GetContents("*.ElmDsl")[-1]

            parameters_ppc = ppc_dsl_insite.params

            kc = parameters_ppc[11]
            tu, te = parameters_ppc[2], 10

            ki = (
                (1 - (4 * tu / te))
                * (4 * math.sqrt(scr**2 + 1))
                / (te * scr * (scr * kc + 1))
            )
            kp = ki / 100

            ki_rounded, kp_rounded = round(ki, 5), round(kp, 5)
            parameters_ppc[5], parameters_ppc[6] = kp_rounded, ki_rounded

            print(gen.loc_name, ki_rounded, kp_rounded)

            ppc_dsl_insite.params = parameters_ppc
            # count += 1
            # if count == 3:
            #     break


if __name__ == "__main__":

    user = user_tools.User("DefaultUser2024SP7")
    app = user.start_powerfactory()

    desktop = app.GetDesktop()
    desktop.Close()

    tool = DispatchExtractor(app=app)
    tool.classify_generation()
    tool.modify_model()

    desktop.Show()

    # print("Script finished. PowerFactory application remains open.")
