import pandas as pd
import numpy as np


class DispatchDistributionCalculator:
    """Calculates distribution factors from Plexos dispatch to PowerFactory units."""

    HOUR_COLUMNS = [str(i) for i in range(1, 25)]

    def __init__(self, merged_df: pd.DataFrame):
        """Initialize with merged dispatch-constraints DataFrame."""
        self.merged = merged_df.copy()
        self.distribution = {}

    def calculate_all(self) -> dict[pd.DataFrame]:
        """Calculate all distributions and aggregations."""
        allocated = self.calculate_allocated()
        aggregated = self._aggregate_by_pf_unit()

        self.distribution["allocated"] = allocated.reset_index(drop=True)
        self.distribution["aggregated"] = aggregated.reset_index(drop=True)

        return self.distribution

    def calculate_allocated(self) -> pd.DataFrame:
        """Calculate distributions: first by pfClass, then by cennom.

        Returns DataFrame with pfUnitName and allocation columns for each hour.
        """
        all_results = []

        # Group only by pfClass (strategy type)
        for pf_class in self.merged["pfClassName"].unique():
            class_df = self.merged[self.merged["pfClassName"] == pf_class]

            # For each cennom in this class, get ONE dispatch row and ALL its PF units
            for cennom in class_df["cennom"].unique():
                cennom_rows = class_df[class_df["cennom"] == cennom]

                # Get dispatch from first row (all rows have same dispatch)
                dispatch_row = cennom_rows.iloc[0]
                dispatch_values = dispatch_row[self.HOUR_COLUMNS].values.astype(float)

                # Apply strategy based on class
                # NO clipping here - distribute ALL dispatch regardless of capacity
                if pf_class in ["noSym", "aSym"]:
                    allocations = self._allocate_proportional(
                        cennom_rows, dispatch_values
                    )
                elif pf_class == "Sym":
                    allocations = self._allocate_greedy(cennom_rows, dispatch_values)
                elif pf_class == "Sym-CC":
                    allocations = self._allocate_iterative(cennom_rows, dispatch_values)
                else:
                    allocations = {i: np.zeros(24) for i in range(len(cennom_rows))}

                # Store results for each PF unit
                cennom_reset = cennom_rows.reset_index(drop=True)
                for idx in range(len(cennom_reset)):
                    result_row = cennom_reset.iloc[idx].copy()
                    for h, hour in enumerate(self.HOUR_COLUMNS):
                        result_row[f"alloc_{hour}"] = allocations[idx][h]
                    all_results.append(result_row)

        # Create single consolidated DataFrame with pfUnitName and allocations
        allocated_df = pd.DataFrame(all_results).reset_index(drop=True)

        # Keep only pfUnitName and allocation columns
        alloc_cols = [f"alloc_{h}" for h in self.HOUR_COLUMNS]
        self.allocated_df = allocated_df[["pfUnitName"] + alloc_cols].copy()

        return self.allocated_df

    def _aggregate_by_pf_unit(self) -> None:
        """Group allocated data by pfUnitName and sum allocations across all cennom."""
        allocated = self.allocated_df
        alloc_cols = [f"alloc_{h}" for h in self.HOUR_COLUMNS]

        # Group by pfUnitName and sum the allocations
        grouped = allocated.groupby("pfUnitName")[alloc_cols].sum().reset_index()
        self.aggregated_df = grouped

        return self.aggregated_df

    def _allocate_proportional(self, group: pd.DataFrame, dispatch: np.ndarray) -> dict:
        """Proportional by pMax_absolute ratio. Pure proportional without clipping."""
        pmax_values = group["pMax_absolute"].values.astype(float)
        total_pmax = pmax_values.sum()

        allocations = {}

        for idx in range(len(group)):
            pmax_this = pmax_values[idx]
            allocation = np.zeros(24)

            for h in range(24):
                disp_h = dispatch[h]

                if total_pmax > 0:
                    weight = pmax_this / total_pmax
                    alloc_h = disp_h * weight
                else:
                    alloc_h = disp_h / len(group)

                allocation[h] = alloc_h

            allocations[idx] = allocation

        return allocations

    def _allocate_greedy(self, group: pd.DataFrame, dispatch: np.ndarray) -> dict:
        """Greedy (for Sym): activate minimum units needed, distribute proportionally.

        Algorithm:
        1. Sort units by pMax descending (largest capacity first)
        2. Activate sequentially until cumulative pMax >= dispatch
        3. Distribute dispatch proportionally by pMax among active units ONLY
        4. No unit exceeds its pMax
        5. All dispatch is allocated (no loss)
        """
        pmax_values = group["pMax_absolute"].values.astype(float)
        n_units = len(group)

        # Create sorted indices: descending by pMax
        sorted_indices = np.argsort(-pmax_values)

        allocations = {idx: np.zeros(24) for idx in range(n_units)}

        for h in range(24):
            dispatch_h = dispatch[h]

            # Find minimum set of units needed to handle dispatch
            cumulative_capacity = 0.0
            active_indices = []

            for idx in sorted_indices:
                active_indices.append(idx)
                cumulative_capacity += pmax_values[idx]
                if cumulative_capacity >= dispatch_h - 1e-9:
                    break

            # Distribute proportionally among active units
            total_capacity_active = pmax_values[active_indices].sum()

            for idx in active_indices:
                if total_capacity_active > 1e-9:
                    weight = pmax_values[idx] / total_capacity_active
                    allocations[idx][h] = dispatch_h * weight
                else:
                    allocations[idx][h] = dispatch_h / len(active_indices)

        return allocations

    def _allocate_iterative(self, group: pd.DataFrame, dispatch: np.ndarray) -> dict:
        """
        Iterative: distribute proportionally with iterative redistribution (NO LOSS).

        Algorithm:
        1. Use absolute values to track precise allocation and remaining
        2. Distribute remaining proportionally by available capacity (pMax - current_alloc)
        3. Clip to pMax limits and recalculate remaining
        4. Iterate until all dispatch allocated OR all units at pMax
        5. Store allocations as absolute values
        """
        pmax_values = group["pMax_absolute"].values.astype(float)
        pmin_values = group["pMin_absolute"].values.astype(float)
        n_units = len(group)

        allocations = {}

        for h in range(24):
            # Use absolute dispatch amount for this hour
            dispatch_h_absolute = np.abs(dispatch[h])
            hour_allocs = np.zeros(n_units, dtype=np.float64)  # Absolute allocations

            active_units = set(range(n_units))
            iteration = 0
            max_iterations = 100

            while iteration < max_iterations and len(active_units) > 0:
                iteration += 1

                # Total already allocated (absolute)
                allocated_total = np.abs(hour_allocs.sum())

                # Remaining to allocate (absolute)
                remaining_absolute = np.abs(dispatch_h_absolute - allocated_total)

                if remaining_absolute < 1e-9:
                    # All allocated
                    break

                # Calculate available capacity for each active unit (absolute)
                available_capacity = np.zeros(n_units, dtype=np.float64)
                for idx in active_units:
                    available_capacity[idx] = np.abs(
                        pmax_values[idx] - hour_allocs[idx]
                    )

                total_available = np.abs(available_capacity.sum())

                if total_available < 1e-9:
                    # All units at pMax
                    break

                # Distribute remaining proportionally by available capacity (absolute values)
                for idx in active_units:
                    proportion = np.abs(available_capacity[idx]) / total_available
                    increment = remaining_absolute * proportion
                    hour_allocs[idx] = np.abs(hour_allocs[idx] + increment)

                # Clip to pMax and remove maxed units
                to_remove = []
                for idx in list(active_units):
                    if hour_allocs[idx] > pmax_values[idx]:
                        hour_allocs[idx] = np.abs(pmax_values[idx])
                        to_remove.append(idx)

                for idx in to_remove:
                    active_units.discard(idx)

            # Store hour allocations (absolute values)
            for idx in range(n_units):
                if idx not in allocations:
                    allocations[idx] = np.zeros(24, dtype=np.float64)
                allocations[idx][h] = np.abs(hour_allocs[idx])

        return allocations


if __name__ == "__main__":
    from short_term_scenarios.modules.unit_mapper import UnitMapper
    from short_term_scenarios.modules.dispatch_merger import DispatchMerger
    from short_term_scenarios.handlers.sh_term_data import (
        ShTermDataHandler,
    )
    from short_term_scenarios.handlers.assets_mapping import AssetsMapper

    shts_handler = ShTermDataHandler(scenario="E4")
    assets_extractor = AssetsMapper()

    mapper = UnitMapper(shts_handler, assets_extractor)
    mapper.materialize()

    merger = DispatchMerger(mapper)
    merged, _ = merger.merge()

    calculator = DispatchDistributionCalculator(merged)
    results = calculator.calculate_all()
