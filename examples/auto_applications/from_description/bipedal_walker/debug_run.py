#!/usr/bin/env python3
"""Debug script to test walker_controller directly on a dummy observation."""

# Note: This script assumes controller.py is in the bipedal_walker_algorithm subdirectory.

import sys
import os
from pathlib import Path

# Add the algorithm directory to path
sys.path.insert(0, str(Path(__file__).parent / "bipedal_walker_algorithm"))
from controller import walker_controller

def main():
    # Create a sample observation (24 floats) as per specification
    # We'll use a typical standing pose with slight tilt.
    sample_obs = [
        0.02,       # hull angle (slightly tilted)
        -0.01,      # hull angular velocity
        0.5,        # velocity x (moving forward slowly)
        0.0,        # velocity y
        0.1,        # hip1 angle (slightly forward)
        -0.05,      # hip1 speed
        -0.2,       # knee1 angle (bent)
        0.03,       # knee1 speed
        1.0,        # leg1 ground contact flag (1 = contact)
        -0.1,       # hip2 angle (slightly backward)
        0.05,       # hip2 speed
        -0.2,       # knee2 angle (bent)
        -0.03,      # knee2 speed
        1.0,        # leg2 ground contact flag
        # 10 lidar distances (all set to 1.0 for simplicity)
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    ]

    # Ensure length is 24
    assert len(sample_obs) == 24, f"Observation length {len(sample_obs)} != 24"

    # Run controller
    try:
        actions = walker_controller(sample_obs)
    except Exception as e:
        print(f"Error calling walker_controller: {e}")
        sys.exit(1)

    # Check output format
    if not isinstance(actions, list) or len(actions) != 4:
        print(f"Invalid output: expected list of 4 floats, got {actions}")
        sys.exit(1)

    # Check each action is in [-1, 1]
    for i, a in enumerate(actions):
        if not (-1.0 <= a <= 1.0):
            print(f"Action {i} ({a}) out of [-1, 1]")
            sys.exit(1)

    print("DEBUG_RUN SUCCESS")
    print(f"Input observation: {sample_obs}")
    print(f"Output actions: {actions}")

if __name__ == "__main__":
    main()