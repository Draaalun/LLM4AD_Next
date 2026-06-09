"""Generate training and test data for symbolic regression benchmarks.

Available benchmark functions:
- Nguyen benchmarks (1-9): Standard symbolic regression benchmarks
- Keijzer benchmarks (6, 15): Additional difficulty benchmarks
- Feynman benchmarks (100 equations): Physics equations from Feynman Lectures
- Nguyen benchmarks (1-9): Standard symbolic regression benchmarks
- Keijzer benchmarks (6, 15): Additional difficulty benchmarks
- Feynman benchmarks (100 equations): Physics equations from Feynman Lectures
"""

import math
import os
import random
from collections.abc import Callable

# === Feynman benchmark function definitions ===
# These will be dynamically generated from the CSV data
# We'll store them as a dictionary mapping names to (func, n_vars, ranges)

def parse_feynman_formula(formula_str: str) -> Callable:
    """Parse a Feynman formula string into a callable function.
    
    The formula uses Python syntax with variables x0, x1, x2, ...
    This is a simple evaluator - for safety we use eval with restricted globals.
    
    Args:
        formula_str: Formula string with variable names like x0, x1, etc.
    
    Returns:
        Function that evaluates the formula given variable values
    """
    # Create a safe evaluation environment
    safe_dict = {
        'abs': abs, 'exp': math.exp, 'log': math.log, 'sqrt': math.sqrt,
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan, 'asin': math.asin,
        'acos': math.acos, 'atan': math.atan, 'sinh': math.sinh, 'cosh': math.cosh,
        'tanh': math.tanh, 'pi': math.pi, 'e': math.e
    }
    
    def evaluator(*args):
        # Create variable bindings: x0, x1, x2, ...
        local_dict = {f'x{i}': val for i, val in enumerate(args)}
        return eval(formula_str, safe_dict, local_dict)
    
    return evaluator


# Feynman benchmarks data (from CSV)
# Structure: (func, n_vars, ranges) - ranges will be determined from CSV
# We'll build this programmatically from the CSV data
FEYNMAN_BENCHMARKS = {}

# We'll define the Feynman formulas as strings with x0, x1, x2... variables
# Based on the CSV file provided

