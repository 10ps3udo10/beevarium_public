"""Double authentification TOTP et espace administrateur (R9)."""

import base64
import hashlib
import hmac
import struct
import subprocess
import time
from types import SimpleNamespace

import requests

from test_api_integration import API_BASE_URL, _auth_headers, _rand_email, _register_user

PASSWORD = "motdepasse123"


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    return str((struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 10**6).zfill(6)


# Meme interface que app.totp (reimplemente ici pour ne pas dependre du chemin Python du backend).
totp = SimpleNamespace(code_at=_code_at, current_step=lambda: int(time.time() // 30))


def _psql(sql: str, **variables: str) -> str:
    # Variables passees a psql (-v) et interpolees par psql (:'nom') : aucune concatenation SQL.
    args = ["docker", "exec", "-i", "beevarium_db", "sh", "-c",
            'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At "$@"', "sh"]
    for name, value in variables.items():
        args += ["-v", f"{name}={value}"]
    result = subprocess.run(args, input=sql, capture_output=True, text=True, check=True, timeout=30)  # noqa: S603
    return result.stdout.strip()


def _make_admin(email: str) -> None:
    _psql("UPDATE users SET is_admin = true WHERE email = :'email';", email=email)


def _post(path: str, token: str | None = None, **json) -> requests.Response:
    headers = _auth_headers(token) if token else {}
    return requests.post(f"{API_BASE_URL}{path}", headers=headers, json=json, timeout=10)


def _enable_mfa(user: dict) -> dict:
    """Active la MFA avec le pas precedent (-1) : laisse les pas courant et +1 pour la suite du test."""
    token = user["access_token"]
    setup = _post("/users/me/mfa/setup", token, password=PASSWORD)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    for _ in range(2):  # deux essais : le pas peut changer entre le calcul et la requete
        enable = _post("/users/me/mfa/enable", token, code=totp.code_at(secret, totp.current_step() - 1))
        if enable.status_code == 200:
            break
    assert enable.status_code == 200, enable.text
    body = enable.json()
    return {"secret": secret, "codes": body["recovery_codes"], "token": body["access_token"], "email": user["user"]["email"]}


def _login_step1(email: str) -> requests.Response:
    return _post("/auth/login", email=email, password=PASSWORD)


def test_mfa_setup_and_enable_validations() -> None:
    user = _register_user(_rand_email("mfasetup"))
    token = user["access_token"]
    assert _post("/users/me/mfa/setup", token, password="pas-le-bon-mdp").status_code == 403

    secret = _post("/users/me/mfa/setup", token, password=PASSWORD).json()["secret"]
    assert _post("/users/me/mfa/enable", token, code="000000").status_code == 403
    assert _post("/users/me/mfa/enable", token, code="abc").status_code == 403
    assert requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(token), timeout=10).json()["mfa_enabled"] is False

    enabled = _post("/users/me/mfa/enable", token, code=totp.code_at(secret, totp.current_step() - 1))
    assert enabled.status_code == 200, enabled.text
    body = enabled.json()
    assert len(body["recovery_codes"]) == 8 and len(set(body["recovery_codes"])) == 8
    assert all(len(c) == 11 and c[5] == "-" for c in body["recovery_codes"])
    assert body["user"]["mfa_enabled"] is True and "mfa_secret" not in body["user"]
    # Nouvelle session pour l'appareil courant, ancienne revoquee.
    assert requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(body["access_token"]), timeout=10).status_code == 200
    assert requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(token), timeout=10).status_code == 401
    assert _post("/users/me/mfa/setup", body["access_token"], password=PASSWORD).status_code == 409
    me = requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(body["access_token"]), timeout=10).json()
    assert "mfa_secret" not in me


def test_login_two_steps_codes_and_replay() -> None:
    mfa = _enable_mfa(_register_user(_rand_email("mfalogin")))
    step1 = _login_step1(mfa["email"])
    assert step1.status_code == 200, step1.text
    body = step1.json()
    assert body["mfa_required"] is True and "access_token" not in body and "user" not in body
    assert "set-cookie" not in {k.lower() for k in step1.headers}
    mfa_token = body["mfa_token"]
    # Le jeton de premiere etape n'ouvre aucune route.
    assert requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(mfa_token), timeout=10).status_code == 401

    assert _post("/auth/login/mfa", mfa_token=mfa_token, code="000000").status_code == 401
    assert _post("/auth/login/mfa", mfa_token="pas.un.jeton", code="000000").status_code == 401

    step = totp.current_step()
    code = totp.code_at(mfa["secret"], step)
    ok = _post("/auth/login/mfa", mfa_token=mfa_token, code=code)
    assert ok.status_code == 200, ok.text
    assert ok.json()["user"]["email"] == mfa["email"] and ok.cookies
    assert requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(ok.json()["access_token"]), timeout=10).status_code == 200
    # Rejeu du meme code refuse.
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=code).status_code == 401
    # Un code anterieur au dernier pas accepte est refuse aussi.
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=totp.code_at(mfa["secret"], step - 1)).status_code == 401


def test_recovery_code_works_once() -> None:
    mfa = _enable_mfa(_register_user(_rand_email("mfarecup")))
    recovery = mfa["codes"][0]
    mfa_token = _login_step1(mfa["email"]).json()["mfa_token"]
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=recovery).status_code == 200
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=recovery).status_code == 401
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=mfa["codes"][1].replace("-", "").upper()).status_code == 200


