from __future__ import annotations

from typing import Any

from .db import Database


FIXED_AI_TOP6 = [2, 3, 5, 7, 8, 10]
_OUTSIDE = [1, 4, 6, 9]
_INSTALLED = False
_ORIGINAL_SAVE_FORECAST = Database.save_forecast
_ORIGINAL_SAVE_FORECAST_WITH_STRATEGIES = Database.save_forecast_with_strategies


def _fixed_sets(
    *,
    source: str,
    top6: list[int],
    top7: list[int],
    probabilities: list[float],
) -> tuple[list[int], list[int]]:
    """Hard output contract: only formal AI forecasts are fixed to 235780.

    Native/local forecasts must remain untouched and keep their original dynamic
    number-selection behaviour.
    """
    if source != "ai":
        return list(top6), list(top7)

    if len(probabilities) == 10:
        hedge = max(_OUTSIDE, key=lambda number: float(probabilities[number - 1]))
    else:
        hedge = next((number for number in top7 if number in _OUTSIDE), _OUTSIDE[0])
    return list(FIXED_AI_TOP6), [*FIXED_AI_TOP6, hedge]


def _guarded_save_forecast(self: Database, **kwargs: Any) -> int | None:
    normalized_top6, normalized_top7 = _fixed_sets(
        source=str(kwargs.get("source") or ""),
        top6=list(kwargs.get("top6") or []),
        top7=list(kwargs.get("top7") or []),
        probabilities=list(kwargs.get("probabilities") or []),
    )
    kwargs["top6"] = normalized_top6
    kwargs["top7"] = normalized_top7
    return _ORIGINAL_SAVE_FORECAST(self, **kwargs)


def _guarded_save_forecast_with_strategies(self: Database, **kwargs: Any) -> int | None:
    normalized_top6, normalized_top7 = _fixed_sets(
        source=str(kwargs.get("source") or ""),
        top6=list(kwargs.get("top6") or []),
        top7=list(kwargs.get("top7") or []),
        probabilities=list(kwargs.get("probabilities") or []),
    )
    kwargs["top6"] = normalized_top6
    kwargs["top7"] = normalized_top7
    return _ORIGINAL_SAVE_FORECAST_WITH_STRATEGIES(self, **kwargs)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    Database.save_forecast = _guarded_save_forecast
    Database.save_forecast_with_strategies = _guarded_save_forecast_with_strategies
    _INSTALLED = True
