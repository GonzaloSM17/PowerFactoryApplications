import os
from pathlib import Path

# Get the directory of the vector files
IN_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent

# Get the absolute path to short_term_scenarios data directory
SHT_SCENARIOS_BASE = IN_SCRIPT_PATH / "mapper"
SHT_SCENARIOS_DATA_PATH = SHT_SCENARIOS_BASE / "data"

# Scenario files mapping (Excel files per scenario)
SHT_SCENARIOS_FILES_PATH = {
    "E1": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E1.xlsx",
    "E2": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E2.xlsx",
    "E3": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E3.xlsx",
    "E4": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E4.xlsx",
    "E5": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E5.xlsx",
    "E6": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E6.xlsx",
    "E7": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E7.xlsx",
    "E8": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E8.xlsx",
    "E5B": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E5B.xlsx",
    "E6B": SHT_SCENARIOS_DATA_PATH / "Solicitud Escenarios Planilla E6B.xlsx",
}

# Access database path (AssetsMapping)
DATABASE_ASSETS_MAPPING_PATH = SHT_SCENARIOS_DATA_PATH

# Vectors output directory
SHT_SCENARIOS_VECTORS_PATH = SHT_SCENARIOS_BASE / "vectors_files"

# Ensure directories exist
SHT_SCENARIOS_DATA_PATH.mkdir(parents=True, exist_ok=True)
SHT_SCENARIOS_VECTORS_PATH.mkdir(parents=True, exist_ok=True)


# Output paths for vectors
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


if __name__ == "__main__":

    print("Vector files paths:")
    for scenario, path in VECTOR_FILES_PATH.items():
        print(f"{scenario}: {path}")

    print("\nShort term scenarios files paths:")
    for scenario, path in SHT_SCENARIOS_FILES_PATH.items():
        print(f"{scenario}: {path}")

    print(f"\nDatabase path: {DATABASE_ASSETS_MAPPING_PATH}")
