# 

import os
import pandas as pd

import my_libs.data_science as ds

import file_io as file_io

FileIO = file_io.FileIO

class DataHandler():
    
    def __init__(self, file_name=None):

        file_io = FileIO(file_name=file_name)
        file_io.run_util()

        self.data = file_io.file_io

    def _dividing_data(self):

        pass

    def _export_data(self, filename="times_data.xlsx"):

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                self.data_wi_.to_excel(writer, sheet_name="Tiempos", index=False)                
                self.data_woi.to_excel(writer, sheet_name="Sin Información", index=False)
            
            print(f"Data has been successfully exported to {filename}")
        
        except Exception as e:
            print(f"An error occurred while exporting data: {e}")

    def run_handler(self):

        pass

# Stand-alone execution
if __name__ == "__main__":

    file_name = "Listado de Centrales en Isla Centro Sur.xlsx"

    handler = DataHandler(file_name=file_name)
    handler.run_handler()