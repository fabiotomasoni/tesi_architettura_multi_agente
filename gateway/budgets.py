"""Budget fidati all'avvio, invarianti nel confronto sperimentale."""
from dataclasses import asdict, dataclass
import math
import os


@dataclass(frozen=True)
class Budgets:
    activity_seconds: float = 120
    model_seconds: float = 90
    source_seconds: float = 30
    transport_grace_seconds: float = 5

    @property
    def a2a_seconds(self):
        return self.activity_seconds + self.transport_grace_seconds

    def public(self):
        return asdict(self)


ENV_KEYS = {
    'activity_seconds':'TESI_ACTIVITY_TIMEOUT_SECONDS',
    'model_seconds':'TESI_MODEL_TIMEOUT_SECONDS',
    'source_seconds':'TESI_SOURCE_TIMEOUT_SECONDS',
    'transport_grace_seconds':'TESI_TRANSPORT_GRACE_SECONDS',
}


def load_budgets(environment):
    defaults = Budgets()
    try:
        values = {name:float(environment.get(key, getattr(defaults,name))) for name,key in ENV_KEYS.items()}
        if any(not math.isfinite(v) or not 0 < v <= 3600 for v in values.values()):
            raise ValueError()
        result = Budgets(**values)
        if result.model_seconds > result.activity_seconds or result.source_seconds > result.activity_seconds:
            raise ValueError()
        if environment.get('TESI_EXPERIMENT','off')!='off' and result != defaults:
            raise ValueError()
        return result
    except (ValueError,TypeError,OverflowError):
        raise RuntimeError('Budget non validi; il confronto sperimentale richiede i valori predefiniti.') from None


BUDGETS = load_budgets(os.environ)