FEYNMAN_FORMULAS = {
    # I.6.2a: Gaussian distribution (1 variable)
    "feynman_I.6.2a": {
        "formula": "math.exp(-x0**2/2) / math.sqrt(2*math.pi)",
        "n_vars": 1,
        "ranges": [(1, 3)],
        "original_vars": ["theta"]
    },
    # I.6.2: Gaussian with sigma (2 vars)
    "feynman_I.6.2": {
        "formula": "math.exp(-(x0/x1)**2/2) / (math.sqrt(2*math.pi)*x1)",
        "n_vars": 2,
        "ranges": [(1, 3), (1, 3)],
        "original_vars": ["sigma", "theta"]
    },
    # I.6.2b: Gaussian with mean and sigma (3 vars)
    "feynman_I.6.2b": {
        "formula": "math.exp(-((x0-x1)/x2)**2/2) / (math.sqrt(2*math.pi)*x2)",
        "n_vars": 3,
        "ranges": [(1, 3), (1, 3), (1, 3)],
        "original_vars": ["sigma", "theta", "theta1"]
    },
    # I.8.14: Distance in 2D (4 vars)
    "feynman_I.8.14": {
        "formula": "math.sqrt((x0-x1)**2 + (x2-x3)**2)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["x1", "x2", "y1", "y2"]
    },
    # I.9.18: Gravitational force (9 vars)
    "feynman_I.9.18": {
        "formula": "x2 * x0 * x1 / ((x3-x4)**2 + (x5-x6)**2 + (x7-x8)**2)",
        "n_vars": 9,
        "ranges": [(1, 2), (1, 2), (1, 2), (3, 4), (1, 2), (3, 4), (1, 2), (3, 4), (1, 2)],
        "original_vars": ["m1", "m2", "G", "x1", "x2", "y1", "y2", "z1", "z2"]
    },
    # I.10.7: Relativistic mass (3 vars)
    "feynman_I.10.7": {
        "formula": "x0 / math.sqrt(1 - x1**2 / x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 2), (3, 10)],
        "original_vars": ["m_0", "v", "c"]
    },
    # I.11.19: Dot product in 3D (6 vars)
    "feynman_I.11.19": {
        "formula": "x0*x3 + x1*x4 + x2*x5",
        "n_vars": 6,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["x1", "x2", "x3", "y1", "y2", "y3"]
    },
    # I.12.1: Friction force (2 vars)
    "feynman_I.12.1": {
        "formula": "x0 * x1",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["mu", "Nn"]
    },
    # I.12.2: Coulomb force (4 vars)
    "feynman_I.12.2": {
        "formula": "x0 * x1 * x4 / (4 * math.pi * x2 * x4**3)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["q1", "q2", "epsilon", "r"]
    },
    # I.12.4: Electric field (3 vars)
    "feynman_I.12.4": {
        "formula": "x0 * x2 / (4 * math.pi * x1 * x2**3)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q1", "epsilon", "r"]
    },
    # I.12.5: Force from electric field (2 vars)
    "feynman_I.12.5": {
        "formula": "x0 * x1",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["q2", "Ef"]
    },
    # I.12.11: Lorentz force (5 vars)
    "feynman_I.12.11": {
        "formula": "x0 * (x1 + x2 * x3 * math.sin(x4))",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "Ef", "B", "v", "theta"]
    },
    # I.13.4: Kinetic energy (4 vars)
    "feynman_I.13.4": {
        "formula": "0.5 * x0 * (x1**2 + x2**2 + x3**2)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m", "v", "u", "w"]
    },
    # I.13.12: Gravitational potential (5 vars)
    "feynman_I.13.12": {
        "formula": "x4 * x0 * x1 * (1/x2 - 1/x3)",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m1", "m2", "r1", "r2", "G"]
    },
    # I.14.3: Gravitational potential near Earth (3 vars)
    "feynman_I.14.3": {
        "formula": "x0 * x1 * x2",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["m", "g", "z"]
    },
    # I.14.4: Spring potential (2 vars)
    "feynman_I.14.4": {
        "formula": "0.5 * x0 * x1**2",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["k_spring", "x"]
    },
    # I.15.3x: Lorentz transformation - position (4 vars)
    "feynman_I.15.3x": {
        "formula": "(x0 - x2*x3) / math.sqrt(1 - x2**2/x1**2)",
        "n_vars": 4,
        "ranges": [(5, 10), (3, 20), (1, 2), (1, 2)],
        "original_vars": ["x", "c", "u", "t"]
    },
    # I.15.3t: Lorentz transformation - time (4 vars)
    "feynman_I.15.3t": {
        "formula": "(x3 - x2*x0/x1**2) / math.sqrt(1 - x2**2/x1**2)",
        "n_vars": 4,
        "ranges": [(1, 5), (3, 10), (1, 2), (1, 5)],
        "original_vars": ["x", "c", "u", "t"]
    },
    # I.15.1: Relativistic momentum (3 vars)
    "feynman_I.15.1": {
        "formula": "x0 * x1 / math.sqrt(1 - x1**2/x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 2), (3, 10)],
        "original_vars": ["m_0", "v", "c"]
    },
    # I.16.6: Velocity addition (3 vars)
    "feynman_I.16.6": {
        "formula": "(x1 + x2) / (1 + x1*x2/x0**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["c", "v", "u"]
    },
    # I.18.4: Center of mass (4 vars)
    "feynman_I.18.4": {
        "formula": "(x0*x2 + x1*x3) / (x0 + x1)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m1", "m2", "r1", "r2"]
    },
    # I.18.12: Torque (3 vars)
    "feynman_I.18.12": {
        "formula": "x0 * x1 * math.sin(x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["r", "F", "theta"]
    },
    # I.18.14: Angular momentum (4 vars)
    "feynman_I.18.14": {
        "formula": "x0 * x1 * x2 * math.sin(x3)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m", "r", "v", "theta"]
    },
    # I.24.6: Energy of harmonic oscillator (4 vars)
    "feynman_I.24.6": {
        "formula": "0.5 * x0 * (x1**2 + x2**2) * 0.5 * x3**2",
        "n_vars": 4,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["m", "omega", "omega_0", "x"]
    },
    # I.25.13: Capacitor voltage (2 vars)
    "feynman_I.25.13": {
        "formula": "x0 / x1",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["q", "C"]
    },
    # I.26.2: Snell's law (2 vars)
    "feynman_I.26.2": {
        "formula": "math.asin(x0 * math.sin(x1))",
        "n_vars": 2,
        "ranges": [(0, 1), (1, 5)],
        "original_vars": ["n", "theta2"]
    },
    # I.27.6: Focal length (3 vars)
    "feynman_I.27.6": {
        "formula": "1 / (1/x0 + x2/x1)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["d1", "d2", "n"]
    },
    # I.29.4: Wave number (2 vars)
    "feynman_I.29.4": {
        "formula": "x0 / x1",
        "n_vars": 2,
        "ranges": [(1, 10), (1, 10)],
        "original_vars": ["omega", "c"]
    },
    # I.29.16: Law of cosines (4 vars)
    "feynman_I.29.16": {
        "formula": "math.sqrt(x0**2 + x1**2 - 2*x0*x1*math.cos(x2 - x3))",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["x1", "x2", "theta1", "theta2"]
    },
    # I.30.3: Diffraction intensity (3 vars)
    "feynman_I.30.3": {
        "formula": "x0 * (math.sin(x2 * x1/2)**2 / math.sin(x1/2)**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["Int_0", "theta", "n"]
    },
    # I.30.5: Diffraction grating (3 vars)
    "feynman_I.30.5": {
        "formula": "math.asin(x0 / (x2 * x1))",
        "n_vars": 3,
        "ranges": [(1, 2), (2, 5), (1, 5)],
        "original_vars": ["lambd", "d", "n"]
    },
    # I.32.5: Larmor formula (4 vars)
    "feynman_I.32.5": {
        "formula": "x0**2 * x1**2 / (6 * math.pi * x2 * x3**3)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "a", "epsilon", "c"]
    },
    # I.32.17: Scattering cross section (6 vars)
    "feynman_I.32.17": {
        "formula": "(0.5 * x0 * x1 * x2**2) * (8 * math.pi * x3**2 / 3) * (x4**4 / (x4**2 - x5**2)**2)",
        "n_vars": 6,
        "ranges": [(1, 2), (1, 2), (1, 2), (1, 2), (1, 2), (3, 5)],
        "original_vars": ["epsilon", "c", "Ef", "r", "omega", "omega_0"]
    },
    # I.34.8: Cyclotron frequency (4 vars)
    "feynman_I.34.8": {
        "formula": "x0 * x1 * x2 / x3",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "v", "B", "p"]
    },
    # I.34.1: Doppler effect (3 vars)
    "feynman_I.34.1": {
        "formula": "x2 / (1 - x1/x0)",
        "n_vars": 3,
        "ranges": [(3, 10), (1, 2), (1, 5)],
        "original_vars": ["c", "v", "omega_0"]
    },
    # I.34.14: Relativistic Doppler (3 vars)
    "feynman_I.34.14": {
        "formula": "(1 + x1/x0) / math.sqrt(1 - x1**2/x0**2) * x2",
        "n_vars": 3,
        "ranges": [(3, 10), (1, 2), (1, 5)],
        "original_vars": ["c", "v", "omega_0"]
    },
    # I.34.27: Photon energy (2 vars)
    "feynman_I.34.27": {
        "formula": "(x1/(2*math.pi)) * x0",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["omega", "h"]
    },
    # I.37.4: Interference intensity (3 vars)
    "feynman_I.37.4": {
        "formula": "x0 + x1 + 2*math.sqrt(x0*x1)*math.cos(x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["I1", "I2", "delta"]
    },
    # I.38.12: Bohr radius (4 vars)
    "feynman_I.38.12": {
        "formula": "4 * math.pi * x3 * (x2/(2*math.pi))**2 / (x0 * x1**2)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m", "q", "h", "epsilon"]
    },
    # I.39.1: Ideal gas energy (2 vars)
    "feynman_I.39.1": {
        "formula": "1.5 * x0 * x1",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["pr", "V"]
    },
    # I.39.11: Ideal gas energy with gamma (3 vars)
    "feynman_I.39.11": {
        "formula": "1/(x0 - 1) * x1 * x2",
        "n_vars": 3,
        "ranges": [(2, 5), (1, 5), (1, 5)],
        "original_vars": ["gamma", "pr", "V"]
    },
    # I.39.22: Ideal gas law (4 vars)
    "feynman_I.39.22": {
        "formula": "x0 * x3 * x1 / x2",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["n", "T", "V", "kb"]
    },
    # I.40.1: Barometric formula (6 vars)
    "feynman_I.40.1": {
        "formula": "x0 * math.exp(-x1 * x2 * x5 / (x4 * x3))",
        "n_vars": 6,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["n_0", "m", "x", "T", "g", "kb"]
    },
    # I.41.16: Blackbody radiation (5 vars)
    "feynman_I.41.16": {
        "formula": "(x2/(2*math.pi)) * x0**3 / (math.pi**2 * x4**2 * (math.exp((x2/(2*math.pi))*x0/(x3*x1)) - 1))",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["omega", "T", "h", "kb", "c"]
    },
    # I.43.16: Drift velocity (4 vars)
    "feynman_I.43.16": {
        "formula": "x0 * x1 * x2 / x3",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["mu_drift", "q", "Volt", "d"]
    },
    # I.43.31: Einstein relation (3 vars)
    "feynman_I.43.31": {
        "formula": "x0 * x1 * x2",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["mob", "T", "kb"]
    },
    # I.43.43: Thermal conductivity (4 vars)
    "feynman_I.43.43": {
        "formula": "1/(x0 - 1) * x1 * x3 / x2",
        "n_vars": 4,
        "ranges": [(2, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["gamma", "kb", "A", "v"]
    },
    # I.44.4: Entropy of ideal gas (5 vars)
    "feynman_I.44.4": {
        "formula": "x0 * x1 * x2 * math.log(x4/x3)",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["n", "kb", "T", "V1", "V2"]
    },
    # I.47.23: Speed of sound (3 vars)
    "feynman_I.47.23": {
        "formula": "math.sqrt(x0 * x1 / x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["gamma", "pr", "rho"]
    },
    # I.48.2: Relativistic energy (3 vars)
    "feynman_I.48.2": {
        "formula": "x0 * x2**2 / math.sqrt(1 - x1**2/x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 2), (3, 10)],
        "original_vars": ["m", "v", "c"]
    },
    # I.50.26: Nonlinear oscillation (4 vars)
    "feynman_I.50.26": {
        "formula": "x0 * (math.cos(x1*x2) + x3 * math.cos(x1*x2)**2)",
        "n_vars": 4,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["x1", "omega", "t", "alpha"]
    },
    # II.2.42: Heat conduction (5 vars)
    "feynman_II.2.42": {
        "formula": "x0 * (x2 - x1) * x3 / x4",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["kappa", "T1", "T2", "A", "d"]
    },
    # II.3.24: Flux from point source (2 vars)
    "feynman_II.3.24": {
        "formula": "x0 / (4 * math.pi * x1**2)",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["Pwr", "r"]
    },
    # II.4.23: Electric potential from point charge (3 vars)
    "feynman_II.4.23": {
        "formula": "x0 / (4 * math.pi * x1 * x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "epsilon", "r"]
    },
    # II.6.11: Dipole potential (4 vars)
    "feynman_II.6.11": {
        "formula": "1/(4 * math.pi * x0) * x1 * math.cos(x2) / x3**2",
        "n_vars": 4,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["epsilon", "p_d", "theta", "r"]
    },
    # II.6.15a: Dipole field xy-component (6 vars)
    "feynman_II.6.15a": {
        "formula": "x1/(4 * math.pi * x0) * 3 * x5 / x2**5 * math.sqrt(x3**2 + x4**2)",
        "n_vars": 6,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["epsilon", "p_d", "r", "x", "y", "z"]
    },
    # II.6.15b: Dipole field radial component (4 vars)
    "feynman_II.6.15b": {
        "formula": "x1/(4 * math.pi * x0) * 3 * math.cos(x2) * math.sin(x2) / x3**3",
        "n_vars": 4,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["epsilon", "p_d", "theta", "r"]
    },
    # II.8.7: Electrostatic energy of sphere (3 vars)
    "feynman_II.8.7": {
        "formula": "0.6 * x0**2 / (4 * math.pi * x1 * x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "epsilon", "d"]
    },
    # II.8.31: Energy density of electric field (2 vars)
    "feynman_II.8.31": {
        "formula": "x0 * x1**2 / 2",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["epsilon", "Ef"]
    },
    # II.10.9: Electric field in dielectric (3 vars)
    "feynman_II.10.9": {
        "formula": "x0 / x1 * 1/(1 + x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["sigma_den", "epsilon", "chi"]
    },
    # II.11.3: Driven harmonic oscillator (5 vars)
    "feynman_II.11.3": {
        "formula": "x0 * x1 / (x2 * (x4**2 - x3**2))",
        "n_vars": 5,
        "ranges": [(1, 3), (1, 3), (1, 3), (3, 5), (1, 2)],
        "original_vars": ["q", "Ef", "m", "omega_0", "omega"]
    },
    # II.11.17: Langevin function expansion (6 vars)
    "feynman_II.11.17": {
        "formula": "x0 * (1 + x4 * x5 * math.cos(x3) / (x1 * x2))",
        "n_vars": 6,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["n_0", "kb", "T", "theta", "p_d", "Ef"]
    },
    # II.11.20: Polarization of dipoles (5 vars)
    "feynman_II.11.20": {
        "formula": "x0 * x1**2 * x2 / (3 * x3 * x4)",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["n_rho", "p_d", "Ef", "kb", "T"]
    },
    # II.11.27: Clausius-Mossotti (4 vars)
    "feynman_II.11.27": {
        "formula": "x0 * x1 / (1 - (x0*x1/3)) * x2 * x3",
        "n_vars": 4,
        "ranges": [(0, 1), (0, 1), (1, 2), (1, 2)],
        "original_vars": ["n", "alpha", "epsilon", "Ef"]
    },
    # II.11.28: Dielectric constant (2 vars)
    "feynman_II.11.28": {
        "formula": "1 + x0*x1 / (1 - (x0*x1/3))",
        "n_vars": 2,
        "ranges": [(0, 1), (0, 1)],
        "original_vars": ["n", "alpha"]
    },
    # II.13.17: Magnetic field from wire (4 vars)
    "feynman_II.13.17": {
        "formula": "1/(4*math.pi*x0*x1**2) * 2 * x2 / x3",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["epsilon", "c", "I", "r"]
    },
    # II.13.23: Relativistic charge density (3 vars)
    "feynman_II.13.23": {
        "formula": "x0 / math.sqrt(1 - x1**2/x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 2), (3, 10)],
        "original_vars": ["rho_c_0", "v", "c"]
    },
    # II.13.34: Relativistic current density (3 vars)
    "feynman_II.13.34": {
        "formula": "x0 * x1 / math.sqrt(1 - x1**2/x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 2), (3, 10)],
        "original_vars": ["rho_c_0", "v", "c"]
    },
    # II.15.4: Magnetic dipole energy (3 vars)
    "feynman_II.15.4": {
        "formula": "-x0 * x1 * math.cos(x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["mom", "B", "theta"]
    },
    # II.15.5: Electric dipole energy (3 vars)
    "feynman_II.15.5": {
        "formula": "-x0 * x1 * math.cos(x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["p_d", "Ef", "theta"]
    },
    # II.21.32: Liénard-Wiechert potential (5 vars)
    "feynman_II.21.32": {
        "formula": "x0 / (4 * math.pi * x1 * x2 * (1 - x3/x4))",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 2), (3, 10)],
        "original_vars": ["q", "epsilon", "r", "v", "c"]
    },
    # II.24.17: Waveguide dispersion (3 vars)
    "feynman_II.24.17": {
        "formula": "math.sqrt(x0**2/x1**2 - math.pi**2/x2**2)",
        "n_vars": 3,
        "ranges": [(4, 6), (1, 2), (2, 4)],
        "original_vars": ["omega", "c", "d"]
    },
    # II.27.16: Poynting vector magnitude (3 vars)
    "feynman_II.27.16": {
        "formula": "x0 * x1 * x2**2",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["epsilon", "c", "Ef"]
    },
    # II.27.18: Energy density EM field (2 vars)
    "feynman_II.27.18": {
        "formula": "x0 * x1**2",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["epsilon", "Ef"]
    },
    # II.34.2a: Current from moving charge (3 vars)
    "feynman_II.34.2a": {
        "formula": "x0 * x1 / (2 * math.pi * x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "v", "r"]
    },
    # II.34.2: Magnetic moment of orbiting charge (3 vars)
    "feynman_II.34.2": {
        "formula": "x0 * x1 * x2 / 2",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "v", "r"]
    },
    # II.34.11: Larmor precession frequency (4 vars)
    "feynman_II.34.11": {
        "formula": "x0 * x1 * x2 / (2 * x3)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["g_", "q", "B", "m"]
    },
    # II.34.29a: Bohr magneton (3 vars)
    "feynman_II.34.29a": {
        "formula": "x0 * x1 / (4 * math.pi * x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["q", "h", "m"]
    },
    # II.34.29b: Zeeman energy (5 vars)
    "feynman_II.34.29b": {
        "formula": "x0 * x3 * x4 * x2 / (x1/(2*math.pi))",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["g_", "h", "Jz", "mom", "B"]
    },
    # II.35.18: Two-level system population (5 vars)
    "feynman_II.35.18": {
        "formula": "x0 / (math.exp(x3*x4/(x1*x2)) + math.exp(-x3*x4/(x1*x2)))",
        "n_vars": 5,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["n_0", "kb", "T", "mom", "B"]
    },
    # II.35.21: Magnetization (5 vars)
    "feynman_II.35.21": {
        "formula": "x0 * x1 * math.tanh(x1 * x2 / (x3 * x4))",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["n_rho", "mom", "B", "kb", "T"]
    },
    # II.36.38: Weiss field equation (8 vars)
    "feynman_II.36.38": {
        "formula": "x0*x1/(x2*x3) + (x0*x4)/(x5*x6**2*x2*x3)*x7",
        "n_vars": 8,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3), (1, 3), (1, 3), (1, 3), (1, 3)],
        "original_vars": ["mom", "H", "kb", "T", "alpha", "epsilon", "c", "M"]
    },
    # II.37.1: Energy in magnetic material (3 vars)
    "feynman_II.37.1": {
        "formula": "x0 * (1 + x2) * x1",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["mom", "B", "chi"]
    },
    # II.38.3: Hooke's law (4 vars)
    "feynman_II.38.3": {
        "formula": "x0 * x1 * x3 / x2",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["Y", "A", "d", "x"]
    },
    # II.38.14: Shear modulus (2 vars)
    "feynman_II.38.14": {
        "formula": "x0 / (2 * (1 + x1))",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["Y", "sigma"]
    },
    # III.4.32: Bose-Einstein distribution (4 vars)
    "feynman_III.4.32": {
        "formula": "1 / (math.exp((x0/(2*math.pi))*x1/(x2*x3)) - 1)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["h", "omega", "kb", "T"]
    },
    # III.4.33: Planck's law (4 vars)
    "feynman_III.4.33": {
        "formula": "(x0/(2*math.pi))*x1 / (math.exp((x0/(2*math.pi))*x1/(x2*x3)) - 1)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["h", "omega", "kb", "T"]
    },
    # III.7.38: Larmor frequency (3 vars)
    "feynman_III.7.38": {
        "formula": "2 * x0 * x1 / (x2/(2*math.pi))",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["mom", "B", "h"]
    },
    # III.8.54: Rabi oscillation probability (3 vars)
    "feynman_III.8.54": {
        "formula": "math.sin(x0 * x1 / (x2/(2*math.pi)))**2",
        "n_vars": 3,
        "ranges": [(1, 2), (1, 2), (1, 4)],
        "original_vars": ["E_n", "t", "h"]
    },
    # III.9.52: Transition probability (6 vars)
    "feynman_III.9.52": {
        "formula": "(x0*x1*x2/(x3/(2*math.pi))) * (math.sin((x4-x5)*x2/2)**2 / ((x4-x5)*x2/2)**2)",
        "n_vars": 6,
        "ranges": [(1, 3), (1, 3), (1, 3), (1, 3), (1, 5), (1, 4.9)],
        "original_vars": ["p_d", "Ef", "t", "h", "omega", "omega_0"]
    },
    # III.10.19: Zeeman Hamiltonian (4 vars)
    "feynman_III.10.19": {
        "formula": "x0 * math.sqrt(x1**2 + x2**2 + x3**2)",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["mom", "Bx", "By", "Bz"]
    },
    # III.12.43: Angular momentum quantization (2 vars)
    "feynman_III.12.43": {
        "formula": "x0 * (x1/(2*math.pi))",
        "n_vars": 2,
        "ranges": [(1, 5), (1, 5)],
        "original_vars": ["n", "h"]
    },
    # III.13.18: Group velocity (4 vars)
    "feynman_III.13.18": {
        "formula": "2 * x0 * x1**2 * x2 / (x3/(2*math.pi))",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["E_n", "d", "k", "h"]
    },
    # III.14.14: Diode equation (5 vars)
    "feynman_III.14.14": {
        "formula": "x0 * (math.exp(x1*x2/(x3*x4)) - 1)",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 2), (1, 2), (1, 2), (1, 2)],
        "original_vars": ["I_0", "q", "Volt", "kb", "T"]
    },
    # III.15.12: Tight binding energy (3 vars)
    "feynman_III.15.12": {
        "formula": "2 * x0 * (1 - math.cos(x1 * x2))",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["U", "k", "d"]
    },
    # III.15.14: Effective mass (3 vars)
    "feynman_III.15.14": {
        "formula": "(x0/(2*math.pi))**2 / (2 * x1 * x2**2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["h", "E_n", "d"]
    },
    # III.15.27: Crystal momentum (3 vars)
    "feynman_III.15.27": {
        "formula": "2 * math.pi * x0 / (x1 * x2)",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["alpha", "n", "d"]
    },
    # III.17.37: Angular distribution (3 vars)
    "feynman_III.17.37": {
        "formula": "x0 * (1 + x1 * math.cos(x2))",
        "n_vars": 3,
        "ranges": [(1, 5), (1, 5), (1, 5)],
        "original_vars": ["beta", "alpha", "theta"]
    },
    # III.19.51: Hydrogen energy levels (5 vars)
    "feynman_III.19.51": {
        "formula": "-x0 * x1**4 / (2 * (4*math.pi*x4)**2 * (x2/(2*math.pi))**2) * (1/x3**2)",
        "n_vars": 5,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["m", "q", "h", "n", "epsilon"]
    },
    # III.21.20: Supercurrent (4 vars)
    "feynman_III.21.20": {
        "formula": "-x0 * x1 * x3 / x2",
        "n_vars": 4,
        "ranges": [(1, 5), (1, 5), (1, 5), (1, 5)],
        "original_vars": ["rho_c_0", "q", "A_vec", "m"]
    },
}


