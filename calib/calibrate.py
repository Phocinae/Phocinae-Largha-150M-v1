"""apply_gamma — per-decision power calibration for Phocinae-Largha-150M-v1.

q ∝ p ** gamma  (per decision, normalized). Monotone; argmax and the 0.5
threshold of noul answers are unchanged, so accuracy is invariant.
Recommended: gamma=4.33 (en face), gamma=2.51 (zh face). gamma=1 = raw.
"""
from __future__ import annotations


def apply_gamma(probs: dict, gamma: float = 1.0) -> dict:
    """probs: {option_id: probability}. Returns calibrated dict (same keys)."""
    if gamma == 1.0:
        return dict(probs)
    powered = {k: (max(float(v), 0.0) ** gamma) for k, v in probs.items()}
    s = sum(powered.values())
    if s <= 0:
        raise ValueError("apply_gamma: all probabilities are zero")
    return {k: v / s for k, v in powered.items()}


def calibrate_response(probabilities: dict, gamma: float = 4.33) -> dict:
    """Calibrate a full response: {qid: {option: prob}} -> {qid: {option: prob}}."""
    return {qid: apply_gamma(p, gamma) for qid, p in probabilities.items()}
