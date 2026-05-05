from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass
class PresignedUpload:
    object_key: str
    upload_url: str
    public_url: str


class PhotoService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_presigned_upload(self, filename: str, content_type: str, folder: str = "photos") -> PresignedUpload:
        ext = os.path.splitext(filename)[1].lower()
        object_key = f"{folder}/{uuid.uuid4().hex}{ext}"
        if self.settings.s3_bucket_photos:
            upload_url = f"https://{self.settings.s3_bucket_photos}.s3.amazonaws.com/{object_key}"
        else:
            upload_url = f"{self.settings.api_url}/mock-upload/{object_key}"
        public_host = self.settings.cloudfront_domain or self.settings.api_url.replace("http://", "").replace("https://", "")
        scheme = "https" if self.settings.cloudfront_domain else self.settings.api_url.split("://")[0]
        public_url = f"{scheme}://{public_host}/{object_key}"
        return PresignedUpload(object_key=object_key, upload_url=upload_url, public_url=public_url)


def get_photo_service() -> PhotoService:
    return PhotoService(get_settings())
