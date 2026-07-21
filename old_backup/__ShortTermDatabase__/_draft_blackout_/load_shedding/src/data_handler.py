# 

import os
import pandas as pd
from unidecode import unidecode

# %load_ext autoreload
# %autoreload 2

import my_libs.data_science as ds

import file_io as file_io
FileIO = file_io.FileIO


NORTHERN_SUBSTATIONS = [
    "Diego de Almagro", "Cardones", "Alto Hospicio", "La Portada", "Sur", "Chinchorro", "Cerro Dragón", "Paipote","Chuquicamata", "Gaby", "Pukará", "Aguas Blancas",
    "MMH", "Radomiro Tomic", "Collahuasi", "Calama", "Esmeralda", "Cóndores", "Parinacota", "Lomas Bayas", "Cerro Colorado", "Quebrada Blanca", "Tap Off E.C. Algorta",
    "Zaldívar", "Alto Norte", "Central Diesel Enaex", "Mantos de la Luna", "La Cascada HMC (Sagasca)", "Antucoya", "El Tesoro", "Esperanza", "Coloso", "Escondida",
    "Laguna Seca", "OGP1", "Planta Óxidos", "Sulfuros", "Tap Off Estación de bombeo N°2", "Tap Off Estación de bombeo N°3", "Tap Off Estación de bombeo N°4", "Mantos Blancos",
    "Tap Off Palestina", "Mejillones", "Spence", "Molycop", "Sierra Gorda", "El Abra", "GNL Mejillones", "El Loa", "Tap Off Nueva Victoria", "Tap Off Oeste"
]

