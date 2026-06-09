"""
LLM4AD Evaluator for MCM 2024 Problem D: Great Lakes Water Level Control

This evaluator takes a GENOTYPE (modeling design choices across 8 dimensions)
and returns FITNESS metrics. It does NOT evolve control parameters directly -
it evaluates HOW GOOD a particular MODELING METHODOLOGY is for this problem.

This follows the standard LLM4AD evaluator interface.
"""

import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from llm4ad.evaluator.base import BaseEvaluator, EvaluationResult, Metric, MetricType
from llm4ad.config.evaluator import EvalContext


# ============================================================
# 8-Dimensional Gene Space Definition (Core Search Space)
# ============================================================
# Each locus represents a fundamental choice in the modeling methodology
# This is the space LLM4AD searches - not parameters, but METHODOLOGY

GENE_SPACE = {
    # 1. Dynamics Fidelity
    "dynamics": [
        "simple_mass_balance",      # Basic inflow = outflow
        "seasonal_evap",            # + Seasonal evaporation pattern
        "flow_delay",               # + River travel time between lakes
        "stochastic_inflow",        # + Probabilistic inflow model
    ],

    # 2. Constraint Handling Method
    "constraints": [
        "hard_clipping",            # Clip flows to bounds (0 violation)
        "soft_penalty",             # Quadratic penalty for violations
        "barrier_function",         # Log barrier for interior point method
        "leaky_constraint",         # Allow small violation with heavy penalty
    ],

    # 3. Objective Function Mathematical Form
    "objective_form": [
        "linear_weighted",          # Standard weighted sum
        "chebyshev",                # Min-max: minimize worst-case regret
        "exponential_utility",      # Diminishing returns curve
        "lexicographic",            # Rank objectives, optimize sequentially
        "min_max_fairness",         # Max-min fairness across stakeholders
    ],

    # 4. Stakeholder Subset to Explicitly Model
    "stakeholders": [
        "core_3",                   # Flood, Nav, Hydro only
        "balanced_4",               # + Recreation
        "comprehensive_5",          # + Ecosystem
        "full_6",                   # All 6 including Municipal Water
    ],

    # 5. Optimization Solver Paradigm
    "solver": [
        "nsga2",                    # Multi-objective genetic algorithm
        "mpc_rolling",              # Model Predictive Control (receding horizon)
        "linear_program",           # LP for convex objectives
        "particle_swarm",           # PSO for non-convex spaces
        "bayesian_opt",             # Bayesian optimization (expensive objectives)
        # "admm_distributed" <- L3 meta-learner may propose this new allele!
    ],

    # 6. Temporal Architecture
    "temporal": [
        "annual_monthly",           # 12 monthly steps, 1 year horizon
        "seasonal_peak",            # 4 seasons with peak flow focus
        "multi_year",               # Multi-year planning (60 months)
        "event_triggered",          # Adaptive steps based on extreme events
    ],

    # 7. Robustness Paradigm
    "robustness": [
        "deterministic",            # Nominal values only (no uncertainty)
        "worst_case",               # Minimize maximum loss
        "stochastic_expected",      # Minimize expected value over scenarios
        "stochastic_cvar",          # Minimize Conditional Value-at-Risk
    ],

    # 8. Multi-Objective Coupling Method
    "coupling": [
        "equal_weight",             # All objectives get equal weight (1/6)
        "entropy_weight",           # Data-driven entropy weighting
        "ahp_hierarchy",            # Analytic Hierarchy Process pairwise
        "pareto_filter",            # Full Pareto frontier selection
        "topsis",                   # TOPSIS ranking method
    ],
}


# ============================================================
# Great Lakes Physical Parameters (Real Engineering Data)
# ============================================================
LAKE_NAMES = ["Superior", "Michigan", "Huron", "Erie", "Ontario"]

# Surface area in km²
SURFACE_AREAS = np.array([82100, 58000, 59600, 25700, 18960])

# Nominal level in meters
NOMINAL_LEVELS = np.array([183.0, 177.0, 176.5, 173.5, 74.2])

# Historical safe level ranges in meters [min, max]
LEVEL_RANGES = np.array([
    [182.0, 184.0],  # Superior
    [176.0, 178.0],  # Michigan
    [175.5, 177.5],  # Huron
    [172.5, 174.5],  # Erie
    [73.2, 75.2],    # Ontario
])

# Dam flow ranges in m³/s
DAM_NAMES = ["Soo Locks", "Moses-Saunders"]
DAM_FLOW_RANGES = np.array([
    [1000.0, 3000.0],  # Soo Locks (Superior -> Huron/Michigan)
    [6000.0, 10000.0],  # Moses-Saunders (Ontario outflow)
])


# ============================================================
# Evaluator Class (Standard LLM4AD Interface)
# ============================================================

