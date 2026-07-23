from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response

from zero_semester.admin.deps import AdminIdentity, CurrentAdmin, DbSession
from zero_semester.admin.forms import AdminCreateForm
from zero_semester.admin.templating import render_template
from zero_semester.models import AdminUser, AuditLog
from zero_semester.models.enums import AdminRole
from zero_semester.security import hash_password

router = APIRouter(prefix="/admins", tags=["admins"])


def _ensure_admin(admin: AdminIdentity) -> None:
    if admin.role != AdminRole.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав")


async def _context(session: DbSession, admin: AdminIdentity) -> dict[str, object]:
    accounts = list(
        (await session.scalars(select(AdminUser).order_by(AdminUser.created_at))).all()
    )
    return {"admin": admin, "accounts": accounts, "roles": list(AdminRole)}


@router.get("")
async def admins_page(request: Request, session: DbSession, admin: CurrentAdmin) -> Response:
    _ensure_admin(admin)
    context = await _context(session, admin)
    context["created"] = request.query_params.get("created") == "1"
    return render_template(request, "admins/index.html", context)


@router.post("")
async def create_admin_account(
    request: Request,
    session: DbSession,
    admin: CurrentAdmin,
) -> Response:
    _ensure_admin(admin)
    try:
        form = AdminCreateForm.model_validate(dict(await request.form()))
        account = AdminUser(
            username=form.username,
            password_hash=hash_password(form.password),
            role=form.role,
        )
        session.add(account)
        await session.flush()
        session.add(
            AuditLog(
                admin_user_id=admin.id,
                action="admin.created",
                entity_type="admin_user",
                entity_id=str(account.id),
                changes={"username": account.username, "role": account.role.value},
            )
        )
        await session.commit()
    except (ValidationError, IntegrityError) as error:
        await session.rollback()
        context = await _context(session, admin)
        context["error"] = (
            "Администратор с таким логином уже существует"
            if isinstance(error, IntegrityError)
            else f"Проверь поля: {error}"
        )
        return render_template(request, "admins/index.html", context, status_code=400)
    return RedirectResponse("/admins?created=1", status_code=303)


@router.post("/{admin_id}/toggle")
async def toggle_admin_account(
    admin_id: int,
    session: DbSession,
    admin: CurrentAdmin,
) -> RedirectResponse:
    _ensure_admin(admin)
    account = await session.get(AdminUser, admin_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Администратор не найден")
    if account.id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя отключить собственную учётку")
    account.is_active = not account.is_active
    await session.commit()
    return RedirectResponse("/admins", status_code=303)
