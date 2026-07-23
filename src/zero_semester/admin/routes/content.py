from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.admin.forms import LmsForm, ModuleDetailsForm, ModuleForm, PracticeForm
from zero_semester.admin.templating import render_template
from zero_semester.media_validation import InvalidMediaError, validate_image, validate_video
from zero_semester.models import (
    Card,
    CourseRun,
    LmsCourse,
    MediaAsset,
    Module,
    ModuleIntroMedia,
    ModuleLmsCourse,
    Post,
    Practice,
    QuizOption,
    School,
    SecretKey,
)
from zero_semester.models.enums import PracticeType, PublicationStatus
from zero_semester.services.secrets import activate_secret_key
from zero_semester.storage import LocalMediaStorage

router = APIRouter(prefix="/content", tags=["content"])
storage = LocalMediaStorage()
MAX_CARD_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_CARD_FILES = 10
MAX_CARD_TOTAL_BYTES = 50 * 1024 * 1024


async def _content_context(
    session: DbSession,
    admin: CurrentAdmin,
    active_school_id: int | None = None,
) -> dict[str, object]:
    schools = list((await session.scalars(select(School).order_by(School.name))).all())
    active_school = next(
        (school for school in schools if school.id == active_school_id),
        schools[0] if schools else None,
    )
    module_rows: list[object] = []
    if active_school is not None:
        module_rows = list(
            (
                await session.execute(
                    select(Module, CourseRun, School)
                    .join(CourseRun, CourseRun.id == Module.course_run_id)
                    .join(School, School.id == CourseRun.school_id)
                    .where(School.id == active_school.id)
                    .order_by(Module.position)
                )
            ).all()
        )
    return {
        "admin": admin,
        "schools": schools,
        "active_school": active_school,
        "module_rows": module_rows,
    }


async def _module_or_404(session: DbSession, module_id: int) -> Module:
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Модуль не найден")
    return module


async def _editor_context(
    session: DbSession,
    admin: CurrentAdmin,
    module: Module,
) -> dict[str, object]:
    course_run = await session.get(CourseRun, module.course_run_id)
    if course_run is None:
        raise HTTPException(status_code=404, detail="Курс не найден")
    school = await session.get(School, course_run.school_id)
    cards = list(
        (
            await session.execute(
                select(Card, Post, MediaAsset)
                .join(Post, Post.id == Card.post_id)
                .join(MediaAsset, MediaAsset.id == Card.media_asset_id)
                .where(Post.module_id == module.id)
                .order_by(Post.position, Card.position)
            )
        ).all()
    )
    intro_row = (
        await session.execute(
            select(ModuleIntroMedia, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ModuleIntroMedia.media_asset_id)
            .where(ModuleIntroMedia.module_id == module.id)
        )
    ).first()
    practice = await session.scalar(select(Practice).where(Practice.module_id == module.id))
    options: list[QuizOption] = []
    if practice is not None:
        options = list(
            (
                await session.scalars(
                    select(QuizOption)
                    .where(
                        QuizOption.practice_id == practice.id,
                        QuizOption.is_active.is_(True),
                    )
                    .order_by(QuizOption.position)
                )
            ).all()
        )
    lms_row = (
        await session.execute(
            select(LmsCourse, ModuleLmsCourse)
            .join(ModuleLmsCourse, ModuleLmsCourse.lms_course_id == LmsCourse.id)
            .where(ModuleLmsCourse.module_id == module.id)
        )
    ).first()
    secret_keys: list[SecretKey] = []
    if lms_row is not None:
        secret_keys = list(
            (
                await session.scalars(
                    select(SecretKey)
                    .where(SecretKey.lms_course_id == lms_row[0].id)
                    .order_by(SecretKey.created_at.desc())
                )
            ).all()
        )
    return {
        "admin": admin,
        "module": module,
        "course_run": course_run,
        "school": school,
        "cards": cards,
        "intro_asset": intro_row[1] if intro_row else None,
        "practice": practice,
        "options": options,
        "lms_course": lms_row[0] if lms_row else None,
        "module_lms": lms_row[1] if lms_row else None,
        "secret_keys": secret_keys,
    }


@router.get("")
async def content_page(
    request: Request,
    session: DbSession,
    admin: CurrentAdmin,
    school_id: int | None = None,
) -> Response:
    return render_template(
        request,
        "content/index.html",
        await _content_context(session, admin, school_id),
    )


