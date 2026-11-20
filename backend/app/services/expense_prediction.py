"""Account-scoped next-month expense prediction with chronological validation.

The service deliberately operates only on completed months containing recorded
expense transactions. It never fills a missing month with zero and features for
month *t* use values available no later than month *t - 1*.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


MIN_COMPLETED_MONTHS = 12
LAG_COUNT = 3
HOLDOUT_OBSERVATIONS = 3
FEATURE_NAMES = (
    "lag_1_expenses",
    "lag_2_expenses",
    "lag_3_expenses",
    "rolling_3_expenses",
    "three_month_change",
    "target_month_sin",
    "target_month_cos",
)
ARTIFACT_VERSION = 1


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _contiguous_completed_expense_months(monthly: list[dict], as_of: date) -> list[dict]:
    """Return the newest continuous history ending in the last completed month."""
    latest_completed = _previous_month(as_of.year, as_of.month)
    rows = {
        (row["year"], row["month_number"]): row
        for row in monthly
        if row.get("expense_transaction_count", 0) > 0
    }
    chain: list[dict] = []
    cursor = latest_completed
    while cursor in rows:
        chain.append(rows[cursor])
        cursor = _previous_month(*cursor)
    return list(reversed(chain))


def _features_for_target(history: list[dict], target_year: int, target_month: int) -> list[float]:
    """Use exactly the three earlier recorded values; never the target label."""
    lag_1, lag_2, lag_3 = (float(history[-1]["total_expenses"]), float(history[-2]["total_expenses"]), float(history[-3]["total_expenses"]))
    angle = 2 * math.pi * target_month / 12
    return [
        lag_1,
        lag_2,
        lag_3,
        (lag_1 + lag_2 + lag_3) / 3,
        lag_1 - lag_3,
        math.sin(angle),
        math.cos(angle),
    ]


def build_time_based_training_rows(monthly: list[dict], *, as_of: date | None = None) -> dict:
    """Build supervised rows from contiguous recorded monthly expense totals."""
    as_of = as_of or date.today()
    history = _contiguous_completed_expense_months(monthly, as_of)
    features: list[list[float]] = []
    targets: list[float] = []
    periods: list[str] = []
    for index in range(LAG_COUNT, len(history)):
        target = history[index]
        features.append(_features_for_target(history[index - LAG_COUNT:index], target["year"], target["month_number"]))
        targets.append(float(target["total_expenses"]))
        periods.append(f"{target['year']:04d}-{target['month_number']:02d}")
    return {
        "history": history,
        "features": features,
        "targets": targets,
        "target_periods": periods,
        "feature_names": list(FEATURE_NAMES),
        "data_fingerprint": _fingerprint(history),
    }


def _fingerprint(history: list[dict]) -> str:
    values = [
        [row["year"], row["month_number"], str(row["total_expenses"])]
        for row in history
    ]
    return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode("utf-8")).hexdigest()


def _metric_bundle(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(math.sqrt(mean_squared_error(actual, predicted)))
    # R² is not meaningful with fewer than two varied holdout observations.
    r_squared = float(r2_score(actual, predicted)) if len(actual) >= 2 and not np.allclose(actual, actual[0]) else None
    return {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": None if r_squared is None else round(r_squared, 4)}


def _candidate_models() -> dict[str, Any]:
    return {
        "linear_regression": LinearRegression(),
        "random_forest_regressor": RandomForestRegressor(
            n_estimators=160, min_samples_leaf=1, random_state=42, n_jobs=1
        ),
        "gradient_boosting_regressor": GradientBoostingRegressor(
            n_estimators=80, learning_rate=0.05, max_depth=2, random_state=42,
        ),
    }


def _artifact_path(model_store_dir: str | Path, user_id: int) -> Path:
    return Path(model_store_dir) / f"expense_prediction_user_{int(user_id)}.joblib"


def _load_artifact(path: Path, *, user_id: int, fingerprint: str) -> dict | None:
    if not path.is_file():
        return None
    try:
        artifact = joblib.load(path)
    except Exception:
        return None
    metadata = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
    if not (
        metadata.get("version") == ARTIFACT_VERSION
        and metadata.get("user_id") == user_id
        and metadata.get("data_fingerprint") == fingerprint
        and metadata.get("feature_names") == list(FEATURE_NAMES)
    ):
        return None
    return artifact


def _save_artifact(path: Path, artifact: dict) -> None:
    """Atomically save an app-owned artifact outside the static/web directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.stem}-", suffix=".tmp", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(artifact, temporary_path)
        os.replace(temporary_path, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


def _insufficient_result(training: dict, *, as_of: date) -> dict:
    next_year, next_month = _next_month(as_of.year, as_of.month)
    history_count = len(training["history"])
    return {
        "available": False,
        "predicted_expenses": None,
        "forecast_period": f"{next_year:04d}-{next_month:02d}",
        "historical_months": history_count,
        "required_historical_months": MIN_COMPLETED_MONTHS,
        "training_observations": len(training["targets"]),
        "validation_observations": 0,
        "selected_model": None,
        "model_source": None,
        "feature_names": list(FEATURE_NAMES),
        "evaluation": None,
        "baseline_performance": None,
        "candidate_models": [],
        "explanation": (
            "Not enough historical financial data is available to generate a reliable next-month expense prediction. "
            f"Record {MIN_COMPLETED_MONTHS} consecutive completed months with expense transactions; {history_count} are currently available."
        ),
    }


def _fit_prediction(training: dict) -> tuple[dict, Any]:
    features = np.asarray(training["features"], dtype=float)
    targets = np.asarray(training["targets"], dtype=float)
    split = len(targets) - HOLDOUT_OBSERVATIONS
    x_train, x_test = features[:split], features[split:]
    y_train, y_test = targets[:split], targets[split:]
    baseline = x_test[:, 0]
    baseline_metrics = _metric_bundle(y_test, baseline)
    candidates = []
    fitted_models: dict[str, Any] = {}
    for name, model in _candidate_models().items():
        model.fit(x_train, y_train)
        metrics = _metric_bundle(y_test, model.predict(x_test))
        candidates.append({"name": name, **metrics})
        fitted_models[name] = model
    candidates.sort(key=lambda row: (row["mae"], row["rmse"], row["name"]))
    best = candidates[0]
    # Deploy an ML model only when it improves validation MAE over the naive
    # previous-month baseline. The baseline remains a valid saved selection.
    if best["mae"] < baseline_metrics["mae"]:
        selected_name = best["name"]
        selected_model = fitted_models[selected_name]
        selected_metrics = {key: best[key] for key in ("mae", "rmse", "r2")}
    else:
        selected_name = "previous_month_baseline"
        selected_model = None
        selected_metrics = baseline_metrics
    return {
        "selected_model": selected_name,
        "evaluation": selected_metrics,
        "baseline_performance": baseline_metrics,
        "candidate_models": candidates,
        "training_observations": len(y_train),
        "validation_observations": len(y_test),
    }, selected_model


def predict_next_month_expenses(
    monthly: list[dict],
    *,
    user_id: int,
    as_of: date | None = None,
    model_store_dir: str | Path | None = None,
) -> dict:
    """Train/load the best validated account model and predict the next month."""
    as_of = as_of or date.today()
    training = build_time_based_training_rows(monthly, as_of=as_of)
    if len(training["history"]) < MIN_COMPLETED_MONTHS or len(training["targets"]) <= HOLDOUT_OBSERVATIONS:
        return _insufficient_result(training, as_of=as_of)

    artifact = None
    artifact_path = None
    if model_store_dir is not None:
        artifact_path = _artifact_path(model_store_dir, user_id)
        artifact = _load_artifact(artifact_path, user_id=user_id, fingerprint=training["data_fingerprint"])
    if artifact is None:
        metadata, selected_model = _fit_prediction(training)
        artifact = {
            "metadata": {
                "version": ARTIFACT_VERSION,
                "user_id": user_id,
                "data_fingerprint": training["data_fingerprint"],
                "feature_names": list(FEATURE_NAMES),
                **metadata,
            },
            "model": selected_model,
        }
        model_source = "trained"
        if artifact_path is not None:
            _save_artifact(artifact_path, artifact)
    else:
        model_source = "saved_model"

    metadata = artifact["metadata"]
    # Keep the same horizon as the existing Phase 5 cash-flow forecast: the
    # calendar month after the current partial month. The latest completed
    # expense month remains the final permitted lag input.
    latest = training["history"][-1]
    target_year, target_month = _next_month(as_of.year, as_of.month)
    prediction_features = np.asarray([_features_for_target(training["history"][-LAG_COUNT:], target_year, target_month)], dtype=float)
    selected_name = metadata["selected_model"]
    raw_prediction = prediction_features[0, 0] if selected_name == "previous_month_baseline" else float(artifact["model"].predict(prediction_features)[0])
    predicted = Decimal(str(max(0.0, raw_prediction))).quantize(Decimal("0.01"))
    latest_expenses = Decimal(str(latest["total_expenses"])).quantize(Decimal("0.01"))
    difference = (predicted - latest_expenses).quantize(Decimal("0.01"))
    change_percent = (difference / latest_expenses * Decimal("100")).quantize(Decimal("0.01")) if latest_expenses else None
    model_label = selected_name.replace("_", " ")
    return {
        "available": True,
        "predicted_expenses": predicted,
        "forecast_period": f"{target_year:04d}-{target_month:02d}",
        "historical_months": len(training["history"]),
        "required_historical_months": MIN_COMPLETED_MONTHS,
        "training_observations": metadata["training_observations"],
        "validation_observations": metadata["validation_observations"],
        "selected_model": selected_name,
        "model_source": model_source,
        "feature_names": list(FEATURE_NAMES),
        "evaluation": metadata["evaluation"],
        "baseline_performance": metadata["baseline_performance"],
        "candidate_models": metadata["candidate_models"],
        "latest_recorded_expenses": latest_expenses,
        "predicted_change_from_latest": difference,
        "predicted_change_percent": change_percent,
        "explanation": (
            f"Next-month expenses are predicted with {model_label}, selected from chronological validation against "
            "linear regression, random forest, gradient boosting, and a previous-month baseline. "
            "This prediction uses completed recorded expense months only and is not a guarantee."
        ),
    }
