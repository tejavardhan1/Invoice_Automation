from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

import mlflow


def configure_mlflow(tracking_uri: Optional[str] = None, experiment_name: str = "ai-invoice-expense-automation") -> None:
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)


@contextmanager
def start_run(run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> Generator[mlflow.ActiveRun, None, None]:
    with mlflow.start_run(run_name=run_name, tags=tags) as run:
        yield run


def log_model_params(params: Dict[str, Any]) -> None:
    mlflow.log_params(params)


def log_model_metrics(metrics: Dict[str, float]) -> None:
    mlflow.log_metrics(metrics)


__all__ = ["configure_mlflow", "start_run", "log_model_params", "log_model_metrics"]