# Build FEYNMAN_BENCHMARKS dictionary with callable functions
for name, data in FEYNMAN_FORMULAS.items():
    formula_str = data["formula"]
    # Convert math.xxx to appropriate functions
    # Add math namespace for evaluation
    exec_globals = {
        'math': math,
        'exp': math.exp, 'log': math.log, 'sqrt': math.sqrt,
        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
        'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
        'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
        'pi': math.pi, 'e': math.e
    }
    
    def make_func(formula, globals_dict):
        def func(*args):
            # Create variable bindings x0, x1, ...
            local_dict = {f'x{i}': val for i, val in enumerate(args)}
            return eval(formula, globals_dict, local_dict)
        return func
    
    FEYNMAN_BENCHMARKS[name] = {
        "func": make_func(formula_str, exec_globals),
        "n_vars": data["n_vars"],
        "ranges": data["ranges"],
        "original_vars": data.get("original_vars", [])
    }


# === Benchmark function definitions (Nguyen and Keijzer only) ===

def nguyen1(x: float, y: float = None) -> float:
    """Nguyen-1: sin(x) + sin(x + x**2)"""
    return math.sin(x) + math.sin(x + x**2)


def nguyen2(x: float, y: float = None) -> float:
    """Nguyen-2: log(x+1) + log(x**2 + 1)"""
    return math.log(x + 1) + math.log(x**2 + 1)


