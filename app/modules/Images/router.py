from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from app.Core.database import get_session
from app.Core.deps import require_role
from app.modules.Images.schemas import ImagePublic
from app.modules.Images.service import ImageService

router = APIRouter(prefix="/api/v1/images", tags=["images"],dependencies=[
        Depends(require_role(["ADMIN"]))
    ])


def get_image_service(session: Session = Depends(get_session)) -> ImageService:
    return ImageService(session)


@router.get("", response_model=list[ImagePublic])
def list_images(svc: ImageService = Depends(get_image_service)):
    return svc.list_all()


@router.get("/{image_id}", response_model=ImagePublic)
def get_image(image_id: int, svc: ImageService = Depends(get_image_service)):
    return svc.get_by_id(image_id)


@router.post("/upload_many", response_model=list[ImagePublic], status_code=201)
async def upload_images(
    files: list[UploadFile] = File(...),
    svc: ImageService = Depends(get_image_service),
):
    return await svc.upload_many(files)


@router.delete("/{image_id}", status_code=204)
def delete_image(image_id: int, svc: ImageService = Depends(get_image_service)):
    svc.delete(image_id)
