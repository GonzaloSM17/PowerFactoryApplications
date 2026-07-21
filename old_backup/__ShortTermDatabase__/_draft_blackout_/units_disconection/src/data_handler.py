# 

import os
import pandas as pd

import custom.data_science as ds

import file_io as file_io

FileIO = file_io.FileIO

class DataHandler():
    
    def __init__(self, file_name=None):

        file_io = FileIO(file_name=file_name)
        file_io.run_util()

        self.data = file_io.file_io

    def _dividing_data(self):
        # Drop rows where 'tiempo_en_que_ocurre_la_desconexion' is NaN
        self.data = self.data.dropna(subset=["tiempo_en_que_ocurre_la_desconexion"]).reset_index(drop=True)

        # Define conditions
        condition_woi_1 = self.data["tiempo_en_que_ocurre_la_desconexion"] == "Sin información"
        condition_woi_2 = self.data["tiempo_en_que_ocurre_la_desconexion"] == "Sin Información"
        condition_add   = self.data["tiempo_en_que_ocurre_la_desconexion"] == "No aplica"

        # Combine the conditions for missing or not applicable information
        condition_woi = condition_woi_1 | condition_woi_2 | condition_add

        # Split the data
        _data_woi = self.data[condition_woi].reset_index(drop=True)
        _data_wi  = self.data[~condition_woi].reset_index(drop=True)

        # Save to attributes
        self.data_woi = _data_woi
        self.data_wi  = _data_wi

    def _get_time(self):
        
        self.reference_time = pd.to_timedelta("15:15:41.394")
        _data_wi = self.data_wi.copy()

        # Convert string to individual components: hours, minutes, seconds, milliseconds
        def string_to_components(t):
            
            try:
                t = str(t).replace(",", ".").strip()  # Replace comma with dot and strip spaces
                h, m, s = t.split(":")  # Split into hours, minutes, and seconds
                if "." in s:  # If milliseconds are present
                    s, ms = s.split(".")  # Split seconds and milliseconds
                    ms = int(ms)  # Convert milliseconds to integer

                    # If milliseconds exceed 999, adjust to valid range (0-999)
                    ms_str = str(ms)
                    if len(ms_str) > 3:  # Check if milliseconds have more than 3 digits
                        ms = int(ms_str[:3])  # Keep only the first 3 digits
                    return int(h), int(m), int(s), ms
                else:
                    return int(h), int(m), int(s), 0  # Default to 0 milliseconds if none
            except Exception as e:
                # Handle error if the conversion fails
                print(f"Error parsing time '{t}': {e}")
                return 0, 0, 0, 0  # Return zeros if error occurs

        # Apply the string_to_components function and split into separate columns
        _data_wi[['hour', 'minute', 'second', 'millisecond']] = _data_wi["tiempo_en_que_ocurre_la_desconexion"].apply(lambda t: pd.Series(string_to_components(t)))

        # Drop the original 'tiempo_en_que_ocurre_la_desconexion' column
        _data_wi = _data_wi.drop(columns=["tiempo_en_que_ocurre_la_desconexion"])

        # Rebuild the time to the format hh:mm:ss.mmm
        _data_wi["reconstructed_time"] = (_data_wi['hour'].astype(str).str.zfill(2) + ":" +
                                        _data_wi['minute'].astype(str).str.zfill(2) + ":" +
                                        _data_wi['second'].astype(str).str.zfill(2) + "." +
                                        _data_wi['millisecond'].astype(str).str.zfill(3))

        # Compute the time difference in seconds (after reconstruction)
        _data_wi["tiempo_en_que_ocurre_la_desconexion"] = pd.to_timedelta(_data_wi['hour'], unit='h') + \
                                                        pd.to_timedelta(_data_wi['minute'], unit='m') + \
                                                        pd.to_timedelta(_data_wi['second'], unit='s') + \
                                                        pd.to_timedelta(_data_wi['millisecond'], unit='ms')

        # Compute the time difference in seconds (from reference time)
        _data_wi["tiempo"] = (
            (_data_wi["tiempo_en_que_ocurre_la_desconexion"] - self.reference_time)
            .dt.total_seconds()
        )

        # Order by 'tiempo'
        _data_wi = _data_wi.sort_values(by="tiempo")

        # Create 'tiempo_simulacion' by adding 1 second to each row in 'tiempo'
        _data_wi["tiempo_simulacion"] = _data_wi["tiempo"] + 1

        self.data_wi_ = _data_wi


    def _export_data(self, filename="times_data.xlsx"):

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                self.data_wi_.to_excel(writer, sheet_name="Tiempos", index=False)                
                self.data_woi.to_excel(writer, sheet_name="Sin Información", index=False)
            
            print(f"Data has been successfully exported to {filename}")
        
        except Exception as e:
            print(f"An error occurred while exporting data: {e}")

    def run_handler(self):

        self._dividing_data()
        self._get_time()
        self._export_data()

# Stand-alone execution
if __name__ == "__main__":

    file_name = "Listado de Centrales en Isla Centro Sur.xlsx"

    handler = DataHandler(file_name=file_name)
    handler.run_handler()