def nguyen3(x: float, y: float = None) -> float:
    """Nguyen-3: sqrt(x)"""
    return math.sqrt(x)


def nguyen4(x: float, y: float) -> float:
    """Nguyen-4: x**4 - x**3 + y**2/2 - y"""
    return x**4 - x**3 + y**2 / 2 - y


def nguyen5(x: float, y: float) -> float:
    """Nguyen-5: sin(x) + sin(y**2)"""
    return math.sin(x) + math.sin(y**2)


def nguyen6(x: float, y: float) -> float:
    """Nguyen-6: 2 * sin(x) * cos(y)"""
    return 2 * math.sin(x) * math.cos(y)


def nguyen7(x: float, y: float) -> float:
    """Nguyen-7: x**y"""
    return x**y


def nguyen8(x: float, y: float) -> float:
    """Nguyen-8: (x + y) ** (x - y)"""
    return (x + y) ** (x - y)


def nguyen9(x: float, y: float) -> float:
    """Nguyen-9: exp(-(x-1)**2) / (1.2 + (y-2.5)**2)"""
    return math.exp(-(x - 1)**2) / (1.2 + (y - 2.5)**2)


def keijzer6(x: float, y: float = None) -> float:
    """Keijzer-6: exp(-x) * x**3 * cos(x) * sin(x) * (cos(x)*sin(x)**2 - 1)"""
    return math.exp(-x) * x**3 * math.cos(x) * math.sin(x) * (math.cos(x)*math.sin(x)**2 - 1)


