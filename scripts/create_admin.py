from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import User, UserRole


async def create_admin(auth0_id: str, email: str, name: str) -> None:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.auth0_id == auth0_id))).scalar_one_or_none()
        if user is None:
            db.add(User(auth0_id=auth0_id, email=email, name=name, role=UserRole.admin))
        else:
            user.email = email
            user.name = name
            user.role = UserRole.admin
        await db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth0-id", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    asyncio.run(create_admin(args.auth0_id, args.email, args.name))
