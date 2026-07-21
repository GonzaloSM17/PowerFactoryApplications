from dataclasses import dataclass
from typing import Optional
import pandas as pd
import unicodedata

import mapper.utils.routes as routes

UNIT_COMMITMENT_FILES_PATH = routes.SHT_SCENARIOS_FILES_PATH


@dataclass(frozen=True)
class SheetConfig:
    """Configuration for loading a specific sheet."""

    key: str
    sheet_name: str
    header_row: int


class ShTermDataManager:
    """Handles loading and processing short term scenarios excel files."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]

    def __init__(self, scenario: str):
        if scenario not in UNIT_COMMITMENT_FILES_PATH:
            raise ValueError(f"Scenario '{scenario}' not found in SCENARIOS_FILES.")

        path = UNIT_COMMITMENT_FILES_PATH[scenario]
        if path is None:
            raise ValueError(
                f"Path for scenario '{scenario}' not found in SCENARIOS_FILES."
            )

        self.scenario = scenario
        self.path = path
        self.shts_data: dict[str, pd.DataFrame] = {}
        self.file: Optional[pd.ExcelFile] = None

    def materialize(self) -> None:
        """Load and process all sheets for the scenario."""
        self._load_sheets()
        self._normalize_fuel_type()
        self._calculate_balance()
        self._integrate_battery_dispatch()

        return self.shts_data

    def _load_sheets(self) -> None:
        """Load sheets from Excel file based on scenario configuration."""
        self.file = pd.ExcelFile(self.path)
        sheet_configs = self._get_sheet_configs()

        for config in sheet_configs:
            self._load_single_sheet(config)

    def _get_sheet_configs(self) -> list[SheetConfig]:
        """Build sheet configuration based on scenario."""
        # scenario_key = "E1" if self.scenario == "E4" else self.scenario
        scenario_key = self.scenario

        configs = [
            SheetConfig("shTSUnits", f"1. {scenario_key}", 7),
            SheetConfig("shTSDispatch", f"2. {scenario_key} Salida Gen Bruta", 1),
            SheetConfig("shTSLoadflow", f"3. {scenario_key} Salida Flujo", 1),
            SheetConfig("shTSDemand", f"4. {scenario_key} Salida Cargas", 1),
            SheetConfig("shTSCpfLw", f"5. {scenario_key} CPF_LW", 1),
            SheetConfig("shTSCpfRs", f"6. {scenario_key} CPF_RS", 1),
            SheetConfig("shTSLoadbess", f"7. {scenario_key} Carga BESS", 1),
        ]

        return configs

    def _load_single_sheet(self, config: SheetConfig) -> None:
        """Load a single sheet and apply transformations."""
        try:
            df = self.file.parse(sheet_name=config.sheet_name, header=config.header_row)

            # Normalize column names to camelCase
            df.columns = [self._to_lower_camel_case(str(col)) for col in df.columns]

            # Remove completely empty rows
            df = df.dropna(how="all").reset_index(drop=True)

            self.shts_data[config.key] = df
        except Exception as e:

            self.shts_data[config.key] = pd.DataFrame()
            print(
                f"Warning: Failed to load sheet '{config.sheet_name}' for scenario '{self.scenario}': {e}"
            )

    # ... existing code ...

    @staticmethod
    def _to_lower_camel_case(text: str) -> str:
        """Convert text to lowerCamelCase and remove accents from column names.

        This normalizes Excel column headers by:
        1. Removing accents (é -> e, á -> a, etc)
        2. Converting to lowerCamelCase for consistency

        Note: This is applied ONLY to column names (headers) for consistency.
        Data values in the cells remain unchanged.
        """
        text = str(text).strip()

        # Remove accents from column names only (NFD normalization + ASCII encoding)
        # This converts: "Potencia Bruta Minima" -> "potenciaBrutaMinima"
        text = (
            unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")
        )

        if not text or text == "nan":
            return text

        words = text.split()
        if not words:
            return text

        # Convert to lowerCamelCase: first word lowercase, rest capitalized
        result = words[0].lower()
        for word in words[1:]:
            if word.startswith("("):
                result += word
            else:
                result += word.capitalize()

        return result

    def _normalize_fuel_type(self) -> None:
        """Normalize fuel type column: replace invalid values and forward fill."""
        if "shTSUnits" not in self.shts_data or self.shts_data["shTSUnits"].empty:
            return

        fuel_col = self.shts_data["shTSUnits"]["tipoDeCombustible"]
        fuel_col = fuel_col.replace(["0", 0, "-"], pd.NA).ffill()
        self.shts_data["shTSUnits"]["tipoDeCombustible"] = fuel_col

    def _calculate_balance(self) -> None:
        """Calculate Plexos balance: total generation, battery discharge, battery charge."""
        total_gen = self._aggregate_sheet("shTSDispatch", "totalGeneration(MW)Plexos")
        batt_discharge = self._filter_and_aggregate(
            "shTSDispatch", "BAT_", "Battery(MW)Plexos(+)"
        )

        batt_charge = self.shts_data["shTSLoadbess"].copy()
        batt_charge = batt_charge.dropna(how="all").reset_index(drop=True)
        batt_charge[self.HOUR_COLUMNS] = batt_charge[self.HOUR_COLUMNS] * (-1)
        batt_charge.iloc[:, 0] = "Battery(MW)Plexos(-)"
        batt_charge = (
            batt_charge.groupby(batt_charge.columns[0])[self.HOUR_COLUMNS]
            .sum()
            .round(1)
            .reset_index()
        )

        self.shts_data["balancePlexos"] = pd.concat(
            [total_gen, batt_discharge, batt_charge], axis=0, ignore_index=True
        )

    def _integrate_battery_dispatch(self) -> None:
        """Integrate battery charge/discharge into dispatch sheet."""
        dispatch = self.shts_data["shTSDispatch"].copy()
        dispatch = dispatch.dropna(subset=[dispatch.columns[0]]).reset_index(drop=True)

        dispatch_batt_mask = (
            dispatch[dispatch.columns[0]].astype(str).str.contains("BAT_", na=False)
        )
        dispatch.loc[dispatch_batt_mask, self.HOUR_COLUMNS] = dispatch.loc[
            dispatch_batt_mask, self.HOUR_COLUMNS
        ].abs()

        charge = self.shts_data["shTSLoadbess"].copy()
        charge = charge.dropna(subset=[charge.columns[0]]).reset_index(drop=True)

        charge_batt_mask = (
            charge[charge.columns[0]].astype(str).str.contains("BAT_", na=False)
        )
        charge.loc[charge_batt_mask, self.HOUR_COLUMNS] *= -1

        # Remove _LOAD suffix from cennom in charge
        charge[charge.columns[0]] = (
            charge[charge.columns[0]].astype(str).str.replace("_LOAD", "", regex=True)
        )

        combined = pd.concat([dispatch, charge], ignore_index=True)
        combined = (
            combined.groupby(combined.columns[0])[self.HOUR_COLUMNS].sum().reset_index()
        )

        self.shts_data["shTSDispatch"] = combined.reset_index(drop=True)

    def _aggregate_sheet(self, sheet_key: str, label: str) -> pd.DataFrame:
        """Aggregate a sheet and label the result."""
        df = self.shts_data[sheet_key].copy()
        df[df.columns[0]] = label
        return df.groupby(df.columns[0])[self.HOUR_COLUMNS].sum().round(1).reset_index()

    def _filter_and_aggregate(
        self, sheet_key: str, pattern: str, label: str
    ) -> pd.DataFrame:
        """Filter sheet by pattern and aggregate."""
        df = self.shts_data[sheet_key].copy()
        df = df[
            df[df.columns[0]].astype(str).str.contains(pattern, na=False)
        ].reset_index(drop=True)
        df[df.columns[0]] = label
        return df.groupby(df.columns[0])[self.HOUR_COLUMNS].sum().round(1).reset_index()


if __name__ == "__main__":
    handler = ShTermDataManager(scenario="E4")
    handler.materialize()
