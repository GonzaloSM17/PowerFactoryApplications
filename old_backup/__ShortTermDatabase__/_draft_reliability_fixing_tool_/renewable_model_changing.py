import common_libs.user_tools as user_tools
import pandas as pd
from typing import Dict, Any
from datetime import datetime


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

                        print(gen.loc_name, min_stage.loc_name)

                except Exception as e:
                    print(f"Error processing generator {gen.loc_name}: {e}")

    def modify_model(self):

        # count = 0

        for _, (gen, stage) in self.to_modify.items():

            # stage.Activate()

            # Templates
            template = self.template_getter.consult_model(cCategory=gen.cCategory)
            model_intemplate = template.GetContents("*.ElmComp")[-1]

            gen_intemplate = template.GetContents("*.ElmGenstat")[-1]
            recc_intemplate = model_intemplate.GetContents("REEC*.ElmDsl")[-1]
            regc_intemplate = model_intemplate.GetContents("REGC*.ElmDsl")[-1]
            protections_intemplate = model_intemplate.GetContents("Prot*.ElmDsl")[-1]
            wtg_intemplate = model_intemplate.GetContents("WTGWGO*.ElmDsl")[-1]

            ppc_intemplate = model_intemplate.GetContents("*.ElmComp")[-1]
            ppc_dsl_intemplate = ppc_intemplate.GetContents("*.ElmDsl")[-1]

            # Insite
            site = gen.GetParent()

            model_insite = site.GetContents("*.ElmComp")[-1]
            reec_insite = model_insite.GetContents("REEC*.ElmDsl")[-1]
            regc_insite = model_insite.GetContents("REGC*.ElmDsl")[-1]
            protections_insite = model_insite.GetContents("Prot*.ElmDsl")[-1]
            wtg_insite = model_insite.GetContents("WTGWGO*.ElmDsl")[-1]

            ppc_insite = model_insite.GetContents("PPC*.ElmComp")[-1]
            ppc_dsl_insite = ppc_insite.GetContents("*.ElmDsl")[-1]

            # Creación Elmsys
            print(f"{model_insite.loc_name} modified")

            # model_insite.Move(gen)
            # model_insite.typ_id = model_intemplate.typ_id
            # site.Move(gen)

            # Adaptación
            # reec
            # reec_insite.typ_id = recc_intemplate.typ_id
            # reec_insite.loc_name = recc_intemplate.loc_name
            # reec_insite.params = recc_intemplate.params

            # vdlp = recc_intemplate.GetContents("vdlp.IntMat")[-1].GetAttribute("M")
            # vdlq = recc_intemplate.GetContents("vdlq.IntMat")[-1].GetAttribute("M")

            # try:
            #     reec_insite.GetContents("vdlp.IntMat")[-1].SetAttribute("M", vdlp)
            #     reec_insite.GetContents("vdlq.IntMat")[-1].SetAttribute("M", vdlq)

            # except:
            #     vdlp_matrix = recc_intemplate.GetContents("vdlp.IntMat")[-1]
            #     vdlq_matrix = recc_intemplate.GetContents("vdlq.IntMat")[-1]

            #     reec_insite.AddCopy(vdlp_matrix)
            #     reec_insite.AddCopy(vdlq_matrix)

            #     print(f"add a vdl matrix for {gen.loc_name}")

            # vdlp_n = reec_insite.GetContents("vdlp.IntMat")[-1]
            # vdlq_n = reec_insite.GetContents("vdlq.IntMat")[-1]

            # reec_insite.GetContents("vdlp.IntMat")[-1].SetAttribute("M", vdlp_n)
            # reec_insite.GetContents("vdlq.IntMat")[-1].SetAttribute("M", vdlq_n)

            # regc
            regc_insite.typ_id = regc_intemplate.typ_id
            regc_insite.loc_name = regc_intemplate.loc_name
            regc_insite.params = regc_intemplate.params

            # # protections
            # protections_insite.typ_id = protections_intemplate.typ_id
            # protections_insite.params = protections_intemplate.params

            # # WTG
            # wtg_insite.typ_id = wtg_intemplate.typ_id
            # wtg_insite.params = wtg_intemplate.params

            # # PPC
            # # PPC (Replicar cuando kp, ki), guardar
            # kp = ppc_dsl_insite.params[5]
            # ki = ppc_dsl_insite.params[6]

            # ppc_insite.typ_id = ppc_intemplate.typ_id

            # ppc_dsl_insite.typ_id = ppc_dsl_intemplate.typ_id
            # ppc_dsl_insite.params = ppc_dsl_intemplate.params

            # ppc_dsl_insite.params[5] = kp
            # ppc_dsl_insite.params[6] = ki

            # try:
            #     wtgib_intemplate = model_intemplate.GetContents("WTGIB*.ElmDsl")[-1]
            #     wtgib_insite = model_insite.GetContents("WTGIB*.ElmDsl")[-1]

            #     wtgib_insite.typ_id = wtgib_intemplate.typ_id
            #     wtgib_insite.params = wtgib_intemplate.params

            # except:
            #     pass

            # count += 1
            # if count == 5:
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
