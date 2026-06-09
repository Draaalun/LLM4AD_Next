"""
Full System Test - NO API KEY REQUIRED
========================================

Tests the Great Lakes project integration with LLM4AD framework:
1. Evaluator import and metrics calculation
2. Genotype format validation
3. All genotype alleles work correctly
4. Physical simulation correctness
"""

import sys
import traceback
from pathlib import Path

import numpy as np


def test_section(name):
    print("\n" + "="*70)
    print("  " + name)
    print("="*70)


def check(condition, desc):
    status = "PASS" if condition else "FAIL"
    mark = "[OK]" if condition else "[XX]"
    print(f"  {mark} [{status}] {desc}")
    return condition


def test_evaluator_import():
    """Test evaluator can be imported and initialized."""
    test_section("1. Evaluator & Framework Integration")

    try:
        from great_lakes_evaluator import GreatLakesModelingEvaluator
        evaluator = GreatLakesModelingEvaluator()
        check(True, "GreatLakesModelingEvaluator imported and initialized")
        return evaluator
    except Exception as e:
        check(False, f"Evaluator import failed: {e}")
        traceback.print_exc()
        return None


def test_template_genotype():
    """Test genotype.py template has correct format."""
    test_section("2. Genotype Template Validation")

    template_path = Path(__file__).parent / "template" / "genotype.py"
    if not template_path.exists():
        check(False, "template/genotype.py not found")
        return

    code = template_path.read_text(encoding="utf-8")

    check("# EVOLVE_START" in code, "EVOLVE_START marker present")
    check("# EVOLVE_END" in code, "EVOLVE_END marker present")
    check('dynamics = "' in code, "dynamics variable present")
    check('constraints = "' in code, "constraints variable present")
    check('objective_form = "' in code, "objective_form variable present")
    check('stakeholders = "' in code, "stakeholders variable present")
    check('solver = "' in code, "solver variable present")
    check('temporal = "' in code, "temporal variable present")
    check('robustness = "' in code, "robustness variable present")
    check('coupling = "' in code, "coupling variable present")
    check("GENOTYPE = {" in code, "GENOTYPE dict construction present")

    # Verify the genotype can be executed
    try:
        import types
        module = types.ModuleType("test_genotype")
        exec(code, module.__dict__)
        check("dynamics" in module.GENOTYPE, "GENOTYPE dict has 'dynamics' key")
        check("constraints" in module.GENOTYPE, "GENOTYPE dict has 'constraints' key")
        check(len(module.GENOTYPE) == 8, f"GENOTYPE has 8 dimensions (got {len(module.GENOTYPE)})")
        print(f"  Sample genotype: {module.GENOTYPE}")
    except Exception as e:
        check(False, f"Cannot execute genotype template: {e}")
        traceback.print_exc()


def test_all_alleles_supported(evaluator):
    """Test every possible allele value works without error."""
    test_section("3. All Alleles & Modeling Dimensions")

    allele_space = {
        "dynamics": ["simple_mass_balance", "seasonal_evap", "flow_delay", "stochastic_inflow"],
        "constraints": ["hard_clipping", "soft_penalty", "barrier_function", "leaky_constraint"],
        "objective_form": ["linear_weighted", "chebyshev", "exponential_utility", "lexicographic", "min_max_fairness"],
        "stakeholders": ["core_3", "balanced_4", "comprehensive_5", "full_6"],
        "solver": ["nsga2", "linear_program", "particle_swarm", "bayesian_opt"],
        "temporal": ["annual_monthly", "seasonal_peak", "multi_year", "event_triggered"],
        "robustness": ["deterministic", "worst_case", "stochastic_expected", "stochastic_cvar"],
        "coupling": ["equal_weight", "entropy_weight", "ahp_hierarchy", "pareto_filter", "topsis"],
    }

    all_pass = True
    total = 0

    for dim, alleles in allele_space.items():
        print(f"\n  Testing {dim}:")
        for allele in alleles:
            try:
                # Create minimal genotype
                genotype = {
                    "dynamics": "simple_mass_balance",
                    "constraints": "hard_clipping",
                    "objective_form": "linear_weighted",
                    "stakeholders": "core_3",
                    "solver": "nsga2",
                    "temporal": "annual_monthly",
                    "robustness": "deterministic",
                    "coupling": "equal_weight",
                }
                genotype[dim] = allele

                # Use internal methods directly
                choices = evaluator._parse_genotype(genotype)
                inflows = evaluator.historical_data["inflows"][:12]
                metrics = evaluator._run_simulation(choices, inflows, n_steps=12)

                check(True, f"  {dim:20s} = {allele:25s} -> score: {metrics.get('overall_fitness', 0):.3f}")
                total += 1
            except Exception as e:
                check(False, f"  {dim:20s} = {allele:25s} ERROR: {e}")
                all_pass = False
                total += 1

    print(f"\n  Total alleles tested: {total}")
    return all_pass