def keijzer15(x0: float, x1: float, x2: float) -> float:
    """Keijzer-15: sqrt(x0) + sqrt(x1) * sqrt(x2)
    3D benchmark with square roots
    """
    return math.sqrt(x0) + math.sqrt(x1) * math.sqrt(x2)


# === Benchmark registry ===
# Nguyen and Keijzer series only
# Nguyen and Keijzer series only
BENCHMARKS = {
    "nguyen1": {"func": nguyen1, "n_vars": 1, "ranges": [(-1, 1)]},
    "nguyen2": {"func": nguyen2, "n_vars": 1, "ranges": [(0, 2)]},
    "nguyen3": {"func": nguyen3, "n_vars": 1, "ranges": [(0, 4)]},
    "nguyen4": {"func": nguyen4, "n_vars": 2, "ranges": [(-1, 1), (-1, 1)]},
    "nguyen5": {"func": nguyen5, "n_vars": 2, "ranges": [(-10, 10), (-10, 10)]},
    "nguyen6": {"func": nguyen6, "n_vars": 2, "ranges": [(-10, 10), (-10, 10)]},
    "nguyen7": {"func": nguyen7, "n_vars": 2, "ranges": [(0, 1), (0, 4)]},
    "nguyen8": {"func": nguyen8, "n_vars": 2, "ranges": [(0, 1), (0, 1)]},
    "nguyen9": {"func": nguyen9, "n_vars": 2, "ranges": [(0.3, 4), (0.3, 4)]},
    "keijzer6": {"func": keijzer6, "n_vars": 1, "ranges": [(0, 10)]},
    "keijzer15": {"func": keijzer15, "n_vars": 3, "ranges": [(0.01, 5), (0.01, 5), (0.01, 5)]},
}

