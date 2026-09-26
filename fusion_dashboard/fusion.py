from states import STATE_LABELS


def fuse(node_a, node_b):
    """
    node_a / node_b: {"state": int, "confidence": float, ...} or None.

    Returns {"state": int | None, "confidence": float, "agree": bool | None, "note": str}.
    """
    if node_a is None and node_b is None:
        return {
            "state": None,
            "confidence": 0.0,
            "agree": None,
            "note": "No data from either node yet.",
        }

    if node_a is None or node_b is None:
        only = node_b if node_a is None else node_a
        missing = "Node A" if node_a is None else "Node B"
        return {
            "state": only["state"],
            "confidence": only["confidence"],
            "agree": None,
            "note": f"{missing} offline - showing the other node's reading only.",
        }

    a_state, a_conf = node_a["state"], node_a["confidence"]
    b_state, b_conf = node_b["state"], node_b["confidence"]

    if a_state == b_state:
        return {
            "state": a_state,
            "confidence": round((a_conf + b_conf) / 2, 2),
            "agree": True,
            "note": "Nodes agree.",
        }

    # Disagreement
    if a_state > b_state:
        fused_state, fused_conf = a_state, a_conf
    else:
        fused_state, fused_conf = b_state, b_conf

    return {
        "state": fused_state,
        "confidence": fused_conf,
        "agree": False,
        "note": (
            f"Nodes disagree (A: {STATE_LABELS[a_state]}, "
            f"B: {STATE_LABELS[b_state]}) - escalating to the more severe state."
        ),
    }