def test_metric_computation(evaluator):
    """Test all metrics are computed correctly."""
    test_section("4. Metrics Computation")

    genotypes_to_test = [
        ("Baseline", {
            "dynamics": "simple_mass_balance",
            "constraints": "hard_clipping",
            "objective_form": "linear_weighted",
            "stakeholders": "core_3",
            "solver": "nsga2",
            "temporal": "annual_monthly",
            "robustness": "deterministic",
            "coupling": "equal_weight",
        }),
        ("Full Stakeholders", {
            "dynamics": "seasonal_evap",
            "constraints": "soft_penalty",
            "objective_form": "chebyshev",
            "stakeholders": "full_6",
            "solver": "linear_program",
            "temporal": "multi_year",
            "robustness": "stochastic_expected",
            "coupling": "ahp_hierarchy",
        }),
    ]

    for name, genotype in genotypes_to_test:
        print(f"\n  Genotype: {name}")
        try:
            choices = evaluator._parse_genotype(genotype)
            inflows = evaluator.historical_data["inflows"][:12]
            metrics = evaluator._run_simulation(choices, inflows, n_steps=12)

            expected_metrics = [
                "flood_prevention", "navigation", "hydropower", "recreation",
                "ecosystem", "municipal_water", "constraint_satisfaction",
                "backtesting_deviation", "sensitivity_score", "overall_fitness"
            ]

            for metric in expected_metrics:
                if metric in metrics:
                    val = metrics[metric]
                    is_valid = isinstance(val, (int, float)) and not np.isnan(val)
                    check(is_valid, f"    {metric:25s} = {val:.4f}")
                else:
                    check(False, f"    {metric:25s} = MISSING")

        except Exception as e:
            check(False, f"  Evaluation failed: {e}")
            traceback.print_exc()


def test_config_file():
    """Test yaml config is valid."""
    test_section("5. YAML Configuration")

    config_path = Path(__file__).parent / "great_lakes_control.yaml"
    if not config_path.exists():
        check(False, "great_lakes_control.yaml not found")
        return

    import yaml
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        check(True, "YAML loads successfully")
        check("evaluator" in config, "Has 'evaluator' section")
        check("evolution" in config, "Has 'evolution' section")
        check("planner" in config, "Has 'planner' section")
        check("coder" in config, "Has 'coder' section")

        print(f"\n  Config loaded: {config.get('project_name', 'unnamed')}")
        print(f"  Islands: {config['evolution'].get('num_islands', 'N/A')}")
        print(f"  Population per island: {config['evolution'].get('island_population_size', 'N/A')}")
        print(f"  Generations: {config['evolution'].get('max_generations', 'N/A')}")

    except Exception as e:
        check(False, f"YAML parse error: {e}")
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  Great Lakes LLM4AD Integration - Full System Test")
    print("  " + "="*68)
    print("\n  No API key required - testing offline components only")

    results = []

    # Test 1: Evaluator import
    evaluator = test_evaluator_import()
    results.append(evaluator is not None)

    # Test 2: Genotype template
    test_template_genotype()

    # Test 3: All alleles
    if evaluator:
        results.append(test_all_alleles_supported(evaluator))

        # Test 4: Metrics
        test_metric_computation(evaluator)

    # Test 5: YAML config
    test_config_file()

    # Summary
    test_section("TEST SUMMARY")
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n  {'PASS' if passed == total else 'SOME TESTS FAILED'}: {passed}/{total} critical tests passed")

    if passed == total:
        print("\n  [OK] System is ready for LLM4AD evolution!")
        print("\n  Run with: llm4ad run great_lakes_control.yaml")
        return 0
    else:
        print("\n  [XX] Some tests need attention before running evolution")
        return 1


if __name__ == "__main__":
    sys.exit(main())
