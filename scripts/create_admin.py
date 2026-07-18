import argparse
import asyncio

from sqlalchemy import select

from zero_semester.database import session_factory
from zero_semester.models import AdminUser
from zero_semester.models.enums import AdminRole
from zero_semester.security import hash_password


async def create_admin(username: str, password: str, role: AdminRole) -> None:
    async with session_factory() as session:
        existing = await session.scalar(select(AdminUser).where(AdminUser.username == username))
        if existing is not None:
            raise SystemExit(f"Admin {username!r} already exists")
        session.add(AdminUser(username=username, password_hash=hash_password(password), role=role))
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin panel user")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--role", choices=list(AdminRole), default=AdminRole.ADMIN)
    args = parser.parse_args()
    asyncio.run(create_admin(args.username, args.password, AdminRole(args.role)))


if __name__ == "__main__":
    main()
