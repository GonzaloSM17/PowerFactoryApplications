import os
from pathlib import Path

# Get the directory of the vector files
IN_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent

# Inputs paths
VECTOR_FOLDER_PATH = IN_SCRIPT_PATH / "mapper" / "vectors_files"
VECTOR_FILES_PATH = {
    "E1": VECTOR_FOLDER_PATH / "__E1_pfVector__.xlsx",
    "E2": VECTOR_FOLDER_PATH / "__E2_pfVector__.xlsx",
    "E3": VECTOR_FOLDER_PATH / "__E3_pfVector__.xlsx",
    "E4": VECTOR_FOLDER_PATH / "__E4_pfVector__.xlsx",
    "E5": VECTOR_FOLDER_PATH / "__E5_pfVector__.xlsx",
    "E6": VECTOR_FOLDER_PATH / "__E6_pfVector__.xlsx",
    "E7": VECTOR_FOLDER_PATH / "__E7_pfVector__.xlsx",
    "E8": VECTOR_FOLDER_PATH / "__E8_pfVector__.xlsx",
    "E5B": VECTOR_FOLDER_PATH / "__E5B_pfVector__.xlsx",
    "E6B": VECTOR_FOLDER_PATH / "__E6B_pfVector__.xlsx",
}


LOADS_DATABASE = IN_SCRIPT_PATH / "integrator" / "data" / "AASS_Loads.xlsx"


OUTPUT_REPORT_PATH = IN_SCRIPT_PATH / "integrator" / "reports"

# Stand-alone execution
if __name__ == "__main__":

    print("IN_SCRIPT_PATH:", IN_SCRIPT_PATH)
    print("INPUT_VECTOR_PATH:", VECTOR_FOLDER_PATH)
    print("INPUT_LOADS_PATH:", LOADS_DATABASE)
    print("OUTPUT_REPORT_PATH:", OUTPUT_REPORT_PATH)
