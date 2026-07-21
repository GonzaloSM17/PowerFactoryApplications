# models_activation.py

import time
import math

# Custom libraries
import common_libs.user_tools as user_tools

# ... Use only if you need change paramaters of models in variations
class ModelFixer:

    def __init__(self, app):

        self.app = app

    def _variations_extractions(self):

        _variations_folders = self.app.GetProjectFolder("scheme").GetContents("*.IntFolder")
        
        self._variations_generation = {}

        for _variation_folder in _variations_folders:

            if "Generación" in _variation_folder.loc_name:
                for _variation in _variation_folder.GetContents("*.IntScheme"):
                    self._variations_generation[_variation.loc_name] = _variation
            
            if "Working" in _variation_folder.loc_name:
                for _folders in _variation_folder.GetContents("Modelos_Din_I*.IntFolder"):
                    for _variations in _folders.GetContents("*.IntScheme"):
                            self._variations_generation[_variations.loc_name] = _variations

                for _folders in _variation_folder.GetContents("Modelos_Din_R*.IntFolder"):
                    for _variations in _folders.GetContents("*.IntScheme"):
                            self._variations_generation[_variations.loc_name] = _variations
            
        print(self._variations_generation)

    def _activate_variations(self):

        _factor = 1 / math.sqrt(1**2 + 0.33**2)

        for _variation in self._variations_generation.values():
            _variation.Activate()

            
            # ps = {}
            for _expansion_stage in _variation.GetContents("*.IntSstage"):

                # _repcs = []

                _expansion_stage.Activate()
                # _ppc_composite = self.app.GetCalcRelevantObjects("PFV_*.ElmComp")
                generator_1 = self.app.GetCalcRelevantObjects("PFV_*.ElmGenstat")
                generator_2 = self.app.GetCalcRelevantObjects("PE_*.ElmGenstat")
                generator_3 = self.app.GetCalcRelevantObjects("BESS_*.ElmGenstat")

                generators = generator_1 + generator_2 + generator_3

                # generator_1 = self.app.GetCalcRelevantObjects("PFV_*.ElmGenstat")


                for _generator in generators:
                    
                    power_saved = _generator.sgn

                    p_nom = _generator.P_max
                    s_nom = p_nom/_factor

                    _generator.sgn = s_nom
                    _generator.cosn = _factor

                    # Set
                    _generator.pmaxratf = 1

                    if "BESS" in _generator.loc_name:
                        _generator.Pmax_uc = p_nom
                        _generator.Pmin_uc = -p_nom
                    
                    else:
                        _generator.Pmax_uc = p_nom
                        _generator.Pmin_uc = 0

                    
                    _model  = _generator.c_pmod
                    # print(_model.loc_name)
                    _repc   = _model.GetContents("*.ElmComp")[-1]


                    # print(_repc.loc_name)

                    power_measurement = _repc.GetContents("*.StaPqmea")
                    current_measurement = _repc.GetContents("*.StaImea")[-1]

                    for power in power_measurement:
                        power.Snom = s_nom
                    
                    current_save = current_measurement.Inom
                    current_measurement.Inom = current_save * s_nom / power_saved                 

                # for generator in generator_1:
                    # generator.iAstabint = 1
                    # print(generator.loc_name)
                
                # for generator in generator_2:
                    # generator.iAstabint = 1
                
                # for generator in generator_3:
                    # generator.iAstabint = 1
                
                # ps_composite = self.app.GetCalcRelevantObjects("P/S_*.ElmComp")
                                
                # for _ps in ps_composite:

                #     try:

                #         if _ps in ps or "Negrete" in _ps.loc_name:
                #             pass
                        
                #         else:                        
                #             _reec = _ps.GetContents("REEC*.ElmDsl")[-1]

                #             _params = _reec.params
                #             # _params[] = 0
                #             _params[29] = 1.5
                #             # _params[34] = 0.9

                            
                #             _reec.params = _params
                #             ps[_ps.loc_name] = _ps.loc_name

                #             print(_ps.loc_name)

                    # for elem in elems:
                    #     if "REGC" in elem.loc_name:
                    #         elem.Reset()

                    # _regcs = ps.GetContents("REGC*.ElmDsl")

                    # for _regc in _regcs:                   

                    #     _regc.Delete()

                    # # _regc.Reset()
                    # _table2 = _reec.table2
                    # print(_table2)
                        # _regc.Reset()
                    # except:
                    #     print(f"Couldn't change the params in {_ps.loc_name}")
                    

                # for _ppc in _ppc_composites:

                #     # _reinsert = False                
                    
                #     power_measurements = _ppc.GetContents("*.StaPqmea")
                #     current_measurement = _ppc.GetContents("*.StaImea")[-1]

                #     for power_measurement in power_measurements:
                #         power_measurement.i_mode=2

                #         if "Branch 1" in power_measurement.loc_name:
                #             power_measurement.i_orient = 1
                #         else:
                #             power_measurement.i_orient = 0

                #         # _reinsert = True
                    
                #     current_measurement.i_mode=2

                    # _reinsert = True

                # for _ppc in _ppc_composites:
                #     _repc   = _ppc.GetContents("*.ElmDsl")[-1]
                    
                #     _repc_params = _repc.params

                #     _reinsert = False
                    
                #     if _repc.params[12] != 0.02:
                #         _repc_params[12] = 0.02
                        
                #         _reinsert = True
                    
                #     if _repc.params[50] != 999:
                #         _repc_params[50] = 999

                #         _reinsert = True
                    
                #     if _reinsert:
                #         _repc.params = _repc_params

                #     print(_repc.params[12], _repc.params[50])

            # _variation.Deactivate()
    
    def _pmgds_mod(self):

        _pmgds = self.app.GetCalcRelevantObjects("PMGD*.ElmGenstat") 
        
        for _pmgd in _pmgds:
            
            _model = _pmgd.c_pmod
            control_pg = _model.GetContents("Control*.ElmDsl")[-1]

            iq_ = control_pg.GetContents("iq_u*.IntMat")[-1]
            row_ = iq_.GetAttribute("M:3")

            row_[1] = -1

            iq_.SetAttribute("M:3", row_)
 
    def run_module(self, **kwargs):

        self._pmgds_mod()        
        # self._variations_extractions()
        # self._activate_variations()
        

