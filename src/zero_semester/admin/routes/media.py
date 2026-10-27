from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.templating import render_template
from zero_semester.media_validation import InvalidMediaError, validate_image_or_video
from zero_semester.models import MediaAsset
from zero_semester.storage import LocalMediaStorage

router = APIRouter(prefix="/media", tags=["media"])
storage = LocalMediaStorage()
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.get("/{asset_id}/file")
async def media_file(
    asset_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> FileResponse:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(
        storage.resolve(asset.relative_path),
        media_type=asset.media_type,
        headers={"Content-Disposition": "inline"},
    )


@router.get("")
async def media_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    assets = list(
        (await session.scalars(select(MediaAsset).order_by(MediaAsset.created_at.desc()))).all()
    )
    return render_template(request, "media/index.html", {"admin": admin, "assets": assets})


@router.post("")
async def upload_media(
    request: Request,
    session: DbSession,
    admin: CurrentAdmin,
    file: UploadFile,
) -> Response:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        if len(content) > MAX_UPLOAD_BYTES:
            raise InvalidMediaError("Файл больше 50 МБ")
        media = validate_image_or_video(content)
    except InvalidMediaError as error:
        assets = list((await session.scalars(select(MediaAsset))).all())
        return render_template(
            request,
            "media/index.html",
            {"admin": admin, "assets": assets, "error": f"Файл не принят: {error}"},
            status_code=400,
        )
    relative_path = storage.save(media.content, media.suffix)
    session.add(
        MediaAsset(
            relative_path=relative_path,
            media_type=media.media_type,
        )
    )
    await session.commit()
    return RedirectResponse("/media", status_code=303)
