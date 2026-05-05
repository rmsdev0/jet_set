from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_photo_service_dep
from app.models import User
from app.schemas.admin import UploadPresignRequest, UploadPresignResponse
from app.services.photo_service import PhotoService


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=UploadPresignResponse)
async def presign_upload(
    payload: UploadPresignRequest,
    current_user: User = Depends(get_current_user),
    photo_service: PhotoService = Depends(get_photo_service_dep),
):
    upload = await photo_service.create_presigned_upload(payload.filename, payload.content_type, payload.folder)
    return UploadPresignResponse(
        object_key=upload.object_key,
        upload_url=upload.upload_url,
        public_url=upload.public_url,
    )
