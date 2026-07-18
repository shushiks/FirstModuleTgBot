from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from zero_semester.admin.deps import CurrentAdmin, DbSession
from zero_semester.models import Module, User

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(session: DbSession, admin: CurrentAdmin) -> str:
    users_count = await session.scalar(select(func.count()).select_from(User)) or 0
    modules_count = await session.scalar(select(func.count()).select_from(Module)) or 0
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Админка</title></head><body><main><h1>Нулевой семестр</h1>
<p>Администратор: {admin.username}</p><p>Пользователей: {users_count}</p>
<p>Модулей: {modules_count}</p><form method="post" action="/logout">
<button>Выйти</button></form></main></body></html>"""
