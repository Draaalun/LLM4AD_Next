#!/usr/bin/env python3
"""Algorithm file for bipedal_walker controller.

This file contains the evolvable walker_controller function.
The LLM will modify the code between EVOLVE_START and EVOLVE_END markers.
"""

import json
import sys

# ===== EVOLVABLE SECTION =====
# The LLM will modify the code between these markers.
# Put all imports needed by the evolvable function inside the markers.

# EVOLVE_START
import math

def walker_controller(observation: list) -> list:
    """Baseline heuristic controller for BipedalWalker-v3.

    Simple PD controller using hull angle and angular velocity to balance,
    and a constant forward torque.

    Args:
        observation: list of 24 floats (see specification for order).

    Returns:
        list of 4 floats in [-1, 1]: [hip1_torque, knee1_torque, hip2_torque, knee2_torque]
    """
    # Extract relevant observations (indices according to specification)
    hull_angle = observation[0]          # hull angle
    hull_angular_vel = observation[1]    # hull angular velocity
    vel_x = observation[2]               # velocity x
    # hip joint angles and speeds (indices 4,5 for hip1; 8,9 for hip2)
    hip1_angle = observation[4]
    hip1_speed = observation[5]
    hip2_angle = observation[8]
    hip2_speed = observation[9]
    # ground contact flags (indices 8? actually leg1 flag at index 8? 
    # According to spec: leg1 ground contact flag is observation[8]? 
    # Let's double-check spec: indices: hull angle(0), hull angular velocity(1), velocity x(2), velocity y(3),
    # hip1 angle(4), hip1 speed(5), knee1 angle(6), knee1 speed(7), leg1 flag(8),
    # hip2 angle(9), hip2 speed(10), knee2 angle(11), knee2 speed(12), leg2 flag(13),
    # and 10 lidar range finders (14-23).
    # So leg1 flag = obs[8], leg2 flag = obs[13].
    leg1_contact = observation[8]
    leg2_contact = observation[13]

    # Simple PD controller to keep hull upright
    # Target hull angle 0, angular velocity 0
    kp_balance = 20.0
    kd_balance = 5.0
    balance_torque = kp_balance * (-hull_angle) + kd_balance * (-hull_angular_vel)

    # Forward movement: apply constant torque to hips
    forward_torque = 0.5  # moderate forward push

    # Stabilize knees: keep them slightly bent (angle near 0.5 rad)
    target_knee_angle = 0.5  # slightly bent
    kp_knee = 10.0
    kd_knee = 2.0

    knee1_torque = kp_knee * (target_knee_angle - observation[6]) + kd_knee * (-observation[7])
    knee2_torque = kp_knee * (target_knee_angle - observation[11]) + kd_knee * (-observation[12])

    # Combine: each hip gets balance + forward component
    # Leg 1 (left) and Leg 2 (right) can be symmetric
    hip1_torque = forward_torque + balance_torque
    hip2_torque = forward_torque - balance_torque  # opposite sign for right leg

    # Clip to [-1, 1]
    actions = [
        max(-1.0, min(1.0, hip1_torque)),
        max(-1.0, min(1.0, knee1_torque)),
        max(-1.0, min(1.0, hip2_torque)),
        max(-1.0, min(1.0, knee2_torque)),
    ]

    return actions
# EVOLVE_END
# =============================


def process(data):
    """Fixed wrapper that calls the evolvable function and formats the result.

    This function is NOT evolved - it provides a stable interface.
    For the bipedal_walker task, the data is the observation list.
    """
    observation = data.get("observation", [0.0]*24)
    action = walker_controller(observation)
    return {
        "action": action,
        "mean_score": None,  # Evaluator computes this
    }


def main():
    """Entry point for standalone testing.

    Reads JSON input from command line (expects {"observation": [...]}),
    runs the controller, prints JSON result.
    """
    if len(sys.argv) < 2:
        print("Usage: python controller.py '<input_json>'", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    result = process(input_data)
    print(json.dumps(result))


if __name__ == "__main__":
    main()