"""Symbolic regression model with predefined parameters (LLM + EC style).

Your implementation should be between the special evolution markers.
Implement the equation function that takes inputs x0, x1, x2 and parameters params
and returns the predicted values as a numpy array.

All numeric parameters should be stored in the params array passed as the last argument.
Bi-level optimization will automatically optimize these parameters before evaluation.

Function signature:
def equation(x0: np.ndarray, x1: np.ndarray, x2: np.ndarray, params: np.ndarray) -> np.ndarray:
"""

import numpy as np


# EVOLVE_START
def equation(x0: np.ndarray, x1: np.ndarray, x2: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Predict f(x0, x1, x2) given input arrays and parameters params.

    Args:
        x0: Input x0 array shape (N,) in (1, 5)
        x1: Input x1 array shape (N,) in (1, 5)
        x2: Input x2 array shape (N,) in (1, 5)
        params: Array of parameters to be optimized shape (P,)

    Returns:
        Predicted values array shape (N,)
    """
    return params[0] * x0 + params[1] * x1 + params[2] * x2 + params[3]
# EVOLVE_END


def main():
    """Main entry point for evaluation."""
    import sys
    import json

    if len(sys.argv) < 2:
        sys.exit(1)

    # Input is JSON array of values
    input_data = json.loads(sys.argv[1])
    x0 = np.array([row[0] for row in input_data])
    x1 = np.array([row[1] for row in input_data])
    x2 = np.array([row[2] for row in input_data])

    # Dummy initial parameters for testing
    import inspect
    sig = inspect.signature(equation)
    num_params = len(sig.parameters) - 3
    params = np.ones(num_params)

    predictions = equation(x0, x1, x2, params)

    # Output predictions as JSON
    result = {
        "predictions": predictions.tolist()
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
