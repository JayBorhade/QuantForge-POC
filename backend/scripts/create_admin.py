"""Create an admin user. Usage: python scripts/create_admin.py email@example.com"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].lower()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User {email} not found. Register first via /signup.")
            sys.exit(1)
        user.role = UserRole.ADMIN
        await db.commit()
        print(f"Promoted {email} to admin")


if __name__ == "__main__":
    asyncio.run(main())
