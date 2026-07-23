from __future__ import annotations

import argparse

from app.core.database import Base, SessionLocal, engine
from app.models import user  # noqa: F401
from app.services.invitations import InvitationService


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one-time invitation codes.")
    parser.add_argument("--count", type=int, default=10, help="Number of invitation codes to generate.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        codes = InvitationService(db).generate_codes(args.count)
        for invitation in codes:
            print(invitation.code)


if __name__ == "__main__":
    main()
