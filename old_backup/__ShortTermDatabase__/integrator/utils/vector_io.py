"""
Vector I/O Module
Reads and filters dispatch vectors from Excel files for PowerFactory scenarios.
"""

import pandas as pd
from typing import Dict, Optional

import integrator.utils.routes as routes

# Initialize variables
VECTOR_FILES_PATH = routes.VECTOR_FILES_PATH
AASS_LOADS_PATH = routes.LOADS_DATABASE


class VectorIO:
    """
    Reads dispatch vectors from Excel files and filters by hour.
    Returns DataFrames with unit names (pf_name) and dispatch values (pgini).
    """

    def __init__(self, scenario: str, hour: int):
        """
        Initialize and load vector data for a given scenario and hour.

        Args:
            scenario: Scenario identifier (e.g., "E1", "E2")
            hour: Hour of the day (0-23)

        Raises:
            ValueError: If scenario or hour are invalid
            FileNotFoundError: If scenario file is not found
        """
        if scenario is None:
            raise ValueError("Scenario is required. Please provide a valid scenario.")

        if hour is None or not (1 <= hour <= 24):
            raise ValueError("Hour must be between 1 and 24.")

        self.scenario = scenario
        self.hour = hour
        self.scenario_vector: Dict[str, pd.DataFrame] = {}

        # Load and filter vectors
        self._read_scenario_file()
        self._filter_by_hour()

    def _read_scenario_file(self):
        """Read all vector sheets from Excel file"""
        sheet_info = {
            "balance": ("_balance_", "A:Y"),
            "symVector": ("_Sym_", "A,I:AF"),
            "noSymVector": ("_noSym_", "A,I:AF"),
            "aSymVector": ("_aSym_", "A,I:AF"),
            "derVector": ("_der_", "A:Y"),
            "biasVector": ("_frequencyBias_", "A:Y"),
        }

        if self.scenario not in VECTOR_FILES_PATH:
            raise ValueError(f"Scenario '{self.scenario}' not found in configuration.")

        try:
            scenario_path = VECTOR_FILES_PATH[self.scenario]
            vector_file = pd.ExcelFile(scenario_path)

        except (ValueError, FileNotFoundError) as e:
            raise FileNotFoundError(
                f"Scenario file for '{self.scenario}' not found: {e}"
            )

        for key, (sheet_name, usecols) in sheet_info.items():
            try:
                df = pd.read_excel(vector_file, sheet_name=sheet_name, usecols=usecols)

                if key != "balance":
                    # Rename first column to standard name
                    df.columns.values[0] = "pf_name"

                self.scenario_vector[key] = df

            except Exception as e:
                self.scenario_vector[key] = None
                print(f"Warning: Could not read sheet '{sheet_name}': {e}")

    def _filter_by_hour(self):
        """Filter vector data by the specified hour"""
        if not self.scenario_vector:
            raise ValueError("Vector data has not been read.")

        hour_column = str(self.hour)

        for key, df in self.scenario_vector.items():
            if df is None:
                continue

            if hour_column not in df.columns:
                raise ValueError(
                    f"Hour column '{hour_column}' not found in '{key}' DataFrame"
                )

            # Filter and rename columns based on vector type
            if key == "balance":
                self.scenario_vector[key] = (
                    df.loc[:, ["-", hour_column]]
                    .rename(columns={hour_column: "balance"})
                    .dropna()
                    .reset_index(drop=True)
                )
            elif key == "biasVector":
                self.scenario_vector[key] = df.loc[:, ["pf_name", hour_column]].rename(
                    columns={hour_column: "Kpf"}
                )
            else:
                # For dispatch vectors (sym, nosym, asym)
                self.scenario_vector[key] = df.loc[:, ["pf_name", hour_column]].rename(
                    columns={hour_column: "pgini"}
                )

    def get_vector(self, vector_type: str) -> Optional[pd.DataFrame]:
        """
        Get a specific vector DataFrame.

        Args:
            vector_type: One of "sym_vector", "nosym_vector", "der_vector","asym_vector", "bias_vector", "balance"

        Returns:
            DataFrame with filtered vector data or None if not available
        """
        return self.scenario_vector.get(vector_type)

    def get_all_vectors(self) -> Dict[str, pd.DataFrame]:
        """
        Get all loaded vectors.

        Returns:
            Dictionary with all vector DataFrames
        """
        return self.scenario_vector.copy()


# Stand-alone execution
if __name__ == "__main__":

    # Example usage
    vector_io = VectorIO(scenario="E4", hour=12)

    # print("Available vectors:")
    # for key, df in vector_io.get_all_vectors().items():
    #     if df is not None:
    #         print(f"  {key}: {len(df)} rows")
    #         print(df.head())
    #         print()
