# 

import os
import pandas as pd

import my_libs.data_science as ds

# Initialize varibales and classes
File        = ds.File
Dataframe   = ds.Dataframe

class FileIO():
    
    def __init__(self, file_name=None):

        if file_name is None:
            raise ValueError("No file provided. Please provide a valid file.")
        
        else:   
            self.file_name = file_name

    def _read_file(self):

        _path = self.file_name

        _file_io = File(path=_path)
        _file_io = Dataframe(_file_io)

        _file_io.load_dataframe(sheet_name="EDAC EAF 089-2025 OK", header=[9], usecols="D:F,M:P,W,AE")
        _file_io.flatten_columns()
        _file_io.modify_columns()

        _df         = _file_io.dataframe
        _df_columns = ["coordinado", "subestacion", "tipo_operacion","escalon", "frecuencia_escalon", "gradiente_escalon", "alimentadores", "potencia_declarada", "monto_desconectado"]
        _df.columns = _df_columns

        self.file_io = _df

    def run_util(self):

        self._read_file()


# Stand-alone execution
if __name__ == "__main__":

    file_name = "Análisis EDAC_FALLA 25-02-2025_version 2.xlsx"

    in_file = FileIO(file_name=file_name)
    in_file.run_util()
