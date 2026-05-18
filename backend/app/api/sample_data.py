"""Routes for installing the deterministic local sample project."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import SampleDataMutationResponse, SampleDataStatusResponse
from app.services.sample_data_service import delete_sample_data, get_sample_data_status, seed_sample_data

router = APIRouter(prefix="/sample-data", tags=["sample-data"])


@router.get("/status", response_model=SampleDataStatusResponse)
def read_sample_data_status() -> SampleDataStatusResponse:
    return get_sample_data_status()


@router.post("/seed", response_model=SampleDataMutationResponse)
def install_sample_data() -> SampleDataMutationResponse:
    return seed_sample_data()


@router.delete("", response_model=SampleDataMutationResponse)
def remove_sample_data() -> SampleDataMutationResponse:
    return delete_sample_data()
