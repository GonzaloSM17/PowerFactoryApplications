"""
Scenario Context Module
Defines the immutable context for scenario processing.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScenarioContext:
    """
    Immutable context containing all scenario parameters.
    Passed to all steps in pipelines.

    This context serves as a single source of truth for scenario configuration,
    ensuring consistency across all processing steps.
    """

    # Identification
    name: str  # Unique scenario name (e.g., "E1_H12_DemandHigh_HydroDry")
    scenario_to_use: str  # PowerFactory scenario name to activate

    # Temporal parameters
    hour: int  # Hour of the day (0-23)
    day: int  # Day of month (1-31)
    month: int  # Month (1-12)
    year: int  # Year

    # Operational conditions
    demand_level: str  # Demand level: "High", "Medium", "Low"
    hydrology_level: str  # Hydrology level: "Wet", "Normal", "Dry"

    def __post_init__(self):
        """Validate context parameters"""
        # Validate hour
        if not (1 <= self.hour <= 24):
            raise ValueError(f"Hour must be between 1 and 24, got {self.hour}")

        # Validate day
        if not (1 <= self.day <= 31):
            raise ValueError(f"Day must be between 1 and 31, got {self.day}")

        # Validate month
        if not (1 <= self.month <= 12):
            raise ValueError(f"Month must be between 1 and 12, got {self.month}")

        # Validate demand level
        valid_demand_levels = ["DA", "DM", "DB"]
        if self.demand_level not in valid_demand_levels:
            raise ValueError(
                f"Demand level must be one of {valid_demand_levels}, got {self.demand_level}"
            )

        # Validate hydrology level
        valid_hydrology_levels = ["HA", "HM", "HS"]
        if self.hydrology_level not in valid_hydrology_levels:
            raise ValueError(
                f"Hydrology level must be one of {valid_hydrology_levels}, got {self.hydrology_level}"
            )

    def __str__(self):
        """String representation for logging"""
        return (
            f"{self.name} "
            f"(H{self.hour:02d}, {self.demand_level} demand, {self.hydrology_level} hydro)"
        )

    def __repr__(self):
        """Detailed representation for debugging"""
        return (
            f"ScenarioContext("
            f"name='{self.name}', "
            f"scenario_to_use='{self.scenario_to_use}', "
            f"hour={self.hour}, "
            f"date={self.year}-{self.month:02d}-{self.day:02d}, "
            f"demand={self.demand_level}, "
            f"hydro={self.hydrology_level})"
        )

    @property
    def date_string(self) -> str:
        """Get formatted date string"""
        return f"{self.year}-{self.month:02d}-{self.day:02d}"

    @property
    def hour_string(self) -> str:
        """Get formatted hour string"""
        return f"H{self.hour:02d}"


# Example usage and validation
if __name__ == "__main__":

    # Valid scenario
    scenario = ScenarioContext(
        name="E4",
        scenario_to_use="E4",
        hour=14,
        day=22,
        month=12,
        year=2027,
        demand_level="DA",
        hydrology_level="HM",
    )

    logger.info("Scenario created successfully:")
