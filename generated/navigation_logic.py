def decide_next_move(state):
    if state.get("front_blocked"):
        if not state.get("left_blocked"):
            return "LEFT"
        if not state.get("right_blocked"):
            return "RIGHT"
        return "STOP"
    if state.get("goal_on_left"):
        return "LEFT"
    if state.get("goal_on_right"):
        return "RIGHT"
    return "FORWARD"