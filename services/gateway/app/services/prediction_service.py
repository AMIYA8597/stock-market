"""
ML prediction service implementation.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.market_data import Prediction
from app.schemas.predictions import (
    EnsemblePredictionResponse,
    ModelInfo,
    ModelPerformanceResponse,
    PredictionRequest,
    PredictionResponse,
)


class PredictionService:
    """Service for handling ML predictions."""

    def __init__(self):
        self.redis = get_redis_client()
        self.ml_engine_url = "http://ml-engine:8002"  # Internal service URL
        self.cache_ttl = 600  # 10 minutes

    async def get_prediction(
        self,
        request: PredictionRequest,
        db: AsyncSession
    ) -> PredictionResponse:
        """
        Get prediction for a symbol using specified model.
        """
        cache_key = f"prediction:{request.symbol}:{request.model_type}:{request.prediction_horizon}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return PredictionResponse(**json.loads(cached_data))

        try:
            # Call ML engine service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ml_engine_url}/predict",
                    json={
                        "symbol": request.symbol,
                        "model_type": request.model_type,
                        "prediction_horizon": request.prediction_horizon,
                        "features": request.features or []
                    }
                )
                response.raise_for_status()
                ml_result = response.json()

            prediction = PredictionResponse(
                symbol=request.symbol,
                model_type=request.model_type,
                prediction_horizon=request.prediction_horizon,
                predicted_price=ml_result["predicted_price"],
                confidence_score=ml_result["confidence_score"],
                prediction_date=datetime.utcnow().isoformat(),
                features_used=ml_result["features_used"],
                model_version=ml_result["model_version"],
                risk_metrics={
                    "volatility": ml_result.get("volatility", 0.0),
                    "sharpe_ratio": ml_result.get("sharpe_ratio", 0.0),
                    "max_drawdown": ml_result.get("max_drawdown", 0.0)
                },
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(prediction.dict()))

            # Store in database
            db_prediction = Prediction(
                symbol=request.symbol,
                model_type=request.model_type,
                prediction_horizon=request.prediction_horizon,
                predicted_price=prediction.predicted_price,
                confidence_score=prediction.confidence_score,
                prediction_date=datetime.fromisoformat(prediction.prediction_date),
                features_used=json.dumps(prediction.features_used),
                model_version=prediction.model_version,
                risk_metrics=json.dumps(prediction.risk_metrics)
            )
            db.add(db_prediction)
            await db.commit()

            return prediction

        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to ML engine: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"ML engine error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get prediction: {str(e)}")

    async def get_ensemble_prediction(
        self,
        symbol: str,
        prediction_horizon: int,
        db: AsyncSession
    ) -> EnsemblePredictionResponse:
        """
        Get ensemble prediction combining multiple models.
        """
        cache_key = f"ensemble:{symbol}:{prediction_horizon}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return EnsemblePredictionResponse(**json.loads(cached_data))

        try:
            # Call ML engine for ensemble prediction
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ml_engine_url}/predict/ensemble",
                    json={
                        "symbol": symbol,
                        "prediction_horizon": prediction_horizon
                    }
                )
                response.raise_for_status()
                ensemble_result = response.json()

            ensemble_prediction = EnsemblePredictionResponse(
                symbol=symbol,
                prediction_horizon=prediction_horizon,
                ensemble_prediction=ensemble_result["ensemble_prediction"],
                individual_predictions=ensemble_result["individual_predictions"],
                ensemble_confidence=ensemble_result["ensemble_confidence"],
                prediction_date=datetime.utcnow().isoformat(),
                models_used=ensemble_result["models_used"],
                ensemble_method=ensemble_result["ensemble_method"],
                risk_metrics=ensemble_result.get("risk_metrics", {}),
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(ensemble_prediction.dict()))

            return ensemble_prediction

        except Exception as e:
            raise Exception(f"Failed to get ensemble prediction: {str(e)}")

    async def get_model_info(self, model_type: str, db: AsyncSession) -> ModelInfo:
        """
        Get information about a specific model.
        """
        cache_key = f"model_info:{model_type}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return ModelInfo(**json.loads(cached_data))

        try:
            # Call ML engine for model info
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.ml_engine_url}/models/{model_type}")
                response.raise_for_status()
                model_data = response.json()

            model_info = ModelInfo(
                model_type=model_type,
                name=model_data["name"],
                description=model_data["description"],
                version=model_data["version"],
                accuracy_metrics=model_data["accuracy_metrics"],
                features_used=model_data["features_used"],
                training_date=model_data["training_date"],
                last_updated=model_data["last_updated"],
                status=model_data["status"]
            )

            # Cache for longer period
            await self.redis.setex(cache_key, 3600, json.dumps(model_info.dict()))  # 1 hour

            return model_info

        except Exception as e:
            raise Exception(f"Failed to get model info: {str(e)}")

    async def get_available_models(self, db: AsyncSession) -> List[ModelInfo]:
        """
        Get list of all available models.
        """
        cache_key = "available_models"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return [ModelInfo(**model) for model in json.loads(cached_data)]

        try:
            # Call ML engine for available models
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.ml_engine_url}/models")
                response.raise_for_status()
                models_data = response.json()

            models = []
            for model_data in models_data:
                models.append(ModelInfo(**model_data))

            # Cache for 30 minutes
            await self.redis.setex(cache_key, 1800, json.dumps([m.dict() for m in models]))

            return models

        except Exception as e:
            raise Exception(f"Failed to get available models: {str(e)}")

    async def get_model_performance(
        self,
        model_type: str,
        symbol: Optional[str] = None,
        db: AsyncSession = None
    ) -> ModelPerformanceResponse:
        """
        Get performance metrics for a model.
        """
        cache_key = f"performance:{model_type}:{symbol or 'all'}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return ModelPerformanceResponse(**json.loads(cached_data))

        try:
            # Call ML engine for performance data
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {"model_type": model_type}
                if symbol:
                    params["symbol"] = symbol

                response = await client.get(
                    f"{self.ml_engine_url}/performance",
                    params=params
                )
                response.raise_for_status()
                perf_data = response.json()

            performance = ModelPerformanceResponse(
                model_type=model_type,
                symbol=symbol,
                mse=perf_data["mse"],
                rmse=perf_data["rmse"],
                mae=perf_data["mae"],
                r_squared=perf_data["r_squared"],
                directional_accuracy=perf_data["directional_accuracy"],
                profit_factor=perf_data.get("profit_factor"),
                max_drawdown=perf_data.get("max_drawdown"),
                sharpe_ratio=perf_data.get("sharpe_ratio"),
                test_period_start=perf_data["test_period_start"],
                test_period_end=perf_data["test_period_end"],
                total_predictions=perf_data["total_predictions"],
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache for 1 hour
            await self.redis.setex(cache_key, 3600, json.dumps(performance.dict()))

            return performance

        except Exception as e:
            raise Exception(f"Failed to get model performance: {str(e)}")

    async def retrain_model(
        self,
        model_type: str,
        symbol: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, str]:
        """
        Trigger model retraining.
        """
        try:
            # Call ML engine to retrain model
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
                payload = {"model_type": model_type}
                if symbol:
                    payload["symbol"] = symbol

                response = await client.post(
                    f"{self.ml_engine_url}/retrain",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

            # Clear related caches
            await self.redis.delete(f"model_info:{model_type}")
            await self.redis.delete("available_models")
            await self.redis.delete(f"performance:{model_type}:{symbol or 'all'}")

            return {
                "status": "success",
                "message": f"Model {model_type} retraining initiated",
                "job_id": result.get("job_id"),
                "estimated_completion": result.get("estimated_completion")
            }

        except Exception as e:
            raise Exception(f"Failed to retrain model: {str(e)}")