# Add all Feynman benchmarks
BENCHMARKS.update(FEYNMAN_BENCHMARKS)

# Add all Feynman benchmarks
BENCHMARKS.update(FEYNMAN_BENCHMARKS)


def generate_dataset(
    benchmark: str,
    num_samples: int,
    seed: int = 42,
) -> list[tuple[float, ...]]:
    """Generate dataset for a given benchmark function.

    Variables are named x0, x1, x2, ... for N inputs.

    Args:
        benchmark: Name of the benchmark function
        num_samples: Number of samples to generate
        seed: Random seed

    Returns:
        List of (x0, [x1, x2...], target) tuples
    """
    if benchmark not in BENCHMARKS:
        raise ValueError(f"Unknown benchmark: {benchmark}. Available: {list(BENCHMARKS.keys())}")

    config = BENCHMARKS[benchmark]
    func: Callable = config["func"]
    n_vars = config["n_vars"]
    ranges = config["ranges"]

    random.seed(seed)
    data = []

    for _ in range(num_samples):
        inputs = [random.uniform(r[0], r[1]) for r in ranges]
        target = func(*inputs)
        data.append(tuple(inputs + [target]))

    return data


def save_dataset(data: list[tuple[float, ...]], filepath: str):
    """Save dataset to text file."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    with open(filepath, mode='w', encoding='utf-8') as f:
        for row in data:
            f.write(" ".join(f"{val:.6f}" for val in row) + "\n")


def _detect_indent(line: str) -> int:
    """Count leading spaces to detect indent level."""
    return len(line) - len(line.lstrip(' '))


def _replace_block(lines: list[str], start_key: str, new_content: str) -> list[str]:
    """Replace indented block after start_key with new_content."""
    output_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        output_lines.append(line)

        if line.strip().startswith(start_key):
            key_indent = _detect_indent(line)
            i += 1

            content_indent = None
            while i < len(lines):
                if lines[i].strip():
                    content_indent = _detect_indent(lines[i])
                    break
                i += 1

            while i < len(lines):
                stripped = lines[i].strip()
                if stripped and _detect_indent(lines[i]) < content_indent:
                    break
                i += 1

            indent_str = ' ' * content_indent if content_indent else '  '
            for content_line in new_content.split('\n'):
                if content_line.strip():
                    output_lines.append(f"{indent_str}{content_line}\n")
                else:
                    output_lines.append(f"{indent_str.rstrip()}\n")
            continue

        i += 1
    return output_lines


def update_yaml_config(benchmark: str, config: dict):
    """Update the YAML configuration file with benchmark-specific settings."""
    yaml_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(yaml_path):
        print(f"Warning: {yaml_path} not found, skipping config update")
        return

    ranges = config["ranges"]
    n_vars = len(ranges)

    var_names = [f"x{i}" for i in range(n_vars)]
    range_parts = [f"{name} in {r}" for name, r in zip(var_names, ranges)]
    range_desc = "Input ranges: " + ", ".join(range_parts)

    new_background = f"""In this benchmark, we aim to evolve symbolic regression expressions following the
