"""Least-squares provisional fits, task section 10; numpy only."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class FitResult:
    """Fitted parameters, R2 in stated space, MPa R2 and MPa RMSE."""
    model_name: str
    values: dict[str, float]
    n_rows: int
    r2: float
    r2_space: str
    r2_mpa: float
    rmse_mpa: float


@dataclass(frozen=True, eq=False)
class FitArrays:
    """Matching fitting arrays corrected to 28-day cylinder strength, MPa."""
    wc: np.ndarray
    cw: np.ndarray
    volume_ratio: np.ndarray
    strength_mpa: np.ndarray


def _arrays(x: np.ndarray, strength_mpa: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    strength_mpa = np.asarray(strength_mpa, dtype=float)
    if x.ndim != 1 or x.shape != strength_mpa.shape or len(x) < 3:
        raise ValueError('Fit requires matching 1-D arrays with >=3 rows')
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(strength_mpa)):
        raise ValueError('Fit values must be finite')
    if np.any(x <= 0) or np.any(strength_mpa <= 0):
        raise ValueError('Fit values must be positive')
    return x, strength_mpa


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    residual = float(np.sum((actual - predicted)**2))
    total = float(np.sum((actual - np.mean(actual))**2))
    if total == 0:
        return 1.0 if residual == 0 else 0.0
    return 1 - residual / total


def _result(name: str, values: dict[str, float], actual: np.ndarray,
            predicted: np.ndarray, log_space: bool = False) -> FitResult:
    r2_mpa = _r2(actual, predicted)
    r2 = _r2(np.log(actual), np.log(predicted)) if log_space else r2_mpa
    rmse_mpa = float(np.sqrt(np.mean((actual-predicted)**2)))
    return FitResult(name, values, len(actual), r2, 'log' if log_space else 'MPa', r2_mpa, rmse_mpa)


def fit_abrams(wc: np.ndarray, strength_mpa: np.ndarray) -> FitResult:
    """ln(f MPa)=ln(A)-ln(B)*wc, ordinary least squares (task section 10)."""
    wc, strength_mpa = _arrays(wc, strength_mpa)
    if np.ptp(wc) == 0:
        raise ValueError('Abrams fit requires distinct wc values')
    slope, intercept = np.polyfit(wc, np.log(strength_mpa), 1)
    a, b = float(np.exp(intercept)), float(np.exp(-slope))
    if not np.isfinite(a) or not np.isfinite(b) or b <= 1:
        raise ValueError('Abrams fit must produce finite A and decreasing strength (B>1)')
    return _result('abrams', {'A': a, 'B': b}, strength_mpa, a / b**wc, True)


def fit_bolomey(cw: np.ndarray, strength_mpa: np.ndarray) -> FitResult:
    """f MPa=K*(C/W-0.5); K=sum(f*g)/sum(g*g), through origin."""
    cw, strength_mpa = _arrays(cw, strength_mpa)
    g = cw - 0.5
    if np.any(g <= 0):
        raise ValueError('Bolomey fit requires C/W > 0.5')
    k = float(np.dot(strength_mpa, g) / np.dot(g, g))
    return _result('bolomey', {'K': k}, strength_mpa, k*g)


def fit_feret(volume_ratio: np.ndarray, strength_mpa: np.ndarray) -> FitResult:
    """f MPa=K*r**2, r=Vc/(Vc+Vw+Va); K=sum(f*r**2)/sum(r**4)."""
    volume_ratio, strength_mpa = _arrays(volume_ratio, strength_mpa)
    if np.any(volume_ratio > 1):
        raise ValueError('Feret volume ratio must be <=1')
    g = volume_ratio**2
    k = float(np.dot(strength_mpa, g) / np.dot(g, g))
    return _result('feret', {'K': k}, strength_mpa, k*g)


def fit_all(arrays: FitArrays) -> dict[str, FitResult]:
    """Fit all parametric models to the same >=3 corrected observations."""
    return {'abrams':fit_abrams(arrays.wc,arrays.strength_mpa),
        'bolomey':fit_bolomey(arrays.cw,arrays.strength_mpa),
        'feret':fit_feret(arrays.volume_ratio,arrays.strength_mpa)}


def comparison_table(results: dict[str, FitResult]) -> tuple[tuple[str,int,float,float,float], ...]:
    """(Model,n,R2 in stated space,R2 MPa,RMSE MPa), retaining input order."""
    return tuple((name,result.n_rows,result.r2,result.r2_mpa,result.rmse_mpa)
                 for name,result in results.items())
