from sqlalchemy import text

from sammy.bootstrap import start


def test_sammy_enforces_foreign_keys_on_sqlite(tmp_path):
    sammy = start(f"sqlite:///{tmp_path / 'sammy.sqlite'}")
    try:
        with sammy.engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    finally:
        sammy.close()