LLM + EC bi-level optimization approach. The LLM proposes the equation structure
with all tunable parameters explicitly placed in the params array. Bi-level
optimization then uses BFGS gradient-based search to find the optimal values
for these parameters before evaluating the expression. The goal is to find
a symbolic expression that matches the data with minimal mean squared error (MSE).

Dataset has {n_vars} input variable{'s' if n_vars > 1 else ''}. {range_desc}.
Discover the underlying mathematical expression from the data."""

    var_example = ", ".join([f"x{i}" for i in range(n_vars)])
    var_list = ", ".join([f"x{i}: np.ndarray" for i in range(n_vars)])
    func_sig = f"def equation({var_list}, params: np.ndarray) -> np.ndarray:"

    if n_vars == 1:
        example_expr = "params[0] * np.sin(params[1] * x0)"
    elif n_vars == 2:
        example_expr = "params[0] * np.sin(params[1] * x0) + params[2] * np.sin(params[3] * x1 ** 2)"
    else:
        example_expr = "params[0] * np.sin(params[1] * x0) + params[2] * np.sin(params[3] * x1 ** 2)"

    new_prompt = f"""DO NOT WRITE CLASSES, PARSERS, OR HELPER FUNCTIONS. YOU WILL BE PENALIZED FOR COMPLICATED CODE.

**NON-NEGOTIABLE REQUIREMENTS - VIOLATION = 0 SCORE**:
- ONLY write the equation function body
- RETURN DIRECTLY: `return {example_expr}`
- **MANDATORY: EVERY parameter MUST use explicit index notation: params[0], params[1], params[2], ...**
- **WRITE params[N] 100% OF THE TIME - NO EXCEPTIONS**
- **MAX 30 PARAMETERS TOTAL: params[0] to params[29] ONLY - DO NOT USE params[30] OR HIGHER**
- **CRITICAL: TUPLE UNPACKING WILL CRASH THE EVALUATOR AND GIVE YOU 0 SCORE**

**💡 SMART PARAMETER STRATEGY - HIGHER SCORE = FEWER PARAMETERS**:
- **Use fewer parameters**: Each extra parameter adds a 0.1% penalty to your MSE score!
- **Reuse parameters creatively**: `params[0] * np.sin(x0) + params[0] * np.cos(x1)` (same param for multiple terms)
- **Smart combinations**: `params[0] * np.sin(x0 + params[1])` (one param controls both amplitude and phase)
- **Avoid full polynomials**: You don't need EVERY interaction term - pick the most promising ones!
- **Example - 4 params**: `return params[0] * np.sin(x0 + params[1]) + params[2] * np.exp(-params[3] * x1**2)`
- **DO NOT DO THIS - EVER**: `a, b, c, d = params` (tuple unpacking is FORBIDDEN)
- **DO NOT DO THIS**: `# Unpack parameters for readability` followed by unpacking
- **DO NOT DO THIS**: Any assignment like `x = params[0]` - use `params[0]` INLINE in the equation
- NO intermediate variables for parameters
- NO classes like `Node`, `Expr`, etc.
- NO helper functions inside the EVOLVE block
- NO docstrings or comments

**INPUT VARIABLE NAMING**: The dataset has {n_vars} input variables, named: `{var_example}`
  - Always use zero-indexed naming: `x0`, `x1`, `x2`, ...
  - Use the EXACT variable names shown in the function signature below.

**AVOID NaN PRODUCTION - CRITICAL FOR SUCCESS**:
- **AVOID**: `np.log(x0)` - use `np.log(np.abs(x0) + 1e-8)` instead
- **AVOID**: `np.sqrt(x0)` - use `np.sqrt(np.abs(x0) + 1e-8)` instead
- **AVOID**: `x0 ** x1` - use `np.power(np.abs(x0) + 1e-8, x1)` instead
- **AVOID**: `np.exp(x0)` for large values - use `np.exp(np.clip(x0, -10, 10))` instead
- **AVOID**: Division by zero - use `1.0 / (x0 + 1e-8)` instead of `1.0 / x0`

Problem: Design the equation structure using inputs `{var_example}`; BFGS will optimize the params values.

```python
import numpy as np

# EVOLVE_START
{func_sig}
    return {example_expr}
# EVOLVE_END
```

