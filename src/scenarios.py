from __future__ import annotations
from dataclasses import dataclass
from .model import SIRParams, SIRState

@dataclass
class Scenario:
    name: str
    beta_multiplier: float = 1.0   # mesures sanitaires (réduit beta)
    vax_fraction: float = 0.0      # fraction de S0 vaccinée -> transférée vers R0

def apply_scenario(params: SIRParams, init: SIRState, sc: Scenario) -> tuple[SIRParams, SIRState]:
    # Mesures sanitaires
    p = SIRParams(beta=params.beta * sc.beta_multiplier, gamma=params.gamma)

    # Vaccination (déplacer une fraction de S vers R au départ)
    v = max(0.0, min(sc.vax_fraction, 1.0))
    moved = v * init.S
    st = SIRState(S=init.S - moved, I=init.I, R=init.R + moved)

    return p, st
