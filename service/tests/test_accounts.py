"""Multi-user accounts + shared household tests (isolated temp DB)."""
import importlib
import os
import tempfile

import pytest


@pytest.fixture()
def stores(monkeypatch):
    # point the shared DB at a temp file, fresh per test
    d = tempfile.mkdtemp()
    import app.db as db
    monkeypatch.setattr(db, "DB_PATH", os.path.join(d, "t.db"))
    from app.accounts.auth import AuthStore
    from app.accounts.household_repo import HouseholdRepo
    return AuthStore(), HouseholdRepo()


def test_register_login_session(stores):
    auth, _ = stores
    token = auth.register("Justin", "j@x.com", "pw12345")
    assert auth.user_for_token(token).name == "Justin"
    # wrong password rejected
    with pytest.raises(ValueError):
        auth.login("j@x.com", "nope")
    # right password issues a working session
    t2 = auth.login("j@x.com", "pw12345")
    assert auth.user_for_token(t2).email == "j@x.com"
    auth.logout(t2)
    assert auth.user_for_token(t2) is None


def test_duplicate_email_rejected(stores):
    auth, _ = stores
    auth.register("A", "dup@x.com", "pw")
    with pytest.raises(ValueError):
        auth.register("B", "dup@x.com", "pw")


def test_household_create_join_and_build(stores):
    auth, repo = stores
    t1 = auth.register("Justin", "j@x.com", "pw")
    t2 = auth.register("Maya", "m@x.com", "pw")
    u1 = auth.user_for_token(t1)
    u2 = auth.user_for_token(t2)

    h = repo.create("The Polomceans", u1.id)
    repo.join(h["code"], u2.id)

    # Maya opts in and sets herself free; Justin busy at pickup
    repo.set_membership(h["id"], u2.id, can_drive=True, shares=True, accepts=True)
    repo.set_availability(u1.id, [(17 * 60, 18 * 60 + 30)])
    repo.set_availability(u2.id, [])

    built = repo.build_for_user(u1.id)
    assert built is not None
    household, timemap, consent = built
    assert {m.name for m in household.all()} == {"Justin", "Maya"}
    assert consent.is_candidate(u2.id) is True       # Maya opted in
    assert timemap.is_free(u2.id, 17 * 60, 18 * 60) is True

    # the matcher now coordinates over the real, shared household
    from app.household import Matcher
    from app.household.timemap import task_minutes
    start = task_minutes("5:30")
    coord = Matcher(household, timemap, consent).find(start, start + 65, True, True)
    assert coord.helper.name == "Maya"


def test_bad_join_code(stores):
    auth, repo = stores
    t = auth.register("X", "x@x.com", "pw")
    with pytest.raises(ValueError):
        repo.join("ZZZZZZ", auth.user_for_token(t).id)
