"""Great Lakes modeling methodology genotype.

IMPORTANT: ONLY MODIFY THE VALUES OF THE VARIABLES BELOW.
DO NOT ADD ANY CLASSES, FUNCTIONS, OR ADDITIONAL CODE.
THE GENOTYPE DICT WILL BE AUTOMATICALLY CONSTRUCTED FROM THESE VARIABLES.
"""

# EVOLVE_START
# Model choice parameters - set each to a valid option
dynamics = "simple_mass_balance"       # Options: simple_mass_balance, seasonal_evap, flow_delay, stochastic_inflow
constraints = "hard_clipping"          # Options: hard_clipping, soft_penalty, barrier_function, leaky_constraint
objective_form = "linear_weighted"     # Options: linear_weighted, chebyshev, exponential_utility, lexicographic, min_max_fairness
stakeholders = "core_3"                # Options: core_3, balanced_4, comprehensive_5, full_6
solver = "nsga2"                       # Options: nsga2, mpc_rolling, linear_program, particle_swarm, bayesian_opt
temporal = "annual_monthly"            # Options: annual_monthly, seasonal_peak, multi_year, event_triggered
robustness = "deterministic"           # Options: deterministic, worst_case, stochastic_expected, stochastic_cvar
coupling = "equal_weight"              # Options: equal_weight, entropy_weight, ahp_hierarchy, pareto_filter, topsis
# EVOLVE_END

# Build genotype dict - DO NOT MODIFY THIS SECTION
GENOTYPE = {
    "dynamics": dynamics,
    "constraints": constraints,
    "objective_form": objective_form,
    "stakeholders": stakeholders,
    "solver": solver,
    "temporal": temporal,
    "robustness": robustness,
    "coupling": coupling,
}