class DataHandler():
    
    def __init__(self, file_name=None):

        file_io = FileIO(file_name=file_name)
        file_io.run_util()
        self.data = file_io.file_io
        self.data_north = None

    def _separate_northern_substations(self):

        _data = self.data.copy()
        
        _data_north = pd.DataFrame()

        for substation in NORTHERN_SUBSTATIONS:
            
            condition = _data["subestacion"] == substation   
            _data_filtered = _data[condition].reset_index(drop=True)
            _data_north = pd.concat([_data_north, _data_filtered], axis=0, ignore_index=True)

            _data = _data[~condition].reset_index(drop=True)

        self.data_north = _data_north.reset_index(drop=True)
        self.data       = _data.reset_index(drop=True)

    def _filtering_data(self):

        _data = self.data.copy()

        # Condition filters
        _condition_aec   = _data["tipo_operacion"] == "EDAC_CE"
        _condition_uf    = _data["tipo_operacion"] == "EDAC_BF"
        _condition_fa    = _data["tipo_operacion"] == "FA"
        _condition_other = ~(_condition_aec | _condition_uf | _condition_fa)

        # Filters
        self.data_aec   = _data[_condition_aec].reset_index(drop=True)
        self.data_uf    = _data[_condition_uf].reset_index(drop=True)
        self.data_fa    = _data[_condition_fa].reset_index(drop=True)
        self.data_other = _data[_condition_other].reset_index(drop=True)
    
    def _eac_by_step(self):

        _data_aec = self.data_aec.copy()
        
        # Attempt to convert "frecuencia" to numeric, keeping original strings for non-numeric values
        _data_aec["frecuencia_escalon"] = (
            _data_aec["frecuencia_escalon"]
            .str.replace("Hz", "", regex=False)  # Remove "Hz"
            .str.strip()  # Remove leading and trailing spaces
        )
        _data_aec["frecuencia_escalon"] = pd.to_numeric(_data_aec["frecuencia_escalon"], errors="coerce").fillna(_data_aec["frecuencia_escalon"])

        # Convert "monto_desconectado" to numeric, dropping non-convertible rows
        _data_aec["monto_desconectado"] = pd.to_numeric(_data_aec["monto_desconectado"], errors="coerce")
        _data_aec = _data_aec.dropna(subset=["monto_desconectado"])

        # Group by "escalon" and sum "monto_desconectado"
        _sum_data_aec = _data_aec.groupby("escalon")["monto_desconectado"].sum().reset_index()

        # Store the summarized data as an instance attribute
        self.sum_data_aec = _sum_data_aec
    
    def _uf_by_step(self):
        # Store original frequency values before attempting conversion
        original_frequencies = self.data_uf["frecuencia_escalon"].copy()
        
        # Remove "Hz" and extra spaces
        self.data_uf["frecuencia_escalon"] = (
            self.data_uf["frecuencia_escalon"]
            .str.replace("Hz", "", regex=False)
            .str.strip()
        )
        
        # Replace complex strings containing 48.8 or 49
        self.data_uf["frecuencia_escalon"] = self.data_uf["frecuencia_escalon"].replace(
            {r".*48[,.]8.*": "48.8", r".*49.*": "49"}, regex=True
        )
        
        # Attempt numeric conversion, restoring original non-convertible values
        self.data_uf["frecuencia_escalon"] = pd.to_numeric(self.data_uf["frecuencia_escalon"], errors="coerce").fillna(original_frequencies)

        # Define the target frequency steps to filter
        target_frequencies = [48.3, 48.5, 48.7, 48.9]
        
        # Separate the filtered and remaining data
        _data_uf = self.data_uf[self.data_uf["frecuencia_escalon"].isin(target_frequencies)]
        _data_uf_rest = self.data_uf[~self.data_uf["frecuencia_escalon"].isin(target_frequencies)]
        
        # Store the filtered data as instance attributes
        self.data_uf_step = _data_uf
        self.data_uf_rest = _data_uf_rest

        # Special cases: frequencies 48.8 and 49
        special_mask = _data_uf_rest["frecuencia_escalon"].isin([48.8, 49])

        # Store the special and remaining rest
        self.data_uf_gradient       = _data_uf_rest[special_mask]
        self.data_uf_rest_cleaned   = _data_uf_rest[~special_mask]

    def _uf_by_step_sum(self):

        # Store the filtered data as instance attributes
        _data_uf = self.data_uf_step
        _data_uf_gradient = self.data_uf_gradient 

        # Convert "monto_desconectado" to numeric, removing non-numeric rows
        _data_uf["monto_desconectado"] = pd.to_numeric(_data_uf["monto_desconectado"], errors="coerce")
        _data_uf = _data_uf.dropna(subset=["monto_desconectado"])

        # Sum by frequency step
        _sum_data_uf = _data_uf.groupby("frecuencia_escalon")["monto_desconectado"].sum().reset_index()
        self.sum_data_uf = _sum_data_uf

        # ---- GRADIENT SUM ----
        
        # Define separate patterns for 49 and 48.8
        pattern_49 = r"(^49$|^49\.0*$)"
        pattern_488 = r"(^48\.8$|^48,8$|^48\.80*$)"
        
        # Filter rows for 49 and 48.8 separately
        mask_49 = _data_uf_gradient["frecuencia_escalon"].astype(str).str.contains(pattern_49, regex=True)
        mask_488 = _data_uf_gradient["frecuencia_escalon"].astype(str).str.contains(pattern_488, regex=True)
        
        # Separate the summable rows
        _data_uf_gradient_49 = _data_uf_gradient[mask_49]
        _data_uf_gradient_488 = _data_uf_gradient[mask_488]
        
        # Sum the filtered rows
        sum_49 = pd.to_numeric(_data_uf_gradient_49["monto_desconectado"], errors="coerce").sum()
        sum_488 = pd.to_numeric(_data_uf_gradient_488["monto_desconectado"], errors="coerce").sum()
        
        # Combine the results for the final sum report
        self.sum_data_uf_gradient = pd.DataFrame([
            {"escalon": "5", "monto_desconectado": sum_49},
            {"escalon": "6", "monto_desconectado": sum_488}
        ])

        # Combine the intact, summable rows
        self.data_uf_gradient_summed_intact = pd.concat([_data_uf_gradient_49, _data_uf_gradient_488], ignore_index=True)
        
        # Handle the remaining rows that did not match either pattern
        _data_uf_gradient_rest = _data_uf_gradient[~(mask_49 | mask_488)]
        
        # Append the remaining rows to the rest cleaned
        self.data_uf_rest_cleaned = pd.concat([self.data_uf_rest_cleaned, _data_uf_gradient_rest], ignore_index=True)

    def _report(self):

        # Extract the precomputed sums
        _sum_data_aec = self.sum_data_aec.copy()
        _sum_data_uf = self.sum_data_uf.copy()
        _sum_data_uf_gradient = self.sum_data_uf_gradient.copy()

        # Standardize column names for consistent concatenation
        _sum_data_aec.columns = ["escalon", "monto_desconectado"]
        _sum_data_uf.columns = ["escalon", "monto_desconectado"]
        _sum_data_uf_gradient.columns = ["escalon", "monto_desconectado"]

        # Correction
        _sum_data_aec = _sum_data_aec[_sum_data_aec["escalon"] != 4]

        # Round the amounts to 3 decimals
        _sum_data_aec["monto_desconectado"] = _sum_data_aec["monto_desconectado"].round(3)
        _sum_data_uf["monto_desconectado"] = _sum_data_uf["monto_desconectado"].round(3)
        _sum_data_uf_gradient["monto_desconectado"] = _sum_data_uf_gradient["monto_desconectado"].round(3)

        # Add "Tipo_EDAC" column
        _sum_data_aec["Tipo_EDAC"]  = "EDAC_CCEx"
        _sum_data_uf["Tipo_EDAC"]   = "EDAC_BF"
        _sum_data_uf_gradient["Tipo_EDAC"] = "EDAC_BF"

        # Add detailed "escalon" labels
        _sum_data_aec["escalon"]    = ["1 (-0.9/49.5 Hz)", "2 (-1.2/49.5 Hz)", "3 (-1.9/49.5 Hz)"]
        _sum_data_uf["escalon"]     = ["1 (48.9 Hz)", "2 (48.7 Hz)", "3 (48.5 Hz)", "4 (48.3 Hz)"]
        _sum_data_uf_gradient["escalon"] = ["-0.6 (49 Hz)", "-0.6 (48.8 Hz)"]

        # Create a blank row separator
        _separator = pd.DataFrame([["", "", ""]], columns=["Tipo_EDAC", "escalon", "monto_desconectado"])

        # Combine all DataFrames with the blank row separator
        _report_df = pd.concat([_sum_data_aec, _separator, _sum_data_uf, _separator, _sum_data_uf_gradient], ignore_index=True)

        # Set "Tipo_EDAC" as the index
        _report_df.set_index("Tipo_EDAC", inplace=True)

        # Store the final report
        self.final_report = _report_df

    def _export_data(self, filename="EDAC_Reporte.xlsx"):

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                self.final_report.to_excel(writer, sheet_name="Reporte", index=True) 
                self.data_aec.to_excel(writer, sheet_name="EDAC_CCEx", index=False)                
                
                self.data_uf_step.to_excel(writer, sheet_name="EDAC_BF", index=False)
                self.data_uf_gradient_summed_intact.to_excel(writer, sheet_name="EDAC_BF_Gradiente", index=False)

                self.data_uf_rest_cleaned.to_excel(writer, sheet_name="EDAC_BF_Resto", index=False)
                self.data_fa.to_excel(writer, sheet_name="FA", index=False)
                self.data_other.to_excel(writer, sheet_name="Otros", index=False)
                self.data_north.to_excel(writer, sheet_name="Isla Norte", index=False)
            
            print(f"Data has been successfully exported to {filename}")
        
        except Exception as e:
            print(f"An error occurred while exporting data: {e}")

    def run_handler(self):

        self._separate_northern_substations()
        self._filtering_data()
        self._eac_by_step()
        self._uf_by_step()
        self._uf_by_step_sum()

        self._report()
        self._export_data()

# Stand-alone execution
if __name__ == "__main__":

    file_name = "Análisis EDAC_FALLA 25-02-2025_version 2.xlsx"

    handler = DataHandler(file_name=file_name)
    handler.run_handler()