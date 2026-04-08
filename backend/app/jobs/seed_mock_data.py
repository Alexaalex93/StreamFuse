from app.persistence.db import SessionLocal
from app.persistence.seed import seed_dev_data


def run() -> None:
    db = SessionLocal()
    try:
        seed_dev_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