Available numpy functions: np.sin, np.cos, np.exp, np.log, np.sqrt, np.tan, np.abs"""

    with open(yaml_path, encoding='utf-8') as f:
        lines = f.readlines()

    lines = _replace_block(lines, 'background:', new_background)
    lines = _replace_block(lines, 'prompt_template:', new_prompt)

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Updated {yaml_path} [background + prompt_template] for {benchmark} ({n_vars} vars)")


def update_template_model(benchmark: str, config: dict):
    """Update the template model.py to match the benchmark's variable count."""
    template_path = os.path.join(os.path.dirname(__file__), "sr_algorithm", "model.py")
    if not os.path.exists(template_path):
        print(f"Warning: {template_path} not found, skipping template update")
        return

    ranges = config["ranges"]
    n_vars = len(ranges)
    var_names = [f"x{i}" for i in range(n_vars)]

    var_list = ", ".join([f"{v}: np.ndarray" for v in var_names])
    func_sig = f"def equation({var_list}, params: np.ndarray) -> np.ndarray:"

    arg_items = [f"{v}: Input {v} array shape (N,) in {r}" for v, r in zip(var_names, ranges)]
    args_lines = "        " + "\n        ".join(arg_items)

    if n_vars == 1:
        default_body = "return params[0] * x0 + params[1]"
    elif n_vars == 2:
        default_body = "return params[0] * x0 + params[1] * x1 + params[2]"
    else:
        terms = " + ".join([f"params[{i}] * x{i}" for i in range(n_vars)])
        default_body = f"return {terms} + params[{n_vars}]"

    if n_vars == 1:
        input_parse = """    # Input is JSON array of x0 values
    input_data = json.loads(sys.argv[1])
    x0 = np.array(input_data)"""
        call_args = "x0, params"
        num_params_expr = "len(sig.parameters) - 1"
    else:
        input_parse_lines = [
            "    # Input is JSON array of values",
            "    input_data = json.loads(sys.argv[1])",
        ]
        for i, v in enumerate(var_names):
            input_parse_lines.append(f"    {v} = np.array([row[{i}] for row in input_data])")
        input_parse = "\n".join(input_parse_lines)
        call_args = ", ".join(var_names) + ", params"
        num_params_expr = f"len(sig.parameters) - {n_vars}"

    new_content = f'''"""Symbolic regression model with predefined parameters (LLM + EC style).

Your implementation should be between the special evolution markers.
Implement the equation function that takes inputs {", ".join(var_names)} and parameters params
and returns the predicted values as a numpy array.

All numeric parameters should be stored in the params array passed as the last argument.
Bi-level optimization will automatically optimize these parameters before evaluation.

Function signature:
{func_sig}
"""

import numpy as np


# EVOLVE_START
{func_sig}
    """Predict f({", ".join(var_names)}) given input arrays and parameters params.

    Args:
{args_lines}
        params: Array of parameters to be optimized shape (P,)

    Returns:
        Predicted values array shape (N,)
    """
    {default_body}
# EVOLVE_END


def main():
    """Main entry point for evaluation."""
    import sys
    import json

    if len(sys.argv) < 2:
        sys.exit(1)

{input_parse}

    # Dummy initial parameters for testing
    import inspect
    sig = inspect.signature(equation)
    num_params = {num_params_expr}
    params = np.ones(num_params)

    predictions = equation({call_args})

    # Output predictions as JSON
    result = {{
        "predictions": predictions.tolist()
    }}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
'''

    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Updated {template_path} [{n_vars} vars: {', '.join(var_names)}]")

    import subprocess
    sr_algorithm_dir = os.path.dirname(template_path)
    try:
        subprocess.run(
            ["git", "add", "model.py"],
            cwd=sr_algorithm_dir,
            check=True,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update template for {benchmark} ({n_vars} vars: {', '.join(var_names)})"],
            cwd=sr_algorithm_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Committed template changes to sr_algorithm git repo")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            print("No template changes to commit")
        else:
            print(f"Warning: Failed to commit template changes: {e.stderr}")
    except Exception as e:
        print(f"Warning: Git commit skipped - {e}")


def list_feynman_benchmarks():
    """Print all available Feynman benchmarks."""
    feynman_names = [name for name in BENCHMARKS.keys() if name.startswith("feynman_")]
    print(f"Total Feynman benchmarks: {len(feynman_names)}")
    print("\n".join(sorted(feynman_names)))


def main():
    """Generate and save datasets.

    Set BENCHMARK variable below to choose which problem to generate.
    """
    script_dir = os.path.dirname(__file__)
    train_path = os.path.join(script_dir, "data/train/train_100.txt")
    test_path = os.path.join(script_dir, "data/test/test_50.txt")

    # === CONFIG: Set your benchmark here ===
    # Options:
    #   Nguyen series: nguyen1, nguyen2, ..., nguyen9
    #   Keijzer series: keijzer6, keijzer15
    #   Feynman series: feynman_I.6.2a, feynman_I.6.2, feynman_I.6.2b, ...
    # 
    # To list all Feynman benchmarks, uncomment:
    # list_feynman_benchmarks(); return
    
    BENCHMARK = "feynman_III.15.12"  # Change this to switch problems

    # Validate benchmark
    if BENCHMARK not in BENCHMARKS:
        print(f"Error: Unknown benchmark '{BENCHMARK}'")
        print(f"Available benchmarks (first 20): {list(BENCHMARKS.keys())[:20]}...")
        print(f"Total {len(BENCHMARKS)} benchmarks available")
        return

    config = BENCHMARKS[BENCHMARK]
    ranges = config["ranges"]
    n_vars = len(ranges)
    print(f"Generating data for: {BENCHMARK} ({n_vars} variables)")
    var_names = [f"x{i}" for i in range(n_vars)]
    for name, r in zip(var_names, ranges):
        print(f"  {name} range: {r}")
    print()

    # Generate training data
    train_data = generate_dataset(BENCHMARK, 100, seed=42)
    save_dataset(train_data, train_path)
    print(f"Generated training data: {len(train_data)} samples -> data/train/train_100.txt")

    # Generate test data
    test_data = generate_dataset(BENCHMARK, 50, seed=1234)
    save_dataset(test_data, test_path)
    print(f"Generated test data: {len(test_data)} samples -> data/test/test_50.txt")

    # Auto-update YAML configuration and template model
    update_yaml_config(BENCHMARK, config)
    update_template_model(BENCHMARK, config)

    print(f"\nDone! Configuration automatically synchronized for '{BENCHMARK}'.")


if __name__ == "__main__":
    main()