@BaseEvaluator.register("great_lakes_modeling_evaluator")
class GreatLakesModelingEvaluator(BaseEvaluator):
    """
    Evaluate a particular MODELING METHODOLOGY (genotype) on the
    Great Lakes water level control problem.

    This evaluator follows standard LLM4AD BaseEvaluator interface:
    - Input: genotype (dict with 8 keys: dynamics, constraints, ...)
    - Output: EvaluationResult with fitness and all objective values
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.gene_space = GENE_SPACE.copy()

        # Load historical data if available
        self.historical_data = self._load_historical_data()

        # Default simulation parameters
        self.n_timesteps = 60  # 5 years monthly

        # State for flow_delay dynamics (stores previous timestep deltas)
        self._prev_deltas = None

    @property
    def name(self) -> str:
        return "great_lakes_modeling_evaluator"

    @property
    def metrics(self) -> List[Metric]:
        return [
            # 6 Stakeholder objectives (per problem statement)
            Metric(name="flood_prevention", type=MetricType.MAXIMIZE, weight=1.0),
            Metric(name="navigation", type=MetricType.MAXIMIZE, weight=0.8),
            Metric(name="hydropower", type=MetricType.MAXIMIZE, weight=0.5),
            Metric(name="recreation", type=MetricType.MAXIMIZE, weight=0.6),
            Metric(name="ecosystem", type=MetricType.MAXIMIZE, weight=0.7),
            Metric(name="municipal_water", type=MetricType.MAXIMIZE, weight=0.6),
            Metric(name="constraint_satisfaction", type=MetricType.MAXIMIZE, weight=1.5),
            # Key requirements per problem statement (lines 11-12)
            Metric(name="backtesting_deviation", type=MetricType.MINIMIZE, weight=2.0),  # vs 2017 actual
            Metric(name="sensitivity_score", type=MetricType.MAXIMIZE, weight=1.5),     # robustness to env change
            # Overall
            Metric(name="overall_fitness", type=MetricType.MAXIMIZE, weight=1.0),
        ]

    def _load_historical_data(self) -> Dict[str, np.ndarray]:
        """Load historical inflow and target level data.

        Data source priority:
        1. Derive real inflows from CSV lake water levels + river flows (mass balance)
        2. Load from great_lakes_data.json (JSON format)
        3. Simple historical data from historical_*.json
        4. Synthetic data as last resort

        Returns:
            Dict with keys: 'inflows', 'historical_levels', 'target_levels',
                  'min_levels', 'max_levels', 'river_flows' (optional)
        """
        data_dir = Path(__file__).parent / "data" / "train"
        csv_dir = Path(__file__).parent / "data"

        # Priority 1: Derive real inflows from CSV data
        result = self._derive_inflows_from_csv(csv_dir)
        if result is not None:
            return result

        # Priority 2: Load from JSON
        complete_data_path = data_dir / "great_lakes_data.json"
        if complete_data_path.exists():
            result = self._load_from_json(complete_data_path)
        elif data_dir.exists():
            data_files = list(sorted(data_dir.glob("historical_*.json")))
            if data_files:
                result = self._load_from_json(data_files[0])
            else:
                result = self._generate_synthetic_inflows()
        else:
            result = self._generate_synthetic_inflows()

        # Load real river flow data from CSV files
        river_flows = self._load_river_flows(csv_dir)
        if river_flows is not None:
            result["river_flows"] = river_flows["flows"]
            result["river_flow_years"] = river_flows["years"]
            result["river_flow_months"] = river_flows["months"]

        return result

    def _parse_level_csv(self, csv_path: Path) -> Optional[Dict[int, np.ndarray]]:
        """Parse a lake water level CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Dict mapping year -> 12-element array of monthly levels (meters), or None
        """
        import csv

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            if row and row[0].strip() == 'Year':
                header_idx = i
                break

        if header_idx is None:
            return None

        year_levels = {}
        for row in rows[header_idx + 1:]:
            if not row or not row[0].strip():
                continue
            try:
                year = int(row[0].strip())
                if 1990 <= year <= 2030:
                    levels = []
                    for col_idx in range(1, 13):
                        if col_idx < len(row):
                            val_str = row[col_idx].strip()
                            if val_str and val_str != '---':
                                try:
                                    levels.append(float(val_str))
                                except ValueError:
                                    levels.append(np.nan)
                            else:
                                levels.append(np.nan)
                        else:
                            levels.append(np.nan)
                    if len(levels) == 12:
                        year_levels[year] = np.array(levels)
            except (ValueError, IndexError):
                continue

        return year_levels if year_levels else None

    def _derive_inflows_from_csv(self, csv_dir: Path) -> Optional[Dict[str, np.ndarray]]:
        """Derive real lake inflows from CSV water levels + river flows via mass balance.

        For each lake, computes net external inflow (precipitation + tributaries):
            Q_net_inflow = A * dH/dt + Q_outflow - Q_inflow_from_upstream

        Uses real river flow CSV data where available, hydraulic conductance model
        to fill gaps, and real lake water level CSVs for dH/dt.

        Args:
            csv_dir: Directory containing CSV files

        Returns:
            Dict with inflows, historical_levels, target_levels, etc. or None if data unavailable
        """
        import csv as csv_module

        # --- Step 1: Load lake water levels from CSV ---
        lake_csv_map = {
            "Superior": csv_dir / "Lake Superior.csv",
            "Michigan": csv_dir / "Lake Michigan and Lake Huron.csv",
            "Huron": csv_dir / "Lake Michigan and Lake Huron.csv",
            "Erie": csv_dir / "Lake Erie.csv",
            "Ontario": csv_dir / "Lake Ontario.csv",
        }

        all_year_levels: Dict[str, Dict[int, np.ndarray]] = {}
        for lake_name, path in lake_csv_map.items():
            if path.exists():
                yl = self._parse_level_csv(path)
                if yl:
                    all_year_levels[lake_name] = yl

        # Need at least Superior, Michigan/Huron, Erie, Ontario
        required = {"Superior", "Michigan", "Erie", "Ontario"}
        if not required.issubset(set(all_year_levels.keys())):
            return None

        # Find common years across all lakes
        common_years = set(all_year_levels["Superior"].keys())
        for lake in ["Michigan", "Erie", "Ontario"]:
            common_years &= set(all_year_levels[lake].keys())
        common_years = sorted(common_years)

        if len(common_years) < 2:
            return None

        # --- Step 2: Load river flow CSVs where available ---
        river_csv_map = {
            "StMarys": csv_dir / "St. Mary's River.csv",
            "Detroit": csv_dir / "Detroit River.csv",
            "Niagara": csv_dir / "Niagara River.csv",
            "StLawrence": csv_dir / "St. Lawrence River.csv",
        }

        river_year_flows: Dict[str, Dict[int, np.ndarray]] = {}
        for river_name, path in river_csv_map.items():
            if path.exists():
                parsed = self._parse_river_csv(path)
                if parsed is not None:
                    # Convert flat array to year -> monthly mapping
                    yf = {}
                    for i, year in enumerate(parsed["years"]):
                        start = i * 12
                        month_data = parsed["flows"][start:start + 12]
                        if len(month_data) == 12 and not np.all(np.isnan(month_data)):
                            yf[year] = month_data
                    if yf:
                        river_year_flows[river_name] = yf

        # --- Step 2b: Only keep years where ALL rivers have data (clean subset) ---
        # This avoids having to model missing river flow data entirely
        if river_year_flows:
            river_common_years = set.intersection(
                *[set(yf.keys()) for yf in river_year_flows.values()]
            )
            # Keep only years with both lake level AND river flow data
            common_years = sorted(set(common_years) & river_common_years)
            if len(common_years) < 2:
                return None

        # --- Step 3: Build arrays aligned by common years ---
        n_years = len(common_years)
        n_steps = n_years * 12
        n_lakes = len(LAKE_NAMES)

        # Build historical water levels array
        historical_levels = np.zeros((n_steps, n_lakes))
        lake_idx_map = {name: i for i, name in enumerate(LAKE_NAMES)}
        for lake_name, idx in lake_idx_map.items():
            src = lake_name if lake_name in all_year_levels else "Michigan"
            for yi, year in enumerate(common_years):
                if year in all_year_levels[src]:
                    historical_levels[yi * 12:(yi + 1) * 12, idx] = all_year_levels[src][year]

        # Build river flow arrays (m³/s), NaN for missing
        river_arrays: Dict[str, np.ndarray] = {}
        for river_name in ["StMarys", "Detroit", "Niagara", "StLawrence"]:
            arr = np.full(n_steps, np.nan)
            if river_name in river_year_flows:
                yf = river_year_flows[river_name]
                for yi, year in enumerate(common_years):
                    if year in yf:
                        arr[yi * 12:(yi + 1) * 12] = yf[year]
            river_arrays[river_name] = arr

        # Also save river flows for dynamics model
        # Keep NaN to indicate missing data - will be filled by conductance model
        river_flows_matrix = np.full((n_steps, 4), np.nan)
        river_flows_matrix[:, 0] = river_arrays["StMarys"]
        river_flows_matrix[:, 1] = river_arrays["Detroit"]
        river_flows_matrix[:, 2] = river_arrays["Niagara"]
        river_flows_matrix[:, 3] = river_arrays["StLawrence"]

        # --- Step 4: Derive inflows via mass balance ---
        # Hydraulic conductance for inter-lake flows (m³/s per meter)
        # Calibrated so that nominal level differences produce realistic flows:
        #   Superior(183) - Michigan(177) = 6m → 350*6 = 2100 m³/s (realistic for St. Mary's)
        #   Huron(176.5) - Erie(173.5) = 3m → 1800*3 = 5400 m³/s (realistic for St. Clair)
        #   Erie(173.5) - Ontario(74.2) = 99.3m → 60*99.3 ≈ 5960 m³/s (realistic for Niagara)
        K_SH = 350.0   # Superior -> Huron/Michigan
        K_HE = 1800.0  # Huron -> Erie
        K_EO = 60.0    # Erie -> Ontario

        seconds_per_month = 86400.0 * 30.0
        areas_m2 = SURFACE_AREAS * 1e6

        inflows = np.zeros((n_steps, n_lakes))

        for t in range(n_steps):
            # Get water levels (use previous month for derivative)
            if t == 0:
                continue  # Can't compute dH/dt for first month
            h = historical_levels[t]
            h_prev = historical_levels[t - 1]
            dh = h - h_prev  # meters per month

            # Inter-lake flows (m³/s): use real data where available, model otherwise
            # St. Mary's River: Superior -> Michigan/Huron
            if not np.isnan(river_arrays["StMarys"][t]):
                flow_SH = river_arrays["StMarys"][t]
            else:
                delta_SH = h_prev[0] - h_prev[1]
                flow_SH = K_SH * max(delta_SH, 0)

            # Detroit River: Huron -> Erie
            if not np.isnan(river_arrays["Detroit"][t]):
                flow_HE = river_arrays["Detroit"][t]
            else:
                delta_HE = h_prev[2] - h_prev[3]
                flow_HE = K_HE * max(delta_HE, 0)

            # Niagara River: Erie -> Ontario
            if not np.isnan(river_arrays["Niagara"][t]):
                flow_EO = river_arrays["Niagara"][t]
            else:
                delta_EO = h_prev[3] - h_prev[4]
                flow_EO = K_EO * max(delta_EO, 0)

            # Moses-Saunders outflow: Ontario -> Atlantic
            if not np.isnan(river_arrays["StLawrence"][t]):
                flow_SL = river_arrays["StLawrence"][t]
            else:
                flow_SL = 7500.0  # Approximate average

            # Mass balance: Q_in = A * dH/dt + Q_out - Q_upstream
            # Superior: inflow = A*dH/dt + Soo_outflow + flow_SH
            #   (Soo Locks are part of St. Mary's; we use total flow_SH as outflow)
            inflows[t, 0] = areas_m2[0] * dh[0] / seconds_per_month + flow_SH

            # Michigan & Huron (connected): receive Soo + St. Mary's, lose Detroit
            mich_huron_area = areas_m2[1] + areas_m2[2]
            mich_huron_dh = (dh[1] + dh[2]) / 2.0  # Average since they share level
            inflows[t, 1] = mich_huron_area * mich_huron_dh / seconds_per_month + flow_HE - flow_SH
            inflows[t, 2] = 0.0  # Huron shares Michigan's dynamics

            # Erie: receives Detroit, loses Niagara
            inflows[t, 3] = areas_m2[3] * dh[3] / seconds_per_month + flow_EO - flow_HE

            # Ontario: receives Niagara, loses St. Lawrence
            inflows[t, 4] = areas_m2[4] * dh[4] / seconds_per_month + flow_SL - flow_EO

        # Replace first month with second month (can't compute dH/dt for t=0)
        if n_steps > 1:
            inflows[0] = inflows[1]

        # Clip physically impossible negative inflows to small positive value
        inflows = np.maximum(inflows, 100.0)

        # Compute target levels (use last year average as backtesting target)
        target_levels = np.mean(historical_levels[-12:], axis=0)

        return {
            "inflows": inflows,
            "historical_levels": historical_levels,
            "target_levels": target_levels,
            "min_levels": LEVEL_RANGES[:, 0].copy(),
            "max_levels": LEVEL_RANGES[:, 1].copy(),
            "river_flows": river_flows_matrix,
            "data_source": "csv_mass_balance",
        }

    def _derive_inflows_from_levels(self, historical_levels: np.ndarray) -> np.ndarray:
        """Derive lake inflows from water level time series via mass balance.

        Uses hydraulic conductance model for inter-lake flows:
            Q_net_inflow = A * dH/dt + Q_outflow - Q_inflow_from_upstream

        Args:
            historical_levels: (n_steps, 5) array of monthly water levels (meters)

        Returns:
            (n_steps, 5) array of net external inflows (m³/s), clipped to >= 100
        """
        n_steps = historical_levels.shape[0]
        areas_m2 = SURFACE_AREAS * 1e6
        seconds_per_month = 86400.0 * 30.0

        # Hydraulic conductance (m³/s per meter of level difference)
        K_SH = 350.0    # Superior -> Huron/Michigan
        K_HE = 1800.0   # Huron -> Erie
        K_EO = 60.0     # Erie -> Ontario

        inflows = np.zeros((n_steps, len(LAKE_NAMES)))

        for t in range(n_steps):
            # Use backward difference; for t=0 use forward
            if t == 0:
                h = historical_levels[1] if n_steps > 1 else historical_levels[0]
                h_prev = historical_levels[0]
            else:
                h = historical_levels[t]
                h_prev = historical_levels[t - 1]
            dh = h - h_prev

            # Inter-lake flows from hydraulic conductance (m³/s)
            flow_SH = K_SH * max(h_prev[0] - h_prev[1], 0)
            flow_HE = K_HE * max(h_prev[2] - h_prev[3], 0)
            flow_EO = K_EO * max(h_prev[3] - h_prev[4], 0)
            flow_SL = 7500.0  # Approximate Moses-Saunders average

            # Mass balance: Q_in = A * dH/dt + Q_out - Q_upstream
            inflows[t, 0] = areas_m2[0] * dh[0] / seconds_per_month + flow_SH
            mich_huron_area = areas_m2[1] + areas_m2[2]
            mich_huron_dh = (dh[1] + dh[2]) / 2.0
            inflows[t, 1] = mich_huron_area * mich_huron_dh / seconds_per_month + flow_HE - flow_SH
            inflows[t, 2] = 0.0  # Huron shares Michigan's dynamics
            inflows[t, 3] = areas_m2[3] * dh[3] / seconds_per_month + flow_EO - flow_HE
            inflows[t, 4] = areas_m2[4] * dh[4] / seconds_per_month + flow_SL - flow_EO

        inflows = np.maximum(inflows, 100.0)
        return inflows

    def _load_river_flows(self, csv_dir: Path) -> Optional[Dict[str, np.ndarray]]:
        """Load real river flow data from CSV files.

        Loads flow data for key inter-lake rivers:
        - St. Mary's River: Superior -> Huron/Michigan (Soo Locks area)
        - Detroit River: Huron -> Erie (via Lake St. Clair)
        - Niagara River: Erie -> Ontario
        - St. Lawrence River: Ontario -> Atlantic

        Args:
            csv_dir: Directory containing CSV files

        Returns:
            Dict with 'flows' (n_months x 4 array), 'years', 'months' or None if no data
        """
        river_files = {
            "St. Mary's River": csv_dir / "St. Mary's River.csv",
            "Detroit River": csv_dir / "Detroit River.csv",
            "Niagara River": csv_dir / "Niagara River.csv",
            "St. Lawrence River": csv_dir / "St. Lawrence River.csv",
        }

        river_data = {}
        for name, path in river_files.items():
            if path.exists():
                try:
                    data = self._parse_river_csv(path)
                    if data is not None:
                        river_data[name] = data
                except Exception as e:
                    print(f"Warning: Could not load {name} data: {e}")

        if not river_data:
            return None

        # Find common year range
        all_years = set()
        for data in river_data.values():
            all_years.update(data["years"])

        if not all_years:
            return None

        # Use years where at least 3 rivers have data
        year_counts = {}
        for year in all_years:
            count = sum(1 for data in river_data.values() if year in data["years"])
            year_counts[year] = count

        valid_years = sorted([y for y, c in year_counts.items() if c >= 3])

        if not valid_years:
            return None

        # Build flows array (n_months x 4 rivers)
        # Order: St. Mary's, Detroit, Niagara, St. Lawrence
        n_months = len(valid_years) * 12
        flows = np.zeros((n_months, 4))
        river_order = ["St. Mary's River", "Detroit River", "Niagara River", "St. Lawrence River"]

        for river_idx, river_name in enumerate(river_order):
            if river_name in river_data:
                data = river_data[river_name]
                for year_idx, year in enumerate(valid_years):
                    if year in data["years"]:
                        year_pos = data["years"].index(year)
                        for month in range(12):
                            src_idx = year_pos * 12 + month
                            dst_idx = year_idx * 12 + month
                            if src_idx < len(data["flows"]):
                                flows[dst_idx, river_idx] = data["flows"][src_idx]

        # Fill missing values with interpolation
        for river_idx in range(4):
            col = flows[:, river_idx]
            # Replace zeros with NaN for interpolation
            col[col == 0] = np.nan
            # Forward fill then backward fill
            mask = np.isnan(col)
            if mask.any():
                # Use mean of non-NaN values as fallback
                mean_val = np.nanmean(col) if not all(mask) else 0
                col[mask] = mean_val
                flows[:, river_idx] = col

        return {
            "flows": flows,
            "years": valid_years,
            "months": list(range(1, 13)) * len(valid_years),
        }

    def _parse_river_csv(self, csv_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a river flow CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Dict with 'flows' (1D array), 'years' (list) or None
        """
        import csv

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if len(rows) < 8:
            return None

        # Find header row (Year, Jan, Feb, ...)
        header_idx = None
        for i, row in enumerate(rows):
            if row and row[0].strip() == 'Year':
                header_idx = i
                break

        if header_idx is None:
            return None

        # Parse data rows
        years = []
        flows = []
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        for row in rows[header_idx + 1:]:
            if not row or not row[0].strip():
                continue

            try:
                year = int(row[0].strip())
                if 1990 <= year <= 2030:
                    year_flows = []
                    for month_idx in range(12):
                        col_idx = month_idx + 1
                        if col_idx < len(row):
                            val_str = row[col_idx].strip()
                            if val_str and val_str != '---':
                                try:
                                    year_flows.append(float(val_str))
                                except ValueError:
                                    year_flows.append(np.nan)
                            else:
                                year_flows.append(np.nan)
                        else:
                            year_flows.append(np.nan)

                    if len(year_flows) == 12:
                        years.append(year)
                        flows.extend(year_flows)
            except (ValueError, IndexError):
                continue

        if not years:
            return None

        return {
            "flows": np.array(flows),
            "years": years,
        }

    def _load_from_json(self, json_path: Path) -> Dict[str, np.ndarray]:
        """Load real historical data from a JSON file.

        Supports two formats:
        1. Simple format (historical_2017.json): monthly_inflows, targets, min_levels, max_levels
        2. Excel export format (great_lakes_data.json): sheets with raw data including headers

        Args:
            json_path: Path to JSON file

        Returns:
            Dict with inflow data and target levels
        """
        with open(json_path) as fp:
            d = json.load(fp)

        # Detect format
        if "monthly_inflows" in d:
            # Simple format (historical_2017.json)
            return self._load_simple_format(d, json_path)
        else:
            # Excel export format (great_lakes_data.json)
            return self._load_excel_format(d, json_path)

    def _load_simple_format(self, d: Dict, json_path: Path) -> Dict[str, np.ndarray]:
        """Load from simple JSON format with monthly_inflows key."""
        monthly = d.get("monthly_inflows", {})
        n_lakes = len(LAKE_NAMES)
        n_steps = len(next(iter(monthly.values()), [])) if monthly else 12

        inflows_array = np.zeros((n_steps, n_lakes))
        for i, lake in enumerate(LAKE_NAMES):
            if lake in monthly:
                inflows_array[:, i] = monthly[lake][:n_steps]
            else:
                print(f"[WARNING] Lake '{lake}' not found in JSON inflows — using hardcoded defaults!")
                inflows_array[:, i] = [1500, 1800, 2200, 2800, 3500, 4200,
                                       4500, 4200, 3600, 2900, 2200, 1700][:n_steps]

        targets = d.get("targets", {})
        target_levels = np.array([targets.get(lake, NOMINAL_LEVELS[i]) for i, lake in enumerate(LAKE_NAMES)])

        return {
            "inflows": inflows_array,
            "historical_levels": None,
            "target_levels": target_levels,
            "min_levels": np.array([d.get("min_levels", {}).get(lake, LEVEL_RANGES[i, 0]) for i, lake in enumerate(LAKE_NAMES)]),
            "max_levels": np.array([d.get("max_levels", {}).get(lake, LEVEL_RANGES[i, 1]) for i, lake in enumerate(LAKE_NAMES)]),
            "data_source": str(json_path),
        }

    def _load_excel_format(self, d: Dict, json_path: Path) -> Dict[str, np.ndarray]:
        """Load from Excel export format (great_lakes_data.json).

        The JSON contains HISTORICAL WATER LEVELS (meters), NOT inflows.
        We:
        1. Parse historical water levels for reference/backtesting
        2. Generate synthetic but realistic inflows (m³/s) for simulation
        3. Extract 2017 target levels for backtesting

        Supports two column naming formats:
        1. Original: 'Lake Superior - Mean Water Level', 'Unnamed: 1', ...
        2. Cleaned: 'Year', 'Jan', 'Feb', 'Mar', ...
        """
        # Map sheet names to lake names
        sheet_to_lake = {
            "Lake Superior": "Superior",
            "Lake Michigan and Lake Huron": "Michigan",  # Michigan and Huron share the same data
            "Lake Erie": "Erie",
            "Lake Ontario": "Ontario",
        }

        # Parse historical water level data from each lake sheet
        all_lake_levels = {}
        for sheet_name, lake_name in sheet_to_lake.items():
            if sheet_name not in d:
                continue

            sheet_data = d[sheet_name]["data"]

            if sheet_data and len(sheet_data) > 0:
                first_row = sheet_data[0]
                keys = list(first_row.keys())

                # Format 1: Original with 'Unnamed: N' columns
                if any('Unnamed' in k for k in keys):
                    monthly_levels = []
                    for row in sheet_data[6:]:
                        try:
                            year = int(row.get(keys[0], 0))
                            if 1990 <= year <= 2030:
                                levels = [float(row.get(f"Unnamed: {i}", 0)) for i in range(1, 13)]
                                monthly_levels.extend(levels)
                        except (ValueError, TypeError):
                            continue

                # Format 2: Cleaned with 'Year', 'Jan', 'Feb', ... columns
                elif 'Year' in keys and 'Jan' in keys:
                    monthly_levels = []
                    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    for row in sheet_data:
                        try:
                            year = int(row.get('Year', 0))
                            if 1990 <= year <= 2030:
                                levels = [float(row.get(m, 0)) for m in months]
                                monthly_levels.extend(levels)
                        except (ValueError, TypeError):
                            continue
                else:
                    continue

                if monthly_levels:
                    all_lake_levels[lake_name] = monthly_levels

        if not all_lake_levels:
            return self._generate_synthetic_inflows()

        # Build historical levels array (for backtesting reference)
        n_lakes = len(LAKE_NAMES)
        n_steps = min(len(v) for v in all_lake_levels.values())
        historical_levels = np.zeros((n_steps, n_lakes))
        for i, lake in enumerate(LAKE_NAMES):
            if lake in all_lake_levels:
                historical_levels[:, i] = all_lake_levels[lake][:n_steps]
            elif lake == "Huron" and "Michigan" in all_lake_levels:
                historical_levels[:, i] = all_lake_levels["Michigan"][:n_steps]

        # Derive inflows from historical water levels via mass balance
        # (same physics as _derive_inflows_from_csv, but no river flow CSVs here)
        inflows_array = self._derive_inflows_from_levels(historical_levels)

        # Extract 2017 target levels for backtesting
        target_levels = NOMINAL_LEVELS.copy()
        for sheet_name, lake_name in sheet_to_lake.items():
            if sheet_name not in d:
                continue

            sheet_data = d[sheet_name]["data"]
            if not sheet_data:
                continue

            first_row = sheet_data[0]
            keys = list(first_row.keys())
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            for row in sheet_data:
                try:
                    if 'Year' in keys:
                        year = int(row.get('Year', 0))
                    else:
                        year = int(row.get(keys[0], 0))

                    if year == 2017:
                        if 'Year' in keys and 'Jan' in keys:
                            levels_2017 = [float(row.get(m, 0)) for m in months]
                        else:
                            levels_2017 = [float(row.get(f"Unnamed: {i}", 0)) for i in range(1, 13)]

                        avg_level_2017 = np.mean(levels_2017)
                        lake_idx = LAKE_NAMES.index(lake_name)
                        target_levels[lake_idx] = avg_level_2017
                        if lake_name == "Michigan":
                            huron_idx = LAKE_NAMES.index("Huron")
                            target_levels[huron_idx] = avg_level_2017
                        break
                except (ValueError, TypeError, IndexError):
                    continue

        return {
            "inflows": inflows_array,
            "historical_levels": historical_levels,
            "target_levels": target_levels,
            "min_levels": LEVEL_RANGES[:, 0].copy(),
            "max_levels": LEVEL_RANGES[:, 1].copy(),
            "data_source": str(json_path),
        }

    def _generate_synthetic_inflows(self) -> Dict[str, np.ndarray]:
        """Generate synthetic inflow patterns (m³/s) as LAST RESORT fallback.

        WARNING: This produces fabricated data. Ensure CSV or JSON data files
        exist under data/ to avoid using this path.
        """
        import warnings
        warnings.warn(
            "No real data files found (CSV or JSON). Falling back to SYNTHETIC inflows. "
            "Place lake level CSVs under data/ or great_lakes_data.json under data/train/.",
            stacklevel=2,
        )
        print("[WARNING] Using SYNTHETIC inflow data — no real data files found!")

        n = self.n_timesteps
        base_inflows = np.array([2500, 4500, 4500, 2500, 3500])
        seasonal = 0.3 * np.sin(2 * np.pi * np.arange(n) / 12) + 1.0
        np.random.seed(42)
        noise = np.random.lognormal(0, 0.1, (n, 5))
        inflows = base_inflows[np.newaxis, :] * seasonal[:, np.newaxis] * noise

        return {
            "inflows": inflows,
            "historical_levels": None,
            "target_levels": NOMINAL_LEVELS.copy(),
            "min_levels": LEVEL_RANGES[:, 0].copy(),
            "max_levels": LEVEL_RANGES[:, 1].copy(),
        }

    def _parse_genotype(self, genotype: Dict[str, str]) -> Dict[str, str]:
        """Parse and validate genotype against gene space."""
        parsed = {}
        for locus in GENE_SPACE.keys():
            allele = genotype.get(locus)
            if allele is None:
                # Default to first allele if not specified
                allele = GENE_SPACE[locus][0]
            elif allele not in GENE_SPACE[locus]:
                # L3 meta-learner may have proposed NEW alleles!
                # We accept them - this is how search space expands
                pass
            parsed[locus] = allele
        return parsed

    async def evaluate(self, cfg: EvalContext) -> EvaluationResult:
        """
        Evaluate a modeling methodology (genotype) on the Great Lakes problem.

        Args:
            cfg: Evaluation context - genotype is loaded from the code file
                 at project_root, which the planner generates

        Returns:
            EvaluationResult with fitness and all objective metrics
        """
        import time
        import importlib.util
        import sys

        start_time = time.time()

        try:
            # Load genotype from the worktree - the planner generates a genotype.py file
            genotype_path = Path(cfg.project_root) / "genotype.py"
            if genotype_path.exists():
                # Import genotype from generated code
                spec = importlib.util.spec_from_file_location("genotype", genotype_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules["genotype"] = module
                spec.loader.exec_module(module)
                genotype = module.GENOTYPE
            else:
                # Fallback to default genotype for testing
                genotype = {
                    "dynamics": "stochastic_inflow",
                    "constraints": "soft_penalty",
                    "objective_form": "chebyshev",
                    "stakeholders": "full_6",
                    "solver": "linear_program",
                    "temporal": "seasonal_peak",
                    "robustness": "deterministic",
                    "coupling": "entropy_weight",
                }

            # Parse genotype into modeling choices
            choices = self._parse_genotype(genotype)

            # Get inflow data
            inflows = self.historical_data["inflows"]

            # Determine timesteps from temporal architecture choice
            if choices["temporal"] == "annual_monthly":
                n_steps = 12
            elif choices["temporal"] == "seasonal_peak":
                n_steps = 24  # 2 years, focus on peak seasons
            elif choices["temporal"] == "multi_year":
                n_steps = 60
            else:  # event_triggered
                n_steps = 36

            # Repeat inflow data if n_steps exceeds length (seasonal pattern repeats)
            if len(inflows) < n_steps:
                repeats = (n_steps // len(inflows)) + 1
                inflows = np.tile(inflows, (repeats, 1))
            inflows = inflows[:n_steps]

            # Run simulation with this modeling methodology
            metrics = self._run_simulation(choices, inflows, n_steps)

            duration_ms = (time.time() - start_time) * 1000

            return EvaluationResult(
                score=metrics["overall_fitness"],
                metrics=metrics,
                monitor_metrics=metrics,
                duration_ms=duration_ms,
                success=True,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return EvaluationResult(
                score=0.0,
                metrics={},
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
            )

    def _run_simulation(
        self,
        choices: Dict[str, str],
        inflows: np.ndarray,
        n_steps: int,
    ) -> Dict[str, float]:
        """Run full Great Lakes simulation with specified modeling methodology."""
        n_lakes = len(LAKE_NAMES)
        n_dams = len(DAM_NAMES)

        # Get real river flow data if available
        river_flows = self.historical_data.get("river_flows")

        # Reset flow delay state for each simulation run
        self._prev_deltas = None

        # Initialize state
        water_levels = np.zeros((n_steps, n_lakes))
        water_levels[0] = NOMINAL_LEVELS.copy()
        dam_flows = np.zeros((n_steps, n_dams))
        constraint_violations = 0.0

        # Run simulation
        for t in range(1, n_steps):
            # Get control action based on solver choice
            dam_flows[t] = self._compute_control(
                water_levels[t-1], t, inflows[t], choices,
                full_inflows=inflows,
            )

            # Apply constraints and compute violation
            dam_flows[t], violation = self._apply_constraints(
                dam_flows[t], choices
            )
            constraint_violations += violation

            # Update water levels based on dynamics choice
            water_levels[t] = self._update_dynamics(
                water_levels[t-1], dam_flows[t], inflows[t], t, choices,
                river_flows=river_flows
            )

            # Check water level constraint
            level_violation = self._check_level_constraints(water_levels[t])
            constraint_violations += level_violation

        # ===== PROBLEM REQUIREMENT 11: 2017 Backtesting Deviation =====
        # "would your new controls result in satisfactory or better than the actual recorded water levels"
        historical_levels = self.historical_data.get("historical_levels")
        target_levels = self.historical_data["target_levels"]
        ontario_idx = LAKE_NAMES.index("Ontario")

        if historical_levels is not None and len(historical_levels) >= n_steps:
            # Compare against actual historical trajectory
            ref = historical_levels[:n_steps]
            final_deviation = np.mean(np.abs(water_levels - ref))
            ontario_deviation = np.mean(np.abs(water_levels[:, ontario_idx] - ref[:, ontario_idx]))
        else:
            # Fallback: compare last 12 months against 2017 target
            final_deviation = np.mean(np.abs(water_levels[-12:, :] - target_levels))
            ontario_deviation = np.mean(np.abs(water_levels[-12:, ontario_idx] - target_levels[ontario_idx]))

        backtesting_deviation = 0.5 * final_deviation + 0.5 * ontario_deviation

        # ===== PROBLEM REQUIREMENT 12: Sensitivity Analysis =====
        # "How sensitive is your algorithm to changes in environmental conditions"
        sensitivity_score = self._compute_sensitivity(choices, inflows, n_steps, water_levels)

        # Compute stakeholder objectives based on objective_form choice
        objectives, n_active = self._compute_objectives(
            water_levels, dam_flows, choices
        )

        # Compute overall fitness using coupling method
        overall_fitness = self._compute_fitness(
            objectives, n_active, constraint_violations, backtesting_deviation, sensitivity_score, choices
        )

        # Build result
        result = {
            "overall_fitness": overall_fitness,
            "constraint_satisfaction": 1.0 / (1.0 + constraint_violations / n_steps),
            "backtesting_deviation": float(backtesting_deviation),
            "sensitivity_score": float(sensitivity_score),
        }
        result.update(objectives)

        return result

    def _compute_control(
        self,
        levels: np.ndarray,
        t: int,
        inflow: np.ndarray,
        choices: Dict[str, str],
        full_inflows: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute dam flows based on solver choice.

        CRITICAL: Each solver MUST have a distinct implementation.
        LLM4AD evolves METHODOLOGIES - not just parameters.
        If LLM chooses "particle_swarm", we MUST run actual PSO.

        Args:
            full_inflows: Full inflow array (n_steps, 5) for look-ahead in MPC.
                          If None, MPC uses repeated last-known inflow.
        """
        solver = choices["solver"]
        min_flow = DAM_FLOW_RANGES[:, 0]
        max_flow = DAM_FLOW_RANGES[:, 1]

        # ============================================
        # SOLVER 1: NSGA-II - Multi-objective GA
        # ============================================
        if solver == "nsga2":
            # NSGA-II: population-based multi-objective optimization with
            # non-dominated sorting and crowding distance.
            # Objectives: (1) minimize level deviation, (2) maximize hydropower
            errors = levels - NOMINAL_LEVELS
            seconds_per_month = 86400.0 * 30.0

            def _nsga2_cost(f_SS, f_MS):
                """Evaluate a candidate: returns (level_deviation, neg_hydropower)."""
                pred_SS = levels[0] + (inflow[0] - f_SS) / (SURFACE_AREAS[0] * 1e6) * seconds_per_month
                pred_MS = levels[4] + (inflow[4] - f_MS) / (SURFACE_AREAS[4] * 1e6) * seconds_per_month
                obj1 = (pred_SS - NOMINAL_LEVELS[0]) ** 2 + (pred_MS - NOMINAL_LEVELS[4]) ** 2
                # Hydropower: higher flow = more power, but prefer balanced
                obj2 = -((f_SS - min_flow[0]) / (max_flow[0] - min_flow[0])
                         + (f_MS - min_flow[1]) / (max_flow[1] - min_flow[1])) * 0.5
                return obj1, obj2

            def _fast_non_dominated_sort(pop_objs):
                """Return list of fronts, each front is a list of indices."""
                n = len(pop_objs)
                domination_count = [0] * n
                dominated_set = [[] for _ in range(n)]
                fronts = [[]]
                for p in range(n):
                    for q in range(n):
                        if p == q:
                            continue
                        # p dominates q if all objectives <= and at least one <
                        if (pop_objs[p][0] <= pop_objs[q][0] and pop_objs[p][1] <= pop_objs[q][1]
                                and (pop_objs[p][0] < pop_objs[q][0] or pop_objs[p][1] < pop_objs[q][1])):
                            dominated_set[p].append(q)
                        elif (pop_objs[q][0] <= pop_objs[p][0] and pop_objs[q][1] <= pop_objs[p][1]
                              and (pop_objs[q][0] < pop_objs[p][0] or pop_objs[q][1] < pop_objs[p][1])):
                            domination_count[p] += 1
                    if domination_count[p] == 0:
                        fronts[0].append(p)
                i = 0
                while fronts[i]:
                    next_front = []
                    for p in fronts[i]:
                        for q in dominated_set[p]:
                            domination_count[q] -= 1
                            if domination_count[q] == 0:
                                next_front.append(q)
                    i += 1
                    fronts.append(next_front)
                return [f for f in fronts if f]

            def _crowding_distance(front_indices, pop_objs):
                """Compute crowding distance for a front."""
                n = len(front_indices)
                if n <= 2:
                    return {idx: np.inf for idx in front_indices}
                distances = {idx: 0.0 for idx in front_indices}
                for obj_idx in range(2):
                    sorted_idx = sorted(front_indices, key=lambda i: pop_objs[i][obj_idx])
                    distances[sorted_idx[0]] = np.inf
                    distances[sorted_idx[-1]] = np.inf
                    obj_range = pop_objs[sorted_idx[-1]][obj_idx] - pop_objs[sorted_idx[0]][obj_idx]
                    if obj_range < 1e-12:
                        continue
                    for k in range(1, n - 1):
                        distances[sorted_idx[k]] += (
                            (pop_objs[sorted_idx[k + 1]][obj_idx] - pop_objs[sorted_idx[k - 1]][obj_idx])
                            / obj_range
                        )
                return distances

            # Initialize population
            pop_size = 16
            n_generations = 6
            population = np.random.uniform(
                low=[min_flow[0], min_flow[1]],
                high=[max_flow[0], max_flow[1]],
                size=(pop_size, 2),
            )
            # Seed with proportional controller baseline
            population[0] = [2000.0 + errors[0] * 500.0, 8000.0 + errors[4] * 800.0]
            population[0] = np.clip(population[0], [min_flow[0], min_flow[1]], [max_flow[0], max_flow[1]])

            for gen in range(n_generations):
                # Evaluate
                pop_objs = [_nsga2_cost(ind[0], ind[1]) for ind in population]

                # Generate offspring via SBX crossover + polynomial mutation
                offspring = []
                for _ in range(pop_size):
                    i, j = np.random.choice(pop_size, 2, replace=False)
                    # SBX crossover
                    eta_c = 20.0
                    u = np.random.rand(2)
                    beta = np.where(u <= 0.5,
                                    (2.0 * u) ** (1.0 / (eta_c + 1.0)),
                                    (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta_c + 1.0)))
                    child = 0.5 * ((1 + beta) * population[i] + (1 - beta) * population[j])
                    # Polynomial mutation
                    eta_m = 20.0
                    for d in range(2):
                        if np.random.rand() < 0.3:
                            delta = np.random.rand()
                            if delta < 0.5:
                                child[d] += (2.0 * delta) ** (1.0 / (eta_m + 1.0)) - 1.0
                            else:
                                child[d] += 1.0 - (2.0 * (1.0 - delta)) ** (1.0 / (eta_m + 1.0))
                    child = np.clip(child, [min_flow[0], min_flow[1]], [max_flow[0], max_flow[1]])
                    offspring.append(child)

                # Combine parent + offspring
                combined = np.vstack([population, offspring])
                combined_objs = [_nsga2_cost(ind[0], ind[1]) for ind in combined]

                # Non-dominated sorting + crowding distance selection
                fronts = _fast_non_dominated_sort(combined_objs)
                new_pop = []
                for front in fronts:
                    if len(new_pop) + len(front) <= pop_size:
                        new_pop.extend(front)
                    else:
                        remaining = pop_size - len(new_pop)
                        cd = _crowding_distance(front, combined_objs)
                        sorted_front = sorted(front, key=lambda i: cd[i], reverse=True)
                        new_pop.extend(sorted_front[:remaining])
                        break
                population = combined[new_pop]

            # Select best from final Pareto front (preference: level deviation)
            final_objs = [_nsga2_cost(ind[0], ind[1]) for ind in population]
            # Weighted scalarization: 70% level deviation, 30% hydropower
            obj1_vals = np.array([o[0] for o in final_objs])
            obj2_vals = np.array([o[1] for o in final_objs])
            obj1_norm = (obj1_vals - obj1_vals.min()) / max(obj1_vals.max() - obj1_vals.min(), 1e-8)
            obj2_norm = (obj2_vals - obj2_vals.min()) / max(obj2_vals.max() - obj2_vals.min(), 1e-8)
            scalar = 0.7 * obj1_norm + 0.3 * obj2_norm
            best_idx = int(np.argmin(scalar))
            flow_SS, flow_MS = float(population[best_idx][0]), float(population[best_idx][1])

        # ============================================
        # SOLVER 2: MPC - Rolling Horizon Optimal Control
        # ============================================
        elif solver == "mpc_rolling":
            # Full 5-lake MPC: simulates all lakes over a look-ahead horizon
            # with inter-lake hydraulic conductance, then picks the dam flows
            # that minimize cumulative deviation across ALL lakes.
            errors = levels - NOMINAL_LEVELS
            seconds_per_month = 86400.0 * 30.0
            areas_m2 = SURFACE_AREAS * 1e6

            # Hydraulic conductance (same as in dynamics model)
            K_SH, K_HE, K_EO = 350.0, 1800.0, 60.0

            def _mpc_simulate(pred_levels, f_SS, f_MS, inflow_step):
                """Advance one MPC step for all 5 lakes."""
                soo_out = f_SS * seconds_per_month
                moses_out = f_MS * seconds_per_month
                flow_SH = K_SH * max(pred_levels[0] - pred_levels[1], 0) * seconds_per_month
                flow_HE = K_HE * max(pred_levels[2] - pred_levels[3], 0) * seconds_per_month
                flow_EO = K_EO * max(pred_levels[3] - pred_levels[4], 0) * seconds_per_month

                new = pred_levels.copy()
                new[0] += (inflow_step[0] * seconds_per_month - soo_out - flow_SH) / areas_m2[0]
                mh_net = (inflow_step[1] + inflow_step[2]) * seconds_per_month + soo_out + flow_SH - flow_HE
                new[1] += mh_net / (areas_m2[1] + areas_m2[2])
                new[2] += mh_net / (areas_m2[1] + areas_m2[2])
                new[3] += (inflow_step[3] * seconds_per_month + flow_HE - flow_EO) / areas_m2[3]
                new[4] += (inflow_step[4] * seconds_per_month + flow_EO - moses_out) / areas_m2[4]
                return new

            # Grid search over gains, evaluating full 5-lake trajectory
            gains_SS = np.linspace(300, 900, 7)
            gains_MS = np.linspace(600, 1500, 7)
            horizon = 3
            best_score = np.inf
            best_g_SS, best_g_MS = 500.0, 800.0

            for g_SS in gains_SS:
                for g_MS in gains_MS:
                    pred_error = 0.0
                    pred_levels = levels.copy()
                    for h in range(horizon):
                        f_SS = 2000.0 + errors[0] * g_SS
                        f_MS = 8000.0 + errors[4] * g_MS
                        f_SS = np.clip(f_SS, min_flow[0], max_flow[0])
                        f_MS = np.clip(f_MS, min_flow[1], max_flow[1])
                        # Use repeated inflow pattern for look-ahead
                        ah = t + h
                        if full_inflows is not None and ah < len(full_inflows):
                            inflow_step = full_inflows[ah]
                        else:
                            inflow_step = inflow  # inflow is already inflows[t], a 5-element array
                        pred_levels = _mpc_simulate(pred_levels, f_SS, f_MS, inflow_step)
                        pred_error += np.sum((pred_levels - NOMINAL_LEVELS) ** 2)

                    if pred_error < best_score:
                        best_score = pred_error
                        best_g_SS, best_g_MS = g_SS, g_MS

            flow_SS = 2000.0 + errors[0] * best_g_SS
            flow_MS = 8000.0 + errors[4] * best_g_MS
            flow_SS = np.clip(flow_SS, min_flow[0], max_flow[0])
            flow_MS = np.clip(flow_MS, min_flow[1], max_flow[1])

        # ============================================
        # SOLVER 3: Linear Programming - Convex Opt
        # ============================================
        elif solver == "linear_program":
            # Formulate as QP: minimize ||level - nominal|| subject to flow bounds
            # Closed form solution for 1D constrained linear system
            errors = levels - NOMINAL_LEVELS

            # Analytical solution: push towards nominal, saturated at bounds
            desired_flow_SS = 2000.0 + errors[0] * 800.0  # Aggressive LP
            desired_flow_MS = 8000.0 + errors[4] * 1200.0

            # Enforce flow bounds exactly (true LP constraint satisfaction)
            flow_SS = np.clip(desired_flow_SS, min_flow[0], max_flow[0])
            flow_MS = np.clip(desired_flow_MS, min_flow[1], max_flow[1])

        # ============================================
        # SOLVER 4: Particle Swarm Optimization
        # ============================================
        elif solver == "particle_swarm":
            # Run a tiny PSO (8 particles, 5 iterations) at each timestep
            # This IS actual PSO - not just a coefficient change!
            errors = levels - NOMINAL_LEVELS

            # PSO over (flow_SS, flow_MS) to minimize level deviation
            n_particles = 8
            n_iterations = 5

            # Initialize particles around baseline
            particles = np.random.uniform(
                low=[min_flow[0], min_flow[1]],
                high=[max_flow[0], max_flow[1]],
                size=(n_particles, 2)
            )
            velocities = np.zeros((n_particles, 2))
            personal_best = particles.copy()
            personal_best_cost = np.inf * np.ones(n_particles)
            global_best = np.array([2000.0 + errors[0] * 500, 8000.0 + errors[4] * 800])

            for _ in range(n_iterations):
                # Evaluate each particle
                for i in range(n_particles):
                    f_SS, f_MS = particles[i]
                    pred_SS = levels[0] + (inflow[0] - f_SS) / (SURFACE_AREAS[0] * 1e6) * 86400.0 * 30.0
                    pred_MS = levels[4] + (inflow[4] - f_MS) / (SURFACE_AREAS[4] * 1e6) * 86400.0 * 30.0
                    cost = (pred_SS - NOMINAL_LEVELS[0]) ** 2 + (pred_MS - NOMINAL_LEVELS[4]) ** 2

                    if cost < personal_best_cost[i]:
                        personal_best_cost[i] = cost
                        personal_best[i] = particles[i]

                global_best = personal_best[np.argmin(personal_best_cost)]

                # PSO velocity update (per-particle random coefficients)
                w, c1, c2 = 0.5, 1.0, 1.0
                r1 = np.random.rand(n_particles, 2)
                r2 = np.random.rand(n_particles, 2)
                velocities = w * velocities + c1 * r1 * (personal_best - particles) + c2 * r2 * (global_best - particles)
                particles += velocities
                particles = np.clip(particles, [min_flow[0], min_flow[1]], [max_flow[0], max_flow[1]])

            flow_SS, flow_MS = global_best

        # ============================================
        # SOLVER 5: Bayesian Optimization - Sample-Efficient
        # ============================================
        elif solver == "bayesian_opt":
            # Lightweight BO with RBF-kernel GP surrogate + Expected Improvement.
            # Maintains a history of (x, cost) observations and uses a GP posterior
            # to guide the next sample toward regions of low predicted cost (exploitation)
            # with high uncertainty (exploration).
            errors = levels - NOMINAL_LEVELS

            # Evaluation function: predict level deviation for candidate (f_SS, f_MS)
            def _bo_cost(f_SS, f_MS):
                pred_SS = levels[0] + (inflow[0] - f_SS) / (SURFACE_AREAS[0] * 1e6) * 86400.0 * 30.0
                pred_MS = levels[4] + (inflow[4] - f_MS) / (SURFACE_AREAS[4] * 1e6) * 86400.0 * 30.0
                return (pred_SS - NOMINAL_LEVELS[0]) ** 2 + (pred_MS - NOMINAL_LEVELS[4]) ** 2

            # Normalize inputs to [0, 1] for stable GP kernel computation
            flow_lo = np.array([min_flow[0], min_flow[1]])
            flow_hi = np.array([max_flow[0], max_flow[1]])
            flow_range = flow_hi - flow_lo

            def _normalize(x):
                return (x - flow_lo) / flow_range

            def _denormalize(x_n):
                return x_n * flow_range + flow_lo

            # RBF kernel: k(x, x') = sigma_f^2 * exp(-0.5 * ||x - x'||^2 / l^2)
            length_scale = 0.3
            sigma_f = 1.0
            sigma_n = 1e-3  # Observation noise

            def _rbf_kernel(X1, X2):
                sq_dist = np.sum((X1[:, None, :] - X2[None, :, :]) ** 2, axis=2)
                return sigma_f ** 2 * np.exp(-0.5 * sq_dist / length_scale ** 2)

            # Seed observations: baseline + corners of search space
            baseline = np.array([
                2000.0 + errors[0] * 500.0,
                8000.0 + errors[4] * 800.0,
            ])
            seed_points = [baseline]
            # Add a few exploratory seed points spread across the space
            for frac_SS in [0.25, 0.75]:
                for frac_MS in [0.25, 0.75]:
                    seed_points.append(np.array([
                        min_flow[0] + frac_SS * (max_flow[0] - min_flow[0]),
                        min_flow[1] + frac_MS * (max_flow[1] - min_flow[1]),
                    ]))

            X_obs = []  # Observed points (normalized)
            y_obs = []  # Observed costs (normalized)
            for pt in seed_points:
                pt_c = np.clip(pt, flow_lo, flow_hi)
                cost = _bo_cost(pt_c[0], pt_c[1])
                X_obs.append(_normalize(pt_c))
                y_obs.append(cost)

            # BO iterations: use GP posterior + EI to pick next point
            n_bo_iters = 8
            from scipy.stats import norm as _norm

            for _ in range(n_bo_iters):
                X_arr = np.array(X_obs)
                y_arr = np.array(y_obs)

                # Normalize costs to zero-mean, unit-variance for stable GP
                y_mean, y_std = np.mean(y_arr), max(np.std(y_arr), 1e-8)
                y_norm = (y_arr - y_mean) / y_std

                # GP posterior: mu(x), sigma(x)
                K = _rbf_kernel(X_arr, X_arr) + sigma_n ** 2 * np.eye(len(X_arr))
                K_inv = np.linalg.inv(K)

                # Generate candidate points (grid + random)
                candidates = []
                n_grid = 6
                for i in range(n_grid):
                    for j in range(n_grid):
                        candidates.append(np.array([i / (n_grid - 1), j / (n_grid - 1)]))
                for _ in range(10):
                    candidates.append(np.random.rand(2))
                C = np.array(candidates)

                # Predict mean and std at candidates
                K_xX = _rbf_kernel(C, X_arr)
                K_xx = _rbf_kernel(C, C)
                mu = K_xX @ K_inv @ y_norm
                cov = np.diag(K_xx - K_xX @ K_inv @ K_xX.T)
                sigma = np.sqrt(np.maximum(cov, 0.0))

                # Expected Improvement acquisition
                y_best = np.min(y_norm)
                z = (y_best - mu) / np.maximum(sigma, 1e-8)
                ei = (y_best - mu) * _norm.cdf(z) + sigma * _norm.pdf(z)
                ei[sigma < 1e-6] = 0.0  # No exploration where fully known

                best_cand = C[np.argmax(ei)]
                best_cand = _denormalize(best_cand)
                best_cand = np.clip(best_cand, flow_lo, flow_hi)

                cost = _bo_cost(best_cand[0], best_cand[1])
                X_obs.append(_normalize(best_cand))
                y_obs.append(cost)

            # Return the point with lowest observed cost
            best_idx = int(np.argmin(y_obs))
            best_pt = _denormalize(np.array(X_obs[best_idx]))
            best_pt = np.clip(best_pt, flow_lo, flow_hi)
            flow_SS, flow_MS = float(best_pt[0]), float(best_pt[1])

        else:
            # Fallback: simple proportional control
            errors = levels - NOMINAL_LEVELS
            flow_SS = 2000.0 + errors[0] * 500.0
            flow_MS = 8000.0 + errors[4] * 800.0

        return np.array([flow_SS, flow_MS])

    def _apply_constraints(
        self,
        flows: np.ndarray,
        choices: Dict[str, str],
    ) -> Tuple[np.ndarray, float]:
        """Apply dam flow constraints per constraint handling choice."""
        method = choices["constraints"]
        min_flow = DAM_FLOW_RANGES[:, 0]
        max_flow = DAM_FLOW_RANGES[:, 1]

        if method == "hard_clipping":
            clipped = np.clip(flows, min_flow, max_flow)
            violation = np.sum(np.abs(flows - clipped))
            return clipped, violation

        elif method == "soft_penalty":
            below = np.maximum(min_flow - flows, 0)
            above = np.maximum(flows - max_flow, 0)
            violation = 10.0 * np.sum(below + above)
            # Clamp to physical limits to prevent impossible water level changes
            clipped = np.clip(flows, min_flow, max_flow)
            return clipped, violation

        elif method == "barrier_function":
            # Log barrier: only penalize when approaching boundaries
            # Interior (feasible) flows get zero penalty
            below = np.maximum(min_flow - flows, 0)
            above = np.maximum(flows - max_flow, 0)
            # Barrier penalty: log distance to boundary (only for violations)
            dist_to_lower = np.maximum(flows - min_flow, 1e-6)
            dist_to_upper = np.maximum(max_flow - flows, 1e-6)
            # Only apply barrier when outside bounds or very close
            violation = np.sum(below + above) * 1000.0  # Hard penalty for actual violations
            # Add soft barrier for proximity to bounds (within 10% of range)
            flow_range = max_flow - min_flow
            proximity_penalty = np.sum(
                np.maximum(0.1 * flow_range - dist_to_lower, 0) +
                np.maximum(0.1 * flow_range - dist_to_upper, 0)
            ) * 10.0
            violation += proximity_penalty
            return flows, violation

        elif method == "leaky_constraint":
            # Allow small violation, heavy penalty
            tolerance = 0.05
            leak_min = min_flow * (1 - tolerance)
            leak_max = max_flow * (1 + tolerance)
            clipped = np.clip(flows, leak_min, leak_max)
            violation = np.sum(np.abs(flows - clipped)) * 100.0
            return clipped, violation

        else:
            return flows, 0.0

    def _update_dynamics(
        self,
        prev_levels: np.ndarray,
        flows: np.ndarray,
        inflow: np.ndarray,
        t: int,
        choices: Dict[str, str],
        river_flows: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Update water levels based on dynamics modeling choice.

        Physical model of Great Lakes connectivity:
        Superior -> (Soo Locks) -> Michigan/Huron -> Erie -> (Moses-Saunders) -> Ontario
        - flows[0] = Soo Locks outflow from Superior (m³/s)
        - flows[1] = Moses-Saunders outflow from Ontario (m³/s)
        - Inter-lake flows are driven by level differences (hydraulic conductance model)
        - If river_flows provided, use real historical data instead of computing

        Args:
            prev_levels: Previous water levels for all 5 lakes (meters)
            flows: Dam flows [Soo Locks, Moses-Saunders] (m³/s)
            inflow: External inflow for all 5 lakes (m³/s, precipitation + tributaries)
            t: Current timestep index (for seasonal evaporation)
            choices: Modeling methodology choices
            river_flows: Optional real river flow data [St.Mary's, Detroit, Niagara, St.Lawrence] (m³/s)
        """
        dynamics = choices["dynamics"]

        # Convert to m³/month
        seconds_per_month = 86400.0 * 30.0
        soo_outflow = flows[0] * seconds_per_month
        moses_outflow = flows[1] * seconds_per_month

        # Surface areas in m²
        areas_m2 = SURFACE_AREAS * 1e6

        # Use real river flow data if available (valid = positive flow, not NaN)
        has_real_flows = (
            river_flows is not None
            and len(river_flows) > t
            and not np.isnan(river_flows[t, 0])
            and not np.isnan(river_flows[t, 1])
            and not np.isnan(river_flows[t, 2])
            and river_flows[t, 0] > 100  # Physically realistic minimum flow
            and river_flows[t, 1] > 100
            and river_flows[t, 2] > 100
        )

        if has_real_flows:
            # Real historical river flows (m³/s)
            # river_flows: [St. Mary's, Detroit, Niagara, St. Lawrence]
            flow_SH = river_flows[t, 0]  # St. Mary's River: Superior -> Huron
            flow_HE = river_flows[t, 1]  # Detroit River: Huron -> Erie
            flow_EO = river_flows[t, 2]  # Niagara River: Erie -> Ontario
            # Note: St. Lawrence River (index 3) is Ontario outflow, not used in mass balance
        else:
            # Compute inter-lake flows from hydraulic conductance model
            # Inter-lake hydraulic conductance (m³/s per meter of level difference)
            # Calibrated to realistic Great Lakes flow rates:
            #   St. Marys River (Superior->Huron): ~2000 m³/s with ~6m nominal diff
            #   St. Clair River (Huron->Erie): ~5400 m³/s with ~3m diff
            #   Niagara River (Erie->Ontario): ~6000 m³/s with ~99m diff (falls/weirs)
            K_SH = 350.0    # Superior -> Huron/Michigan (via St. Marys River)
            K_HE = 1800.0   # Huron -> Erie (via St. Clair River)
            K_EO = 60.0     # Erie -> Ontario (restricted by Niagara Falls/weirs)

            # Level differences drive inter-lake flows (positive = downstream)
            delta_SH = prev_levels[0] - prev_levels[1]  # Superior - Michigan/Huron
            delta_HE = prev_levels[2] - prev_levels[3]  # Huron - Erie
            delta_EO = prev_levels[3] - prev_levels[4]  # Erie - Ontario

            # Inter-lake flows (m³/s)
            if dynamics == "flow_delay":
                # Delayed response: inter-lake flows respond to level difference
                # from the PREVIOUS timestep, modeling water travel time between lakes.
                # On first call (_prev_deltas is None), use current deltas as fallback.
                current_deltas = np.array([delta_SH, delta_HE, delta_EO])
                if self._prev_deltas is not None:
                    delayed = self._prev_deltas
                else:
                    delayed = current_deltas
                self._prev_deltas = current_deltas  # Store for next timestep

                flow_SH = K_SH * max(delayed[0], 0)
                flow_HE = K_HE * max(delayed[1], 0)
                flow_EO = K_EO * max(delayed[2], 0)
            else:
                flow_SH = K_SH * max(delta_SH, 0)  # Only flows downhill
                flow_HE = K_HE * max(delta_HE, 0)
                flow_EO = K_EO * max(delta_EO, 0)

        # Convert to m³/month
        flow_SH_month = flow_SH * seconds_per_month
        flow_HE_month = flow_HE * seconds_per_month
        flow_EO_month = flow_EO * seconds_per_month

        # Mass balance for each lake
        level_change = np.zeros(5)

        # Superior: external inflow - Soo Locks outflow - inter-lake outflow
        level_change[0] = (inflow[0] * seconds_per_month - soo_outflow - flow_SH_month) / areas_m2[0]

        # Michigan & Huron: connected, share same level
        # Receives: Soo Locks + inter-lake from Superior + external
        # Loses: inter-lake to Erie
        mich_huron_net = (inflow[1] + inflow[2]) * seconds_per_month + soo_outflow + flow_SH_month - flow_HE_month
        mich_huron_area = areas_m2[1] + areas_m2[2]
        level_change[1] = mich_huron_net / mich_huron_area
        level_change[2] = mich_huron_net / mich_huron_area

        # Erie: receives from Huron, loses to Ontario + external
        level_change[3] = (inflow[3] * seconds_per_month + flow_HE_month - flow_EO_month) / areas_m2[3]

        # Ontario: receives from Erie + external, loses through Moses-Saunders
        level_change[4] = (inflow[4] * seconds_per_month + flow_EO_month - moses_outflow) / areas_m2[4]

        # Add evaporation if enabled
        if dynamics in ["seasonal_evap", "stochastic_inflow", "flow_delay"]:
            evap_mm = 2.5 + np.sin(2 * np.pi * t / 12) * 1.5
            evap_m = evap_mm * 0.001 * 30
            level_change -= evap_m

        new_levels = prev_levels + level_change

        # Add stochasticity if enabled
        if dynamics == "stochastic_inflow":
            new_levels += np.random.normal(0, 0.05, size=len(new_levels))

        # Clamp to physically plausible range (allow some overshoot for penalty)
        # Use 2x the historical range as hard limits to prevent numerical explosion
        hard_min = LEVEL_RANGES[:, 0] - (LEVEL_RANGES[:, 1] - LEVEL_RANGES[:, 0])
        hard_max = LEVEL_RANGES[:, 1] + (LEVEL_RANGES[:, 1] - LEVEL_RANGES[:, 0])
        new_levels = np.clip(new_levels, hard_min, hard_max)

        return new_levels

    def _check_level_constraints(self, levels: np.ndarray) -> float:
        """Check water levels against historical safe ranges."""
        below = np.maximum(LEVEL_RANGES[:, 0] - levels, 0)
        above = np.maximum(levels - LEVEL_RANGES[:, 1], 0)
        return float(np.sum(below + above))

    def _compute_sensitivity(
        self,
        choices: Dict[str, str],
        nominal_inflows: np.ndarray,
        n_steps: int,
        nominal_levels: np.ndarray,
    ) -> float:
        """
        Compute algorithm sensitivity to environmental changes (per problem requirement line 12).
        Tests how much water levels change when inflows are perturbed (flood/drought scenarios).
        Returns score in [0,1] where 1 = insensitive (robust), 0 = very sensitive.

        Args:
            choices: Modeling methodology choices
            nominal_inflows: Inflow data used in the main simulation
            n_steps: Number of simulation timesteps
            nominal_levels: Water levels from the already-computed nominal simulation
        """
        n_lakes = len(LAKE_NAMES)
        n_dams = len(DAM_NAMES)

        # Scenario 1: +20% inflow perturbation (wet/flood scenario)
        self._prev_deltas = None
        flood_inflows = nominal_inflows * 1.2
        flood_levels = np.zeros((n_steps, n_lakes))
        flood_levels[0] = NOMINAL_LEVELS.copy()
        flood_flows = np.zeros((n_steps, n_dams))

        for t in range(1, n_steps):
            flood_flows[t] = self._compute_control(
                flood_levels[t-1], t, flood_inflows[t], choices
            )
            flood_flows[t], _ = self._apply_constraints(flood_flows[t], choices)
            flood_levels[t] = self._update_dynamics(
                flood_levels[t-1], flood_flows[t], flood_inflows[t], t, choices
            )

        # Scenario 2: -20% inflow perturbation (dry/drought scenario)
        self._prev_deltas = None
        drought_inflows = nominal_inflows * 0.8
        drought_levels = np.zeros((n_steps, n_lakes))
        drought_levels[0] = NOMINAL_LEVELS.copy()
        drought_flows = np.zeros((n_steps, n_dams))

        for t in range(1, n_steps):
            drought_flows[t] = self._compute_control(
                drought_levels[t-1], t, drought_inflows[t], choices
            )
            drought_flows[t], _ = self._apply_constraints(drought_flows[t], choices)
            drought_levels[t] = self._update_dynamics(
                drought_levels[t-1], drought_flows[t], drought_inflows[t], t, choices
            )

        # Sensitivity = deviation from nominal trajectory under perturbation
        flood_dev = np.mean(np.abs(flood_levels - nominal_levels))
        drought_dev = np.mean(np.abs(drought_levels - nominal_levels))
        avg_deviation = (flood_dev + drought_dev) * 0.5

        # Convert to [0,1] score: lower deviation = higher score
        # 0.1m deviation = 0.5 score; 0 deviation = perfect 1.0 score
        sensitivity_score = 1.0 / (1.0 + avg_deviation * 10)

        return sensitivity_score

    def _compute_objectives(
        self,
        water_levels: np.ndarray,
        dam_flows: np.ndarray,
        choices: Dict[str, str],
    ) -> Tuple[Dict[str, float], int]:
        """Compute all 6 stakeholder objective values.

        Returns:
            Tuple of (objectives_dict, n_active_objectives)
        """
        objectives = {}

        # Determine which stakeholders are explicitly modeled
        subset = choices["stakeholders"]
        if subset == "core_3":
            active = ["flood_prevention", "navigation", "hydropower"]
        elif subset == "balanced_4":
            active = ["flood_prevention", "navigation", "hydropower", "recreation"]
        elif subset == "comprehensive_5":
            active = ["flood_prevention", "navigation", "hydropower", "recreation", "ecosystem"]
        else:  # full_6
            active = ["flood_prevention", "navigation", "hydropower", "recreation", "ecosystem", "municipal_water"]

        # 1. Flood prevention: minimize excess above max level
        excess = np.maximum(water_levels - LEVEL_RANGES[:, 1], 0)
        objectives["flood_prevention"] = float(1.0 / (1.0 + np.mean(excess)))

        # 2. Navigation: minimize deficit below min level
        deficit = np.maximum(LEVEL_RANGES[:, 0] - water_levels, 0)
        objectives["navigation"] = float(1.0 / (1.0 + np.mean(deficit)))

        # 3. Hydropower: flow through dams generates revenue
        normalized_flow = np.clip(
            (dam_flows - DAM_FLOW_RANGES[:, 0])
            / (DAM_FLOW_RANGES[:, 1] - DAM_FLOW_RANGES[:, 0]),
            0, 1,
        )
        objectives["hydropower"] = float(np.mean(normalized_flow))

        # 4. Recreation: levels around nominal is best
        if "recreation" in active:
            ideal_dev = np.abs(water_levels - NOMINAL_LEVELS)
            objectives["recreation"] = float(1.0 / (1.0 + np.mean(ideal_dev)))
        else:
            objectives["recreation"] = 0.0  # Not modeled: neutral (no contribution)

        # 5. Ecosystem: level stability is good for wetlands
        if "ecosystem" in active:
            volatility = np.std(water_levels, axis=0)
            objectives["ecosystem"] = float(1.0 / (1.0 + np.mean(volatility)))
        else:
            objectives["ecosystem"] = 0.0

        # 6. Municipal water: intake reliability
        if "municipal_water" in active:
            below_intake = np.maximum(LEVEL_RANGES[:, 0] - 0.5 - water_levels, 0)
            objectives["municipal_water"] = float(1.0 / (1.0 + np.mean(below_intake)))
        else:
            objectives["municipal_water"] = 0.0

        return objectives, len(active)

    def _compute_fitness(
        self,
        objectives: Dict[str, float],
        n_active: int,
        constraint_violations: float,
        backtesting_deviation: float,
        sensitivity_score: float,
        choices: Dict[str, str],
    ) -> float:
        """Compute overall fitness using specified objective form and coupling method.

        Args:
            objectives: Dict of all 6 objective values (inactive ones are 0.0)
            n_active: Number of actively modeled objectives (3-6)
            constraint_violations: Total constraint violation score
            backtesting_deviation: Deviation from 2017 actual levels (lower = better)
            sensitivity_score: Robustness to environmental changes (higher = better)
            choices: Modeling methodology choices
        """
        obj_values = np.array(list(objectives.values()))
        obj_form = choices["objective_form"]
        coupling = choices["coupling"]

        # AHP hierarchy: predefined weights for all 6 objectives
        # Only active objectives contribute to fitness
        ahp_all_weights = np.array([0.25, 0.25, 0.15, 0.1, 0.15, 0.1])

        # Determine weights based on coupling method
        if coupling == "equal_weight":
            # Equal weight among ACTIVE objectives only
            weights = np.zeros_like(obj_values)
            weights[:n_active] = 1.0 / n_active
        elif coupling == "entropy_weight":
            # Entropy-based: higher weight for objectives that deviate from mean
            # Only consider active objectives
            active_vals = obj_values[:n_active]
            deviations = np.abs(active_vals - np.mean(active_vals))
            total_dev = np.sum(deviations)
            if total_dev < 1e-10:
                # All equal: fall back to equal weighting
                weights = np.zeros_like(obj_values)
                weights[:n_active] = 1.0 / n_active
            else:
                active_weights = deviations / total_dev
                weights = np.zeros_like(obj_values)
                weights[:n_active] = active_weights
        elif coupling == "ahp_hierarchy":
            # AHP: renormalize over active objectives
            weights = ahp_all_weights[:n_active].copy()
            weights = weights / np.sum(weights)
            # Pad with zeros for inactive
            full_weights = np.zeros_like(obj_values)
            full_weights[:n_active] = weights
            weights = full_weights
        elif coupling in ["pareto_filter", "topsis"]:
            # For Pareto and TOPSIS, use equal weight among active
            weights = np.zeros_like(obj_values)
            weights[:n_active] = 1.0 / n_active
        else:
            weights = np.zeros_like(obj_values)
            weights[:n_active] = 1.0 / n_active

        # Apply objective function form (only over active objectives)
        active_obj = obj_values[:n_active]
        active_weights = weights[:n_active]

        if obj_form == "linear_weighted":
            raw_fitness = float(np.sum(active_weights * active_obj))

        elif obj_form == "chebyshev":
            # Minimize maximum regret = maximize minimum weighted value
            weighted = active_weights * active_obj
            raw_fitness = float(np.min(weighted))

        elif obj_form == "exponential_utility":
            # Diminishing returns
            alpha = 0.5
            raw_fitness = float(np.sum(1.0 - np.exp(-alpha * active_weights * active_obj)))

        elif obj_form == "lexicographic":
            # Geometrically decreasing weights for ranked objectives
            lex_weights = np.array([0.5, 0.25, 0.125, 0.0625, 0.03125, 0.03125])
            raw_fitness = float(np.sum(lex_weights[:n_active] * active_obj))

        elif obj_form == "min_max_fairness":
            # Max-min fairness: maximize the minimum stakeholder value
            raw_fitness = float(np.min(active_obj))

        else:
            raw_fitness = float(np.mean(active_obj))

        # Apply constraint penalty
        feasibility = 1.0 / (1.0 + constraint_violations / self.n_timesteps)

        # Include problem-required metrics (per lines 11-12 of problem statement)
        # backtesting_deviation: lower is better, convert to [0,1]
        backtest_score = 1.0 / (1.0 + backtesting_deviation * 100)

        # Robustness adjustment (if applicable)
        robustness = choices["robustness"]
        if robustness == "worst_case":
            # Minimax: additional penalty for worst-case performance
            raw_fitness = 0.8 * raw_fitness + 0.2 * float(np.min(active_obj))
        elif robustness == "stochastic_expected":
            # Expected value: blend with mean to reduce variance sensitivity
            raw_fitness = 0.7 * raw_fitness + 0.3 * float(np.mean(active_obj))
        elif robustness == "stochastic_cvar":
            # CVaR: penalize worst 10% tail
            raw_fitness = 0.9 * raw_fitness + 0.1 * float(np.percentile(active_obj, 10))

        # Final fitness: stakeholder objectives + feasibility + backtesting + sensitivity
        # Weighting: 60% objectives, 15% feasibility, 15% backtesting, 10% sensitivity
        fitness = (0.60 * raw_fitness
                   + 0.15 * feasibility
                   + 0.15 * backtest_score
                   + 0.10 * sensitivity_score)

        return float(fitness)


# ============================================================
# Standalone Test
# ============================================================

if __name__ == "__main__":
    import asyncio
    print("Testing GreatLakesModelingEvaluator...")

    evaluator = GreatLakesModelingEvaluator()

    # Test a random genotype
    test_genotype = {
        "dynamics": "stochastic_inflow",
        "constraints": "soft_penalty",
        "objective_form": "chebyshev",
        "stakeholders": "full_6",
        "solver": "linear_program",
        "temporal": "seasonal_peak",
        "robustness": "deterministic",
        "coupling": "entropy_weight",
    }

    # Create mock EvalContext with genotype in metadata
    mock_cfg = EvalContext(
        data_path="",
        project_root="",
        timeout=60.0,
        metadata={"genotype": test_genotype},
    )

    result = asyncio.run(evaluator.evaluate(mock_cfg))
    print(f"\nTest Genotype: {test_genotype}")
    print(f"\nResults (score = overall_fitness): {result.score:.4f}")
    print("\nMetrics:")
    for k, v in sorted(result.metrics.items()):
        print(f"  {k:25s}: {v:.4f}")

    print("\n[OK] Evaluator working!")
