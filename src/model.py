from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class SIRParams:
    beta: float   # contagiosité
    gamma: float  # guérison

@dataclass
class SIRState:
    S: float
    I: float
    R: float

def simulate_sir(N: float, params: SIRParams, init: SIRState, days: int, dt: float = 1.0) -> pd.DataFrame:
    steps = int(np.ceil(days / dt))
    t = np.arange(0, steps + 1) * dt

    S = np.zeros(steps + 1); I = np.zeros(steps + 1); R = np.zeros(steps + 1)
    S[0], I[0], R[0] = init.S, init.I, init.R

    for k in range(steps):
        dS = -params.beta * S[k] * I[k] / N
        dI =  params.beta * S[k] * I[k] / N - params.gamma * I[k]
        dR =  params.gamma * I[k]

        S[k+1] = max(S[k] + dS * dt, 0.0)
        I[k+1] = max(I[k] + dI * dt, 0.0)
        R[k+1] = max(R[k] + dR * dt, 0.0)

        # correction pour conserver N
        total = S[k+1] + I[k+1] + R[k+1]
        if total > 0:
            f = N / total
            S[k+1] *= f; I[k+1] *= f; R[k+1] *= f

    return pd.DataFrame({"t": t, "S": S, "I": I, "R": R})

def indicators(sim: pd.DataFrame) -> dict:
    I = sim["I"].to_numpy()
    t = sim["t"].to_numpy()
    peak_I = float(I.max())
    t_peak = float(t[I.argmax()])

    thr = 1.0
    active = I > thr
    duration = 0.0
    if active.any():
        t_start = float(t[active.argmax()])
        t_end = float(t[len(active)-1 - active[::-1].argmax()])
        duration = t_end - t_start

    return {"peak_I": peak_I, "t_peak": t_peak, "duration_days": duration}
