from __future__ import annotations
from dataclasses import dataclass
from model import SIRParams, SIRState   # import absolu (pas de package)


@dataclass
class Scenario:
    name: str
    beta_multiplier: float = 1.0   # mesures sanitaires: reduit beta (ex: 0.5 = distanciation)
    vax_fraction: float    = 0.0   # fraction de S0 vaccinees -> transferee vers R0


# Scenarios predefinies utiles
SCENARIO_BASELINE    = Scenario(name="Baseline",        beta_multiplier=1.0, vax_fraction=0.0)
SCENARIO_DISTANCING  = Scenario(name="Distanciation",   beta_multiplier=0.5, vax_fraction=0.0)
SCENARIO_VACCINATION = Scenario(name="Vaccination 50%", beta_multiplier=1.0, vax_fraction=0.5)
SCENARIO_COMBINED    = Scenario(name="Combine",         beta_multiplier=0.6, vax_fraction=0.4)


def apply_scenario(
    params: SIRParams,
    init: SIRState,
    sc: Scenario,
) -> tuple[SIRParams, SIRState]:
    """Applique un scenario sur les parametres et l'etat initial."""
    p = SIRParams(beta=params.beta * sc.beta_multiplier, gamma=params.gamma)

    v = max(0.0, min(sc.vax_fraction, 1.0))
    moved = v * init.S
    st = SIRState(S=init.S - moved, I=init.I, R=init.R + moved)

    return p, st