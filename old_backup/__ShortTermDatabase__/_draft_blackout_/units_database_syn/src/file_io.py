# 

import os
import pandas as pd

import my_libs.data_science as ds

# Initialize varibales and classes
File        = ds.File
Dataframe   = ds.Dataframe

class FileIO():
    
    def __init__(self, file_units=None, file_plants=None, file_in_service=None):

        # if file_name is None:
        #     raise ValueError("No file provided. Please provide a valid file.")
        
        # else:   
        #     self.file_name = file_name

        self.file_units      = file_units
        self.file_plants     = file_plants
        self.file_in_service = file_in_service

    def _read_file_units(self):

        _path = self.file_units

        _file_io = File(path=_path)
        _data_io = Dataframe(_file_io)

        _data_io.load_dataframe(sheet_name="1.- Antecedentes Generales", header=[6], usecols="B,D,E")
        _data_io.flatten_columns()
        _data_io.modify_columns()

        _data_io.dataframe.columns = ["nombre_infotecnica", "nombre_propietario", "nombre_central"]

        self.units = _data_io.dataframe

    def _read_file_plants(self):

        _path = self.file_plants

        _file_io = File(path=_path)
        _data_io = Dataframe(_file_io)

        _data_io.load_dataframe(sheet_name="Centrales", header=[6], usecols="A:B")
        _data_io.flatten_columns()
        _data_io.modify_columns()

        _data_io.dataframe.columns = ["id_central", "nombre_central"]  

        _data_io.dataframe["id_central"] = _data_io.dataframe["id_central"].astype(int)       

        self.plants = _data_io.dataframe
    
    def _read_files_scenario_units(self):

        _path = self.file_in_service

        _file_io = File(path=_path)
        _data_io = Dataframe(_file_io)

        _data_io.load_dataframe(sheet_name="Sincronicas", header=[0, 1])
        _data_io.flatten_columns()
        _data_io.dataframe.columns = ["unidad_powerfactory"]

        self.syn_units = _data_io.dataframe

        _data_io.load_dataframe(sheet_name="FACTS", header=[0, 1])
        _data_io.flatten_columns()
        _data_io.dataframe.columns = ["unidad_powerfactory"]

        self.facts_units = _data_io.dataframe

    def _merge_units(self):

        _syn_units   = self.syn_units
        _facts_units   = self.facts_units

        _units    = self.units

        _syn_merge = ds.fuzzy_merge(
            df_left=_syn_units, 
            df_right=_units, 
            left_on="unidad_powerfactory", 
            right_on="nombre_infotecnica",
            threshold= 91
            )

        self.syn_merge = _syn_merge

        _facts_merge = ds.fuzzy_merge(
            df_left=_facts_units, 
            df_right=_units, 
            left_on="unidad_powerfactory", 
            right_on="nombre_infotecnica",
            threshold= 91
            )

        self.facts_merge = _facts_merge

    def _merge_ids(self):

        _plants = self.plants

        _syn_merge   = self.syn_merge
        _facts_merge   = self.facts_merge

        __syn_merge = _syn_merge.merge(
            _plants,
            on="nombre_central",
            how="left"
        )

        self.syn_merge = __syn_merge

        __facts_merge = _facts_merge.merge(
            _plants,
            on="nombre_central",
            how="left"
        )

        self.facts_merge = __facts_merge
  
    def _export_data(self, filename="unidades_infotecnica_blackout_V1.xlsx"):

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                self.syn_merge.to_excel(writer, sheet_name="Sincronicas", index=False)                
                self.facts_merge.to_excel(writer, sheet_name="FACTS", index=False)
            
            print(f"Data has been successfully exported to {filename}")
        
        except Exception as e:
            print(f"An error occurred while exporting data: {e}")   


    def run_util(self):

        self._read_file_units()
        self._read_files_scenario_units()
        self._read_file_plants()

        self._merge_units()
        self._merge_ids()

        self._export_data()

# Stand-alone execution
if __name__ == "__main__":

    file_units      = "reporte_unidades-generadoras.xlsx"
    file_plants     = "reporte_centrales.xlsx"
    file_in_service = "unidades_en_servicio_blackout.xlsx"

    util = FileIO(file_units=file_units,
                     file_plants=file_plants,
                     file_in_service=file_in_service)
    util.run_util()