def test_mfa_failures_are_rate_limited() -> None:
    mfa = _enable_mfa(_register_user(_rand_email("mfalimit")))
    mfa_token = _login_step1(mfa["email"]).json()["mfa_token"]
    for _ in range(5):
        assert _post("/auth/login/mfa", mfa_token=mfa_token, code="000000").status_code == 401
    good = totp.code_at(mfa["secret"], totp.current_step())
    assert _post("/auth/login/mfa", mfa_token=mfa_token, code=good).status_code == 429
    assert _post("/users/me/mfa/disable", mfa["token"], password=PASSWORD, code=good).status_code == 429


def test_disable_mfa_restores_single_step_login() -> None:
    mfa = _enable_mfa(_register_user(_rand_email("mfadisable")))
    assert _post("/users/me/mfa/disable", mfa["token"], password="pas-le-bon-mdp", code=mfa["codes"][0]).status_code == 403
    assert _post("/users/me/mfa/disable", mfa["token"], password=PASSWORD, code="000000").status_code == 403
    disabled = _post("/users/me/mfa/disable", mfa["token"], password=PASSWORD, code=totp.code_at(mfa["secret"], totp.current_step()))
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["user"]["mfa_enabled"] is False
    login = _login_step1(mfa["email"])
    assert login.status_code == 200 and "access_token" in login.json() and "mfa_required" not in login.json()


def test_account_deletion_removes_mfa_and_recovery_codes() -> None:
    mfa = _enable_mfa(_register_user(_rand_email("mfadelete")))
    user_id = _psql("SELECT id FROM users WHERE email = :'email';", email=mfa["email"])
    assert _psql("SELECT count(*) FROM mfa_recovery_codes WHERE user_id = :'uid';", uid=user_id) == "8"
    export = requests.get(f"{API_BASE_URL}/users/me/export", headers=_auth_headers(mfa["token"]), timeout=10).json()
    assert mfa["secret"] not in str(export) and mfa["codes"][0] not in str(export)
    deleted = requests.delete(f"{API_BASE_URL}/users/me", headers=_auth_headers(mfa["token"]), json={"password": PASSWORD}, timeout=10)
    assert deleted.status_code == 204, deleted.text
    assert _psql("SELECT count(*) FROM mfa_recovery_codes WHERE user_id = :'uid';", uid=user_id) == "0"
    again = _register_user(mfa["email"])
    assert again["user"]["mfa_enabled"] is False
    assert "mfa_required" not in _login_step1(mfa["email"]).json()


def test_admin_routes_require_admin_and_mfa() -> None:
    plain = _register_user(_rand_email("adminplain"))
    for path in ("/admin/feedback", "/admin/stats"):
        denied = requests.get(f"{API_BASE_URL}{path}", headers=_auth_headers(plain["access_token"]), timeout=10)
        assert denied.status_code == 403 and denied.json()["error"]["message"] == "Acces administrateur requis", denied.text
    assert _post(f"/admin/feedback/{plain['user']['id']}/traiter", plain["access_token"]).status_code == 403

    admin = _register_user(_rand_email("adminnomfa"))
    _make_admin(admin["user"]["email"])
    no_mfa = requests.get(f"{API_BASE_URL}/admin/stats", headers=_auth_headers(admin["access_token"]), timeout=10)
    assert no_mfa.status_code == 403 and "double authentification" in no_mfa.json()["error"]["message"], no_mfa.text


def test_admin_with_mfa_lists_and_processes_feedback() -> None:
    author = _register_user(_rand_email("adminauthor"))
    created = _post("/feedback", author["access_token"], category="idee", message="Une idee de test pour l'administration.", context="admin")
    assert created.status_code == 201, created.text
    feedback_id = created.json()["id"]

    admin = _register_user(_rand_email("adminok"))
    _make_admin(admin["user"]["email"])
    mfa = _enable_mfa(admin)
    headers = _auth_headers(mfa["token"])

    pending = requests.get(f"{API_BASE_URL}/admin/feedback", headers=headers, timeout=10)
    assert pending.status_code == 200, pending.text
    entry = next(item for item in pending.json() if item["id"] == feedback_id)
    assert entry["email"] == author["user"]["email"] and entry["traite_le"] is None

    assert _post("/admin/feedback/00000000-0000-0000-0000-000000000000/traiter", mfa["token"]).status_code == 404
    done = _post(f"/admin/feedback/{feedback_id}/traiter", mfa["token"], note="vu")
    assert done.status_code == 200 and done.json()["traite_le"] and done.json()["note_traitement"] == "vu"
    assert feedback_id not in [item["id"] for item in requests.get(f"{API_BASE_URL}/admin/feedback", headers=headers, timeout=10).json()]
    everything = requests.get(f"{API_BASE_URL}/admin/feedback?tous=true", headers=headers, timeout=10).json()
    assert feedback_id in [item["id"] for item in everything]
    assert _psql("SELECT traite_le IS NOT NULL FROM beta_feedback WHERE id = :'fid';", fid=feedback_id) == "t"

    stats = requests.get(f"{API_BASE_URL}/admin/stats", headers=headers, timeout=10)
    assert stats.status_code == 200, stats.text
    counts = stats.json()
    assert counts["comptes"] >= 2 and counts["comptes_actifs_30j"] >= 1 and counts["visites_30j"] >= 0
