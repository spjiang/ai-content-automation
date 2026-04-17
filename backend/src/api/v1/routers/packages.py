from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps import get_db
from src.infrastructure.db.models import PublishPackage

router = APIRouter(tags=["packages"])


@router.get("/packages/{package_id}/download")
async def download_package(
    package_id: int,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    pkg = await session.get(PublishPackage, package_id)
    if pkg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="package not found")
    path = Path(pkg.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="package file missing on disk")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"package-{pkg.content_job_id}-{pkg.package_version}.json",
    )