@router.post("/modules")
async def create_module(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    raw: dict[str, object] = dict(await request.form())
    raw["is_required"] = raw.get("is_required") == "on"
    error_message: str | None = None
    try:
        form = ModuleForm.model_validate(raw)
        school = await session.get(School, form.school_id)
        if school is None:
            raise ValueError("Школа не найдена")
        course_run = await session.scalar(
            select(CourseRun)
            .where(CourseRun.school_id == school.id)
            .order_by(CourseRun.year.desc())
        )
        if course_run is None:
            year = datetime.now().year
            course_run = CourseRun(
                school_id=school.id,
                name=f"Нулевой семестр — {school.name}",
                year=year,
                status=PublicationStatus.PUBLISHED,
            )
            session.add(course_run)
            await session.flush()
        elif course_run.status == PublicationStatus.ARCHIVED:
            course_run.status = PublicationStatus.PUBLISHED
        position = (
            await session.scalar(
                select(func.max(Module.position)).where(Module.course_run_id == course_run.id)
            )
            or 0
        ) + 1
        module = Module(
            course_run_id=course_run.id,
            title=form.title,
            description=form.description,
            position=position,
            is_required=form.is_required,
            status=PublicationStatus.DRAFT,
        )
        session.add(module)
        await session.commit()
    except (ValidationError, ValueError) as error:
        await session.rollback()
        error_message = str(error)
    except IntegrityError:
        await session.rollback()
        error_message = "Не удалось подобрать свободную позицию. Попробуй ещё раз"
    if error_message is not None:
        active_school_id = raw.get("school_id")
        context = await _content_context(
            session,
            admin,
            int(str(active_school_id)) if str(active_school_id).isdigit() else None,
        )
        context["error"] = error_message
        return render_template(
            request,
            "content/index.html",
            context,
            status_code=400,
        )
    return RedirectResponse(f"/content/modules/{module.id}", status_code=303)


@router.get("/modules/{module_id}")
async def module_editor(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await _module_or_404(session, module_id)
    return render_template(
        request, "content/module_editor.html", await _editor_context(session, admin, module)
    )


@router.post("/modules/{module_id}/details")
async def update_module_details(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await _module_or_404(session, module_id)
    raw: dict[str, object] = dict(await request.form())
    raw["is_required"] = raw.get("is_required") == "on"
    error_message: str | None = None
    try:
        form = ModuleDetailsForm.model_validate(raw)
        module.title = form.title
        module.description = form.description
        module.is_required = form.is_required
        module.status = PublicationStatus.DRAFT
        await session.commit()
    except (ValidationError, ValueError) as error:
        await session.rollback()
        error_message = str(error)
    except IntegrityError:
        await session.rollback()
        error_message = "Выбранная позиция уже занята другим модулем"
    if error_message is not None:
        module = await _module_or_404(session, module_id)
        context = await _editor_context(session, admin, module)
        context["error"] = error_message
        return render_template(request, "content/module_editor.html", context, status_code=400)
    return RedirectResponse(f"/content/modules/{module.id}#main", status_code=303)


@router.post("/modules/{module_id}/cards")
async def add_module_card(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
    files: list[UploadFile],
) -> Response:
    module = await _module_or_404(session, module_id)
    if len(files) > MAX_CARD_FILES:
        context = await _editor_context(session, admin, module)
        context["error"] = f"За один раз можно загрузить не больше {MAX_CARD_FILES} карточек"
        return render_template(request, "content/module_editor.html", context, status_code=400)
    uploads: list[tuple[bytes, str, str]] = []
    total_bytes = 0
    for file in files:
        content = await file.read(MAX_CARD_BYTES + 1)
        total_bytes += len(content)
        try:
            if len(content) > MAX_CARD_BYTES:
                raise InvalidMediaError("Изображение больше 20 МБ")
            media = validate_image(content)
            if total_bytes > MAX_CARD_TOTAL_BYTES:
                raise InvalidMediaError("Суммарный размер карточек больше 50 МБ")
        except InvalidMediaError as error:
            context = await _editor_context(session, admin, module)
            context["error"] = (
                f"Файл «{file.filename or 'без названия'}» не принят: {error}"
            )
            return render_template(request, "content/module_editor.html", context, status_code=400)
        uploads.append((media.content, media.suffix, media.media_type))
    if not uploads:
        context = await _editor_context(session, admin, module)
        context["error"] = "Выбери хотя бы одно изображение"
        return render_template(request, "content/module_editor.html", context, status_code=400)
    post = await session.scalar(
        select(Post).where(Post.module_id == module.id).order_by(Post.position)
    )
    if post is None:
        post = Post(module_id=module.id, title="Карточки", position=1)
        session.add(post)
        await session.flush()
    position = (
        await session.scalar(select(func.max(Card.position)).where(Card.post_id == post.id)) or 0
    ) + 1
    for offset, (content, suffix, media_type) in enumerate(uploads):
        relative_path = storage.save(content, suffix)
        asset = MediaAsset(relative_path=relative_path, media_type=media_type)
        session.add(asset)
        await session.flush()
        session.add(
            Card(
                post_id=post.id,
                media_asset_id=asset.id,
                caption=None,
                position=position + offset,
            )
        )
    module.status = PublicationStatus.DRAFT
    await session.commit()
    return RedirectResponse(f"/content/modules/{module.id}#cards", status_code=303)


@router.post("/modules/{module_id}/video")
async def save_module_video(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
    file: UploadFile,
) -> Response:
    module = await _module_or_404(session, module_id)
    content = await file.read(MAX_VIDEO_BYTES + 1)
    try:
        if len(content) > MAX_VIDEO_BYTES:
            raise InvalidMediaError("Видео больше 50 МБ")
        media = validate_video(content)
    except InvalidMediaError as error:
        context = await _editor_context(session, admin, module)
        context["error"] = f"Видео не принято: {error}"
        return render_template(request, "content/module_editor.html", context, status_code=400)

    link = await session.get(ModuleIntroMedia, module.id)
    old_asset = await session.get(MediaAsset, link.media_asset_id) if link else None
    relative_path = storage.save(media.content, media.suffix)
    asset = MediaAsset(relative_path=relative_path, media_type=media.media_type)
    session.add(asset)
    await session.flush()
    if link is None:
        session.add(ModuleIntroMedia(module_id=module.id, media_asset_id=asset.id))
    else:
        link.media_asset_id = asset.id
        await session.flush()
        if old_asset is not None:
            await session.delete(old_asset)
            storage.delete(old_asset.relative_path)
    module.status = PublicationStatus.DRAFT
    await session.commit()
    return RedirectResponse(f"/content/modules/{module.id}#video", status_code=303)


@router.post("/modules/{module_id}/video/delete")
async def delete_module_video(
    module_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> RedirectResponse:
    module = await _module_or_404(session, module_id)
    link = await session.get(ModuleIntroMedia, module.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    asset = await session.get(MediaAsset, link.media_asset_id)
    await session.delete(link)
    await session.flush()
    if asset is not None:
        await session.delete(asset)
        storage.delete(asset.relative_path)
    module.status = PublicationStatus.DRAFT
    await session.commit()
    return RedirectResponse(f"/content/modules/{module.id}#video", status_code=303)


@router.post("/modules/{module_id}/practice")
async def save_practice(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await session.scalar(select(Module).where(Module.id == module_id).with_for_update())
    if module is None:
        raise HTTPException(status_code=404, detail="Модуль не найден")
    try:
        form = PracticeForm.model_validate(dict(await request.form()))
        option_texts = [
            line.strip() for line in (form.options_text or "").splitlines() if line.strip()
        ]
        if form.practice_type in {PracticeType.QUIZ, PracticeType.POLL}:
            if len(option_texts) < 2:
                raise ValueError("Для квиза или опроса нужны минимум два варианта")
        if form.practice_type == PracticeType.QUIZ:
            if len(option_texts) < 2 or form.correct_option not in range(1, len(option_texts) + 1):
                raise ValueError("Для квиза нужны минимум два варианта и номер правильного")
        practice = await session.scalar(
            select(Practice).where(Practice.module_id == module.id).with_for_update()
        )
        if practice is None:
            practice = Practice(
                module_id=module.id,
                practice_type=form.practice_type,
                question=form.question,
                explanation=form.explanation,
                max_attempts=form.max_attempts,
            )
            session.add(practice)
            await session.flush()
        else:
            practice.practice_type = form.practice_type
            practice.question = form.question
            practice.explanation = form.explanation
            practice.max_attempts = form.max_attempts
        active_options = list(
            (
                await session.scalars(
                    select(QuizOption)
                    .where(
                        QuizOption.practice_id == practice.id,
                        QuizOption.is_active.is_(True),
                    )
                    .order_by(QuizOption.position)
                )
            ).all()
        )
        desired_options = (
            [
                (
                    text,
                    index == form.correct_option
                    if form.practice_type == PracticeType.QUIZ
                    else False,
                )
                for index, text in enumerate(option_texts, start=1)
            ]
            if form.practice_type in {PracticeType.QUIZ, PracticeType.POLL}
            else []
        )
        current_options = [(option.text, option.is_correct) for option in active_options]
        if current_options != desired_options:
            # Answers keep their foreign keys to the retired options, while the bot sees only
            # the newly active set. Negative positions avoid the per-practice unique constraint.
            for option in active_options:
                option.is_active = False
                option.position = -option.id
            await session.flush()
            session.add_all(
                [
                    QuizOption(
                        practice_id=practice.id,
                        text=text,
                        position=index,
                        is_correct=is_correct,
                        is_active=True,
                    )
                    for index, (text, is_correct) in enumerate(desired_options, start=1)
                ]
            )
        module.status = PublicationStatus.DRAFT
        await session.commit()
    except (ValidationError, ValueError) as error:
        await session.rollback()
        context = await _editor_context(session, admin, module)
        context["error"] = f"Не удалось сохранить практику: {error}"
        return render_template(request, "content/module_editor.html", context, status_code=400)
    return RedirectResponse(f"/content/modules/{module.id}#practice", status_code=303)


@router.post("/modules/{module_id}/cards/{card_id}/delete")
async def delete_module_card(
    module_id: int,
    card_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> RedirectResponse:
    module = await _module_or_404(session, module_id)
    row = (
        await session.execute(
            select(Card, Post, MediaAsset)
            .join(Post, Post.id == Card.post_id)
            .join(MediaAsset, MediaAsset.id == Card.media_asset_id)
            .where(Card.id == card_id, Post.module_id == module.id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    card, _post, asset = row
    await session.delete(card)
    await session.flush()
    remaining = await session.scalar(
        select(func.count(Card.id)).where(Card.media_asset_id == asset.id)
    )
    if not remaining:
        await session.delete(asset)
        storage.delete(asset.relative_path)
    module.status = PublicationStatus.DRAFT
    await session.commit()
    return RedirectResponse(f"/content/modules/{module.id}#cards", status_code=303)


@router.post("/modules/{module_id}/lms")
async def save_lms(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await _module_or_404(session, module_id)
    course_run = await session.get(CourseRun, module.course_run_id)
    if course_run is None:
        raise HTTPException(status_code=404, detail="Курс не найден")
    try:
        form = LmsForm.model_validate(dict(await request.form()))
        link = await session.scalar(
            select(ModuleLmsCourse).where(ModuleLmsCourse.module_id == module.id)
        )
        lms_course = await session.get(LmsCourse, link.lms_course_id) if link else None
        if lms_course is None:
            lms_course = LmsCourse(
                school_id=course_run.school_id,
                name=form.name,
                target_url=str(form.target_url),
                short_code=uuid4().hex[:10],
            )
            session.add(lms_course)
            await session.flush()
            session.add(
                ModuleLmsCourse(
                    module_id=module.id,
                    lms_course_id=lms_course.id,
                    button_text=form.button_text,
                )
            )
        else:
            lms_course.name = form.name
            lms_course.target_url = str(form.target_url)
            if link is not None:
                link.button_text = form.button_text
        if form.secret_key:
            await activate_secret_key(
                session,
                lms_course_id=lms_course.id,
                value=form.secret_key,
                label=form.secret_key_label or "Новый ключ",
            )
        module.status = PublicationStatus.DRAFT
        await session.commit()
    except (ValidationError, ValueError, IntegrityError) as error:
        await session.rollback()
        context = await _editor_context(session, admin, module)
        context["error"] = f"Не удалось сохранить LMS и ключ: {error}"
        return render_template(request, "content/module_editor.html", context, status_code=400)
    return RedirectResponse(f"/content/modules/{module.id}#lms", status_code=303)


@router.get("/modules/{module_id}/preview")
async def preview_module(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await _module_or_404(session, module_id)
    return render_template(
        request, "content/module_preview.html", await _editor_context(session, admin, module)
    )


@router.post("/modules/{module_id}/publish")
async def publish_module(
    request: Request,
    module_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    module = await _module_or_404(session, module_id)
    cards_count = await session.scalar(
        select(func.count(Card.id)).join(Post).where(Post.module_id == module.id)
    )
    practice = await session.scalar(select(Practice.id).where(Practice.module_id == module.id))
    lms = await session.scalar(
        select(ModuleLmsCourse.module_id).where(ModuleLmsCourse.module_id == module.id)
    )
    intro = await session.scalar(
        select(ModuleIntroMedia.module_id).where(ModuleIntroMedia.module_id == module.id)
    )
    if not cards_count and practice is None and lms is None and intro is None:
        context = await _editor_context(session, admin, module)
        context["error"] = "Нельзя опубликовать пустой модуль — добавь карточку, практику или LMS"
        return render_template(request, "content/module_editor.html", context, status_code=400)
    module.status = PublicationStatus.PUBLISHED
    course_run = await session.get(CourseRun, module.course_run_id)
    if course_run is not None:
        course_run.status = PublicationStatus.PUBLISHED
    await session.commit()
    return RedirectResponse(f"/content/modules/{module.id}", status_code=303)


@router.post("/modules/{module_id}/archive")
async def archive_module(
    module_id: int,
    session: DbSession,
    _admin: CurrentAdmin,
) -> RedirectResponse:
    module = await _module_or_404(session, module_id)
    module.status = PublicationStatus.ARCHIVED
    await session.commit()
    return RedirectResponse("/content", status_code=303)