class DSLFixer():

    def __init__(self, app):

        self.app = app
        
        self.exclude_list = [
        "ALMEYDA",
        "ATACAMA SOLAR II",
        "MESETA DE LOS ANDES",
        "PAMPA TIGRE",
        "BOLERO",
        "RENAICO I",
        "BUENOS AIRES",
        "COYA",

        "RENAICO II",
        "CABAÑA",
        "LA ESPERANZA",
        "CUEL", 
        "PUNTA SIERRA",

        "SAN GABRIEL",
        "TOLPAN SUR",
        "MESAMAVIDA",
        "ALENA",

        "COCHRANE",
        "ARICA",
        "ANGAMOS",
        ]


    def _dsl_extractions(self):

        self.dsl_ibr = {}

        _dsls = self.app.GetCalcRelevantObjects("*.ElmDsl")

        for _dsl in _dsls:
            if (
                any(name in _dsl.fold_id.loc_name for name in [" PFV ", " PE ", " BESS "]) 
                and not any(name in _dsl.fold_id.loc_name for name in self.exclude_list)
                ):

                # print(_dsl.fold_id.loc_name)

                self.dsl_ibr[f"{_dsl.loc_name}-{_dsl.fold_id.loc_name}"] = _dsl

                


    def _set_no_a_stable(self):
        
        for _, _dsl in self.dsl_ibr.items():

            if "EDAG" in _dsl.loc_name:
                pass
            else:
                _dsl.iAstabint = 0      
    
    def run_module(self, **kwargs):
        
        self._dsl_extractions()
        self._set_no_a_stable()
            
# Stand-alone execution
if __name__ == "__main__":

    user = user_tools.User(user_name="Gonzalo")
    app = user.start_powerfactory()

    # Running time...
    start_time = time.time()

    # desktop = app.GetDesktop()
    # desktop.Close()

# ... Emergency
    # fixer = ModelFixer(app=app)
    # fixer.run_module()

    dsl_fixer = DSLFixer(app=app)
    dsl_fixer.run_module()

# ...

    # desktop.Show()
    print(f"Time taken to process units: {int((time.time() - start_time) // 60)} minutes and {(time.time() - start_time) % 60:.2f} seconds")