"""LunarLander control policy implementation.

This file contains the policy function to be evolved by LLM4AD.
The code between EVOLVE_START and EVOLVE_END markers will be
modified by LLM during evolution.

The policy function is called at each time step with:
- s: Current state [x, y, vx, vy, angle, angular_velocity, left_leg, right_leg]
- last_action: Action taken in previous step (0-3)
- s_pre: State before last action was executed

The function should return an action:
- 0: do nothing
- 1: fire left orientation engine (rotate counter-clockwise)
- 2: fire main engine (thrust up)
- 3: fire right orientation engine (rotate clockwise)
"""

import json
import sys

import numpy as np


# ===== EVOLVABLE SECTION =====
# The LLM will modify the code between these markers
# EVOLVE_START
def choose_action(s, last_action, s_pre):
    """Selects an action for LunarLander to achieve safe landing.

    Args:
        s: Current state vector with 8 elements:
            s[0] - horizontal position (x)
            s[1] - vertical position (y)
            s[2] - horizontal velocity (vx)
            s[3] - vertical velocity (vy)
            s[4] - angle (radians)
            s[5] - angular velocity
            s[6] - 1 if left leg is in contact with ground, else 0
            s[7] - 1 if right leg is in contact with ground, else 0

        last_action: Action taken in previous step (0-3)
        s_pre: State vector before last action was executed

    Returns:
        int: The chosen action for the next step. One of:
            0 - do nothing
            1 - fire left orientation engine
            2 - fire main (upward) engine
            3 - fire right orientation engine
    """
    # Simple heuristic control: target angle towards center, maintain hover

    # Calculate target angle based on horizontal position and velocity
    angle_targ = s[0] * 0.5 + s[2] * 1.0

    # Clamp target angle to prevent excessive tilting
    if angle_targ > 0.4:
        angle_targ = 0.4
    if angle_targ < -0.4:
        angle_targ = -0.4

    # Target hover altitude based on horizontal offset
    # Keep higher when far from center for maneuvering
    hover_targ = 0.55 * np.abs(s[0])

    # Calculate angle and hover corrections
    angle_todo = (angle_targ - s[4]) * 0.5 - s[5] * 1.0
    hover_todo = (hover_targ - s[1]) * 0.5 - s[3] * 0.5

    # Special handling when legs have contact with ground
    # Focus on reducing fall speed instead of maintaining hover
    if s[6] or s[7]:
        angle_todo = 0
        hover_todo = -s[3] * 0.5

    # Select action based on priorities
    a = 0
    if hover_todo > np.abs(angle_todo) and hover_todo > 0.05:
        a = 2  # Fire main engine (highest priority)
    elif angle_todo < -0.05:
        a = 3  # Fire right engine (rotate clockwise)
    elif angle_todo > 0.05:
        a = 1  # Fire left engine (rotate counter-clockwise)

    return a
# EVOLVE_END
# =============================


def main():
    """Entry point for command-line execution.

    Expected usage:
        python choose_action.py '{"s": [...], "last_action": 0, "s_pre": [...]}'

    Input format (JSON):
    {
        "s": [x, y, vx, vy, angle, angular_velocity, left_leg, right_leg],
        "last_action": 0,
        "s_pre": [x_prev, y_prev, vx_prev, vy_prev, angle_prev, angular_velocity_prev, left_leg_prev, right_leg_prev]
    }

    Output format (JSON):
    {
        "action": 0
    }
    """
    if len(sys.argv) < 2:
        print("Error: No input data provided", file=sys.stderr)
        sys.exit(1)

    try:
        # Parse input JSON
        input_data = json.loads(sys.argv[1])

        s = input_data.get("s", [])
        last_action = input_data.get("last_action", 0)
        s_pre = input_data.get("s_pre", [])

        # Validate input
        if not s or len(s) != 8:
            print('Error: Invalid state vector "s"', file=sys.stderr)
            sys.exit(1)

        # Call policy function
        action = choose_action(s, last_action, s_pre)

        # Validate action
        if action not in [0, 1, 2, 3]:
            action = 0

        # Output result as JSON
        output = {"action": int(action)}
        print(json.dumps(output))

    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
