"""How the predictions work: the benchmark, assumption evidence and the final models' 2026 test (read only)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cricketlens.api.schemas import MethodologyResponse
from cricketlens.api.services import methodology_service as service

router = APIRouter(prefix="/api/methodology", tags=["Methodology"])


@router.get(
    "",
    response_model=MethodologyResponse,
    summary="Prediction-model methodology and evidence",
    description="The workflow, prediction questions, data and algorithm assumption verdicts, the seven-algorithm "
                "comparison (2021–2025), learning curves, paired per-season gaps, tuning grids and the final "
                "models' 2026 retrospective test with calibration and confusion matrices, all read from "
                "reports/model_benchmark.",
)
def get_methodology() -> MethodologyResponse:
    try:
        return service.methodology_service.get()
    except service.MethodologyUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
