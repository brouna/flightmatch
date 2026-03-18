"""Celery task for ML model retraining."""
import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.ml.retrain_model_task", bind=True)
def retrain_model_task(self):
    """Run offline LightGBM training."""
    from ml.train import train
    result = train()
    # Reload model in scorer
    from app.matching.scorer import reload_model
    reload_model()
    return result
