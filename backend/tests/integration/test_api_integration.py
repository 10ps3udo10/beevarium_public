from datetime import datetime, timezone
import os
import random
import time
from urllib.parse import parse_qs, urlparse

import pytest
import requests


API_BASE_URL = os.getenv("BEEVARIUM_API_URL", "http://localhost:8000").rstrip("/")


def _rand_email(prefix: str = "itest") -> str:
    return f"{prefix}{random.randint(100000, 999999)}@example.com"


def _register_user(email: str, prenom: str = "Test", is_premium: bool = False) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"email": email, "prenom": prenom, "password": "motdepasse123", "is_premium": is_premium},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login_user(email: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": "motdepasse123"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
def api_health_check() -> None:
    deadline = time.time() + 45
    last_error: str | None = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return
            last_error = f"status={response.status_code} body={response.text}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1.5)

    assert False, (
        "API indisponible pour les tests d integration apres attente active. "
        f"Verifier {API_BASE_URL} et docker compose up. Derniere erreur: {last_error}"
    )


def test_health_returns_metadata_and_request_id() -> None:
    response = requests.get(f"{API_BASE_URL}/health", headers={"X-Request-ID": "itest-request-123"}, timeout=10)
    assert response.status_code == 200, response.text
    assert response.headers["X-Request-ID"] == "itest-request-123"
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["app_version"]
    assert payload["environment"]


def test_beta_feedback_is_authenticated_and_scoped_to_author() -> None:
    user_a = _register_user(_rand_email("feedbacka"), prenom="FeedbackA")
    user_b = _register_user(_rand_email("feedbackb"), prenom="FeedbackB")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])
    payload = {
        "category": "bug",
        "message": "La saisie de visite est difficile a comprendre.",
        "context": "Onglet visites",
    }

    anonymous = requests.post(f"{API_BASE_URL}/feedback", json=payload, timeout=10)
    assert anonymous.status_code == 403, anonymous.text

    created = requests.post(f"{API_BASE_URL}/feedback", headers=headers_a, json=payload, timeout=10)
    assert created.status_code == 201, created.text
    feedback_id = created.json()["id"]

    mine_a = requests.get(f"{API_BASE_URL}/feedback/mine", headers=headers_a, timeout=10)
    assert mine_a.status_code == 200, mine_a.text
    assert any(item["id"] == feedback_id for item in mine_a.json())

    mine_b = requests.get(f"{API_BASE_URL}/feedback/mine", headers=headers_b, timeout=10)
    assert mine_b.status_code == 200, mine_b.text
    assert not any(item["id"] == feedback_id for item in mine_b.json())


def test_api_event_log_records_authenticated_requests() -> None:
    email = _rand_email("events")
    auth_payload = _register_user(email, prenom="Events")
    headers = _auth_headers(auth_payload["access_token"])

    response = requests.get(
        f"{API_BASE_URL}/auth/me",
        headers={**headers, "X-Request-ID": "itest-event-request"},
        timeout=10,
    )
    assert response.status_code == 200, response.text

    events_response = requests.get(f"{API_BASE_URL}/events/api", headers=headers, timeout=10)
    assert events_response.status_code == 200, events_response.text
    events_payload = events_response.json()
    assert events_payload, "Le journal API devrait contenir au moins un evenement"
    assert any(event["path"] == "/auth/me" and event["request_id"] == "itest-event-request" for event in events_payload)


def test_auth_register_login_me() -> None:
    email = _rand_email("auth")
    registered = _register_user(email.upper(), prenom="Auth")
    token = registered["access_token"]

    me = requests.get(f"{API_BASE_URL}/auth/me", headers=_auth_headers(token), timeout=10)
    assert me.status_code == 200, me.text
    me_payload = me.json()
    assert me_payload["email"] == email

    logged_in = _login_user(email)
    login_token = logged_in["access_token"]
    assert isinstance(login_token, str)
    assert len(login_token) > 20

    duplicate = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"email": email.upper(), "prenom": "Auth", "password": "motdepasse123"},
        timeout=10,
    )
    assert duplicate.status_code == 409, duplicate.text


def test_root_redirects_to_web_app() -> None:
    response = requests.get(f"{API_BASE_URL}/", allow_redirects=False, timeout=10)
    assert response.status_code == 307, response.text
    assert response.headers["location"] == "/app/"


def test_update_profile_prenom() -> None:
    email = _rand_email("profile")
    registered = _register_user(email, prenom="Avant")
    token = registered["access_token"]

    update_response = requests.patch(
        f"{API_BASE_URL}/users/me",
        headers=_auth_headers(token),
        json={"prenom": "Apres"},
        timeout=10,
    )
    assert update_response.status_code == 200, update_response.text
    update_payload = update_response.json()
    assert update_payload["prenom"] == "Apres"

    me_response = requests.get(f"{API_BASE_URL}/users/me", headers=_auth_headers(token), timeout=10)
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["prenom"] == "Apres"


def test_get_user_by_id_access_rules() -> None:
    user_a = _register_user(_rand_email("userida"), prenom="UserA")
    user_b = _register_user(_rand_email("useridb"), prenom="UserB")

    headers_a = _auth_headers(user_a["access_token"])

    me_resp = requests.get(f"{API_BASE_URL}/auth/me", headers=headers_a, timeout=10)
    assert me_resp.status_code == 200, me_resp.text
    user_a_id = me_resp.json()["id"]

    get_self_resp = requests.get(f"{API_BASE_URL}/users/{user_a_id}", headers=headers_a, timeout=10)
    assert get_self_resp.status_code == 200, get_self_resp.text
    assert get_self_resp.json()["email"] == user_a["user"]["email"]

    get_other_resp = requests.get(f"{API_BASE_URL}/users/{user_b['user']['id']}", headers=headers_a, timeout=10)
    assert get_other_resp.status_code == 403, get_other_resp.text
    assert get_other_resp.json()["error"]["message"] == "Acces refuse"


def test_logout_invalidates_token() -> None:
    email = _rand_email("logout")
    registered = _register_user(email, prenom="Logout")
    token = registered["access_token"]

    logout_response = requests.post(f"{API_BASE_URL}/auth/logout", headers=_auth_headers(token), timeout=10)
    assert logout_response.status_code == 200, logout_response.text
    assert logout_response.json()["message"] == "Deconnexion prise en compte"

    me_after_logout = requests.get(f"{API_BASE_URL}/auth/me", headers=_auth_headers(token), timeout=10)
    assert me_after_logout.status_code == 401, me_after_logout.text
    assert me_after_logout.json()["error"]["message"] == "Token invalide ou expire"


def test_validation_error_uses_standard_envelope() -> None:
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"email": "not-an-email", "prenom": "Auth", "password": "123"},
        timeout=10,
    )
    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Validation error"
    assert isinstance(payload["error"]["details"], list)
    assert payload["error"]["details"]
    assert any(detail["loc"][-1] == "email" for detail in payload["error"]["details"])


def test_ownership_isolation_on_rucher() -> None:
    user_a = _register_user(_rand_email("ownera"), prenom="OwnerA")
    user_b = _register_user(_rand_email("ownerb"), prenom="OwnerB")

    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    rucher_create = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers_a,
        json={
            "nom": "Rucher Prive A",
            "latitude": 45.1,
            "longitude": 3.1,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_create.status_code == 201, rucher_create.text
    rucher_id = rucher_create.json()["id"]

    forbidden_read = requests.get(f"{API_BASE_URL}/ruchers/{rucher_id}", headers=headers_b, timeout=10)
    assert forbidden_read.status_code == 404, forbidden_read.text


def test_account_isolation_on_private_reference_and_hive_endpoints() -> None:
    user_a = _register_user(_rand_email("privatea"), prenom="PrivateA")
    user_b = _register_user(_rand_email("privateb"), prenom="PrivateB")

    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    custom_ref = requests.post(
        f"{API_BASE_URL}/references/type-ruche",
        headers=headers_a,
        json={"libelle": "Type Prive A"},
        timeout=10,
    )
    assert custom_ref.status_code == 201, custom_ref.text
    custom_ref_id = custom_ref.json()["id"]

    listed_by_b = requests.get(f"{API_BASE_URL}/references/type-ruche", headers=headers_b, timeout=10)
    assert listed_by_b.status_code == 200, listed_by_b.text
    assert not any(item["id"] == custom_ref_id for item in listed_by_b.json())

    rucher_create = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers_a,
        json={
            "nom": "Rucher Prive A 2",
            "latitude": 45.2,
            "longitude": 3.2,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_create.status_code == 201, rucher_create.text
    rucher_id = rucher_create.json()["id"]

    ruche_create = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers_a,
        json={
            "identifiant_personnalise": "PRIVATE-42",
            "rucher_id": rucher_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_create.status_code == 201, ruche_create.text
    ruche_id = ruche_create.json()["id"]

    forbidden_rucher = requests.get(f"{API_BASE_URL}/ruchers/{rucher_id}", headers=headers_b, timeout=10)
    assert forbidden_rucher.status_code == 404, forbidden_rucher.text

    forbidden_ruche = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers_b, timeout=10)
    assert forbidden_ruche.status_code == 404, forbidden_ruche.text

    tag = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers_a, json={"libelle": "a surveiller"}, timeout=10)
    assert tag.status_code == 201, tag.text
    forbidden_tags = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers_b, timeout=10)
    assert forbidden_tags.status_code == 404, forbidden_tags.text
    forbidden_tag_create = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers_b, json={"libelle": "a nourrir"}, timeout=10)
    assert forbidden_tag_create.status_code == 404, forbidden_tag_create.text
    forbidden_tag_delete = requests.delete(f"{API_BASE_URL}/ruches/{ruche_id}/tags/{tag.json()['id']}", headers=headers_b, timeout=10)
    assert forbidden_tag_delete.status_code == 404, forbidden_tag_delete.text

    reine = requests.post(
        f"{API_BASE_URL}/ruches/{ruche_id}/reines",
        headers=headers_a,
        json={"date_mise_en_place": "2026-01-01T00:00:00Z", "origine": "inconnue"},
        timeout=10,
    )
    assert reine.status_code == 201, reine.text
    forbidden_reines = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/reines", headers=headers_b, timeout=10)
    assert forbidden_reines.status_code == 404, forbidden_reines.text
    forbidden_reine_create = requests.post(
        f"{API_BASE_URL}/ruches/{ruche_id}/reines",
        headers=headers_b,
        json={"date_mise_en_place": "2026-02-01T00:00:00Z", "origine": "remerage"},
        timeout=10,
    )
    assert forbidden_reine_create.status_code == 404, forbidden_reine_create.text

    forbidden_move = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers_b,
        json={"ruche_ids": [ruche_id], "move_to_atelier": True, "target_rucher_id": None},
        timeout=10,
    )
    assert forbidden_move.status_code == 404, forbidden_move.text


def test_ruche_tags_are_manual_with_effects_and_derived_atelier_tag() -> None:
    user = _register_user(_rand_email("tags"), prenom="Tags")
    headers = _auth_headers(user["access_token"])

    types = requests.get(f"{API_BASE_URL}/references/type-ruche", headers=headers, timeout=10)
    assert types.status_code == 200, types.text
    starter_type = next(item for item in types.json() if item["libelle"] == "Starter")

    rucher = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Tags",
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher.status_code == 201, rucher.text

    ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "TAG-1", "rucher_id": rucher.json()["id"], "is_at_atelier": False},
        timeout=10,
    )
    assert ruche.status_code == 201, ruche.text
    ruche_id = ruche.json()["id"]

    reine = requests.post(
        f"{API_BASE_URL}/ruches/{ruche_id}/reines",
        headers=headers,
        json={"date_mise_en_place": datetime.utcnow().isoformat(), "origine": "inconnue"},
        timeout=10,
    )
    assert reine.status_code == 201, reine.text

    starter_tag = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "starter"}, timeout=10)
    assert starter_tag.status_code == 201, starter_tag.text
    updated_ruche = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10)
    assert updated_ruche.status_code == 200, updated_ruche.text
    assert updated_ruche.json()["ref_type_ruche_id"] == starter_type["id"]
    assert any(tag["libelle"] == "starter" for tag in updated_ruche.json()["tags"])

    duplicate = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "Starter"}, timeout=10)
    assert duplicate.status_code == 409, duplicate.text

    queen_not_seen = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "reine non vue"}, timeout=10)
    assert queen_not_seen.status_code == 201, queen_not_seen.text
    visit_seen = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": ruche_id, "visite_rucher_id": None, "reine_vue": True, "statut_validation": "valide"},
        timeout=10,
    )
    assert visit_seen.status_code == 201, visit_seen.text
    after_seen = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert all(tag["libelle"] != "reine non vue" for tag in after_seen.json())

    visit_low_reserves = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": ruche_id, "visite_rucher_id": None, "reserves_nourriture": "critique", "statut_validation": "valide"},
        timeout=10,
    )
    assert visit_low_reserves.status_code == 201, visit_low_reserves.text
    assert set(visit_low_reserves.json()["tag_suggestions"]) >= {"reserves faibles", "a nourrir"}
    after_suggestion = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert all(tag["libelle"] != "reserves faibles" for tag in after_suggestion.json())

    event_tag = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "candi pose"}, timeout=10)
    assert event_tag.status_code == 201, event_tag.text
    orphan_suggestion = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": ruche_id, "visite_rucher_id": None, "reine_vue": False, "nombre_cadres_couvain": 0, "statut_validation": "valide"},
        timeout=10,
    )
    assert orphan_suggestion.status_code == 201, orphan_suggestion.text
    assert set(orphan_suggestion.json()["tag_suggestions"]) >= {"reine non vue", "orpheline", "a surveiller", "absence couvain"}
    assert orphan_suggestion.json()["tag_removal_suggestions"] == ["candi pose"]
    after_event_visit = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert all(tag["libelle"] != "candi pose" for tag in after_event_visit.json())
    assert all(tag["libelle"] != "orpheline" for tag in after_event_visit.json())

    two_supers = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "2 hausses posees"}, timeout=10)
    assert two_supers.status_code == 201, two_supers.text
    five_supers = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "5 hausses posees"}, timeout=10)
    assert five_supers.status_code == 201, five_supers.text
    tagged = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert tagged.status_code == 200, tagged.text
    hausse_tags = [tag["libelle"] for tag in tagged.json() if "hausse" in tag["libelle"] and "posee" in tag["libelle"]]
    assert hausse_tags == ["5 hausses posees"]

    quarantine = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "quarantaine"}, timeout=10)
    assert quarantine.status_code == 201, quarantine.text
    watch = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "a surveiller"}, timeout=10)
    assert watch.status_code == 201, watch.text
    dead_colony = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "colonie morte"}, timeout=10)
    assert dead_colony.status_code == 201, dead_colony.text
    after_death = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert after_death.status_code == 200, after_death.text
    assert [tag["libelle"] for tag in after_death.json()] == ["colonie morte"]
    rejected = requests.post(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, json={"libelle": "active"}, timeout=10)
    assert rejected.status_code == 409, rejected.text
    reines_after_death = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/reines", headers=headers, timeout=10)
    assert reines_after_death.status_code == 200, reines_after_death.text
    assert reines_after_death.json()[0]["statut"] == "terminee"
    moved_dead = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={"ruche_ids": [ruche_id], "move_to_atelier": True, "target_rucher_id": None},
        timeout=10,
    )
    assert moved_dead.status_code == 200, moved_dead.text
    after_workshop = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10)
    assert after_workshop.status_code == 200, after_workshop.text
    assert all(tag["libelle"] != "colonie morte" for tag in after_workshop.json())

    atelier_ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "TAG-ATELIER", "rucher_id": None, "is_at_atelier": True},
        timeout=10,
    )
    assert atelier_ruche.status_code == 201, atelier_ruche.text
    tags = requests.get(f"{API_BASE_URL}/ruches/{atelier_ruche.json()['id']}/tags", headers=headers, timeout=10)
    assert tags.status_code == 200, tags.text
    assert any(tag["libelle"] == "atelier" and tag["source"] == "derive" for tag in tags.json())


def test_rucher_filters_by_name_and_status() -> None:
    user = _register_user(_rand_email("filter"), prenom="Filter")
    headers = _auth_headers(user["access_token"])

    payloads = [
        {
            "nom": "Rucher Maison Sud",
            "latitude": 45.2,
            "longitude": 3.2,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        {
            "nom": "Rucher Forêt Nord",
            "latitude": 45.3,
            "longitude": 3.3,
            "type_terrain": "forêt",
            "statut_activite": "inactif",
            "statut_peuplement": "vide",
        },
    ]

    created = []
    for payload in payloads:
        response = requests.post(f"{API_BASE_URL}/ruchers", headers=headers, json=payload, timeout=10)
        assert response.status_code == 201, response.text
        created.append(response.json())

    by_name = requests.get(f"{API_BASE_URL}/ruchers", headers=headers, params={"nom": "Maison"}, timeout=10)
    assert by_name.status_code == 200, by_name.text
    by_name_payload = by_name.json()
    assert len(by_name_payload) == 1
    assert by_name_payload[0]["nom"] == "Rucher Maison Sud"

    by_status = requests.get(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        params={"statut_activite": "inactif", "statut_peuplement": "vide"},
        timeout=10,
    )
    assert by_status.status_code == 200, by_status.text
    by_status_payload = by_status.json()
    assert len(by_status_payload) == 1
    assert by_status_payload[0]["nom"] == "Rucher Forêt Nord"

    by_terrain = requests.get(f"{API_BASE_URL}/ruchers", headers=headers, params={"type_terrain": "plaine"}, timeout=10)
    assert by_terrain.status_code == 200, by_terrain.text
    by_terrain_payload = by_terrain.json()
    assert len(by_terrain_payload) == 1
    assert by_terrain_payload[0]["nom"] == "Rucher Maison Sud"


def test_update_rucher_coordinates_and_type_terrain() -> None:
    user = _register_user(_rand_email("geo"), prenom="Geo")
    headers = _auth_headers(user["access_token"])

    create_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Geo",
            "latitude": 45.123456,
            "longitude": 3.123456,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    rucher_id = create_resp.json()["id"]

    update_resp = requests.put(
        f"{API_BASE_URL}/ruchers/{rucher_id}",
        headers=headers,
        json={
            "nom": "Rucher Geo Maj",
            "latitude": 46.234567,
            "longitude": 4.234567,
            "type_terrain": "montagne",
            "statut_activite": "actif",
            "statut_peuplement": "vide",
        },
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    update_payload = update_resp.json()
    assert update_payload["nom"] == "Rucher Geo Maj"
    assert update_payload["latitude"] == pytest.approx(46.234567)
    assert update_payload["longitude"] == pytest.approx(4.234567)
    assert update_payload["type_terrain"] == "montagne"
    assert update_payload["statut_peuplement"] == "vide"

    get_resp = requests.get(f"{API_BASE_URL}/ruchers/{rucher_id}", headers=headers, timeout=10)
    assert get_resp.status_code == 200, get_resp.text
    get_payload = get_resp.json()
    assert get_payload["latitude"] == pytest.approx(46.234567)
    assert get_payload["longitude"] == pytest.approx(4.234567)
    assert get_payload["type_terrain"] == "montagne"


def test_archive_rucher_sets_statut_inactif() -> None:
    user = _register_user(_rand_email("archive"), prenom="Archive")
    headers = _auth_headers(user["access_token"])

    create_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher a archiver",
            "latitude": 45.11,
            "longitude": 3.11,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    rucher_id = create_resp.json()["id"]

    archive_resp = requests.post(f"{API_BASE_URL}/ruchers/{rucher_id}/archive", headers=headers, timeout=10)
    assert archive_resp.status_code == 200, archive_resp.text
    archive_payload = archive_resp.json()
    assert archive_payload["statut_activite"] == "inactif"

    filtered = requests.get(f"{API_BASE_URL}/ruchers", headers=headers, params={"statut_activite": "inactif"}, timeout=10)
    assert filtered.status_code == 200, filtered.text
    filtered_payload = filtered.json()
    assert any(item["id"] == rucher_id and item["statut_activite"] == "inactif" for item in filtered_payload)


def test_free_plan_is_limited_to_two_ruchers_while_premium_is_unlimited() -> None:
    free_user = _register_user(_rand_email("freeplan"), prenom="Free", is_premium=False)
    premium_user = _register_user(_rand_email("premiumplan"), prenom="Premium", is_premium=True)

    free_headers = _auth_headers(free_user["access_token"])
    premium_headers = _auth_headers(premium_user["access_token"])

    for idx in range(2):
        free_create = requests.post(
            f"{API_BASE_URL}/ruchers",
            headers=free_headers,
            json={
                "nom": f"Rucher Free {idx + 1}",
                "latitude": 45.2 + idx,
                "longitude": 3.2 + idx,
                "type_terrain": "plaine",
                "statut_activite": "actif",
                "statut_peuplement": "peuple",
            },
            timeout=10,
        )
        assert free_create.status_code == 201, free_create.text

    free_third = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=free_headers,
        json={
            "nom": "Rucher Free 3",
            "latitude": 47.2,
            "longitude": 5.2,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert free_third.status_code == 403, free_third.text
    assert free_third.json()["error"]["message"] == "Limite gratuite atteinte: passez premium pour creer plus de 2 ruchers"

    for idx in range(3):
        premium_create = requests.post(
            f"{API_BASE_URL}/ruchers",
            headers=premium_headers,
            json={
                "nom": f"Rucher Premium {idx + 1}",
                "latitude": 48.2 + idx,
                "longitude": 6.2 + idx,
                "type_terrain": "montagne",
                "statut_activite": "actif",
                "statut_peuplement": "peuple",
            },
            timeout=10,
        )
        assert premium_create.status_code == 201, premium_create.text


def test_visite_rucher_crud() -> None:
    user = _register_user(_rand_email("vrucher"), prenom="Rucher")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Visite Globale",
            "latitude": 45.61,
            "longitude": 3.61,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text
    rucher_id = rucher_resp.json()["id"]

    create_resp = requests.post(
        f"{API_BASE_URL}/visites-rucher",
        headers=headers,
        json={
            "rucher_id": rucher_id,
            "note_meteo": "ensoleille",
            "impression_generale": "Belle activite",
            "note_globale": 4,
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    visite_rucher_id = create_resp.json()["id"]

    list_resp = requests.get(f"{API_BASE_URL}/visites-rucher", headers=headers, params={"rucher_id": rucher_id}, timeout=10)
    assert list_resp.status_code == 200, list_resp.text
    list_payload = list_resp.json()
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == visite_rucher_id
    assert list_payload[0]["note_globale"] == 4

    update_resp = requests.put(
        f"{API_BASE_URL}/visites-rucher/{visite_rucher_id}",
        headers=headers,
        json={
            "rucher_id": rucher_id,
            "note_meteo": "nuageux",
            "impression_generale": "Activite moderee",
            "note_globale": 3,
        },
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    update_payload = update_resp.json()
    assert update_payload["note_meteo"] == "nuageux"
    assert update_payload["impression_generale"] == "Activite moderee"
    assert update_payload["note_globale"] == 3

    get_resp = requests.get(f"{API_BASE_URL}/visites-rucher/{visite_rucher_id}", headers=headers, timeout=10)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["note_globale"] == 3

    delete_resp = requests.delete(f"{API_BASE_URL}/visites-rucher/{visite_rucher_id}", headers=headers, timeout=10)
    assert delete_resp.status_code == 204, delete_resp.text

    missing_resp = requests.get(f"{API_BASE_URL}/visites-rucher/{visite_rucher_id}", headers=headers, timeout=10)
    assert missing_resp.status_code == 404, missing_resp.text


def test_visite_ruche_actions_and_intervention_sanitaire() -> None:
    user = _register_user(_rand_email("vruche"), prenom="Ruche")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Visite Ruche",
            "latitude": 45.71,
            "longitude": 3.71,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "VR-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text

    action_refs = requests.get(f"{API_BASE_URL}/references/action-visite", headers=headers, timeout=10)
    assert action_refs.status_code == 200, action_refs.text
    action_payload = action_refs.json()
    assert len(action_payload) >= 2

    intervention_refs = requests.get(f"{API_BASE_URL}/references/type-intervention", headers=headers, timeout=10)
    assert intervention_refs.status_code == 200, intervention_refs.text
    intervention_payload = intervention_refs.json()
    assert intervention_payload

    visite_payload = {
        "ruche_id": ruche_resp.json()["id"],
        "visite_rucher_id": None,
        "reine_vue": True,
        "presence_ponte": True,
        "etat_couvain": "normal",
        "nombre_cadres_couvain": 4,
        "reserves_nourriture": "correct",
        "agressivite": 2,
        "note_ruche": 4,
        "nombre_cadres_total": 10,
        "source_saisie": "manuelle",
        "statut_validation": "valide",
        "action_ids": [action_payload[0]["id"], action_payload[1]["id"]],
        "interventions": [
            {
                "ref_type_intervention_id": intervention_payload[0]["id"],
                "details": "Traitement local",
            }
        ],
        "mouvements_cadres": [],
        "mouvements_hausses": [],
    }

    create_resp = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=visite_payload, timeout=10)
    assert create_resp.status_code == 201, create_resp.text
    create_payload = create_resp.json()
    assert len(create_payload["actions"]) == 2
    assert {action["libelle"] for action in create_payload["actions"]} == {
        action_payload[0]["libelle"],
        action_payload[1]["libelle"],
    }
    assert len(create_payload["interventions"]) == 1
    assert create_payload["interventions"][0]["details"] == "Traitement local"

    get_resp = requests.get(f"{API_BASE_URL}/visites/{create_payload['id']}", headers=headers, timeout=10)
    assert get_resp.status_code == 200, get_resp.text
    get_payload = get_resp.json()
    assert len(get_payload["actions"]) == 2
    assert len(get_payload["interventions"]) == 1


def test_visite_ruche_update_delete_filters_and_ownership() -> None:
    user_a = _register_user(_rand_email("vcrudA"), prenom="VisiteA")
    user_b = _register_user(_rand_email("vcrudB"), prenom="VisiteB")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers_a,
        json={
            "nom": "Rucher Visite CRUD",
            "latitude": 46.31,
            "longitude": 4.31,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers_a,
        json={
            "identifiant_personnalise": "VCRUD-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    create_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers_a,
        json={
            "ruche_id": ruche_id,
            "visite_rucher_id": None,
            "reine_vue": True,
            "presence_ponte": True,
            "etat_couvain": "normal",
            "nombre_cadres_couvain": 4,
            "reserves_nourriture": "correct",
            "agressivite": 2,
            "note_ruche": 4,
            "nombre_cadres_total": 10,
            "source_saisie": "manuelle",
            "statut_validation": "valide",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    visite_id = create_resp.json()["id"]

    update_resp = requests.put(
        f"{API_BASE_URL}/visites/{visite_id}",
        headers=headers_a,
        json={
            "ruche_id": ruche_id,
            "visite_rucher_id": None,
            "reine_vue": True,
            "presence_ponte": True,
            "etat_couvain": "excellent",
            "nombre_cadres_couvain": 5,
            "reserves_nourriture": "abondant",
            "agressivite": 1,
            "note_ruche": 5,
            "nombre_cadres_total": 10,
            "source_saisie": "ia_vocale",
            "statut_validation": "brouillon",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    update_payload = update_resp.json()
    assert update_payload["etat_couvain"] == "excellent"
    assert update_payload["source_saisie"] == "ia_vocale"
    assert update_payload["statut_validation"] == "brouillon"

    filtered_resp = requests.get(
        f"{API_BASE_URL}/visites",
        headers=headers_a,
        params={"ruche_id": ruche_id, "source_saisie": "ia_vocale", "statut_validation": "brouillon"},
        timeout=10,
    )
    assert filtered_resp.status_code == 200, filtered_resp.text
    filtered_payload = filtered_resp.json()
    assert len(filtered_payload) == 1
    assert filtered_payload[0]["id"] == visite_id

    forbidden_get = requests.get(f"{API_BASE_URL}/visites/{visite_id}", headers=headers_b, timeout=10)
    assert forbidden_get.status_code == 404, forbidden_get.text

    delete_resp = requests.delete(f"{API_BASE_URL}/visites/{visite_id}", headers=headers_a, timeout=10)
    assert delete_resp.status_code == 204, delete_resp.text

    missing_resp = requests.get(f"{API_BASE_URL}/visites/{visite_id}", headers=headers_a, timeout=10)
    assert missing_resp.status_code == 404, missing_resp.text


def test_visites_synthese_periode_aggregates_visites_ruche_and_rucher() -> None:
    user = _register_user(_rand_email("vsynth"), prenom="VSynth")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Synthese",
            "latitude": 46.41,
            "longitude": 4.41,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text
    rucher_id = rucher_resp.json()["id"]

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "SYNTH-1",
            "rucher_id": rucher_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    visite_rucher_resp = requests.post(
        f"{API_BASE_URL}/visites-rucher",
        headers=headers,
        json={
            "rucher_id": rucher_id,
            "note_meteo": "soleil",
            "impression_generale": "Bonne activite",
            "note_globale": 4,
        },
        timeout=10,
    )
    assert visite_rucher_resp.status_code == 201, visite_rucher_resp.text
    visite_rucher_id = visite_rucher_resp.json()["id"]

    visite_manuelle_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={
            "ruche_id": ruche_id,
            "visite_rucher_id": visite_rucher_id,
            "reine_vue": True,
            "presence_ponte": True,
            "etat_couvain": "normal",
            "nombre_cadres_couvain": 4,
            "reserves_nourriture": "correct",
            "agressivite": 2,
            "note_ruche": 4,
            "nombre_cadres_total": 10,
            "source_saisie": "manuelle",
            "statut_validation": "valide",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert visite_manuelle_resp.status_code == 201, visite_manuelle_resp.text

    visite_ia_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={
            "ruche_id": ruche_id,
            "visite_rucher_id": visite_rucher_id,
            "reine_vue": False,
            "presence_ponte": True,
            "etat_couvain": "normal",
            "nombre_cadres_couvain": 3,
            "reserves_nourriture": "correct",
            "agressivite": 3,
            "note_ruche": 3,
            "nombre_cadres_total": 10,
            "source_saisie": "ia_vocale",
            "statut_validation": "brouillon",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert visite_ia_resp.status_code == 201, visite_ia_resp.text

    today = datetime.utcnow().date().isoformat()
    synthese_resp = requests.get(
        f"{API_BASE_URL}/visites/synthese/periode",
        headers=headers,
        params={"rucher_id": rucher_id, "start_date": today, "end_date": today},
        timeout=10,
    )
    assert synthese_resp.status_code == 200, synthese_resp.text
    payload = synthese_resp.json()
    assert payload["total_visites_ruche"] == 2
    assert payload["total_visites_rucher"] == 1
    assert payload["visites_manuelles"] == 1
    assert payload["visites_ia_vocale"] == 1
    assert payload["brouillons_ia"] == 1
    assert payload["note_ruche_moyenne"] == 3.5
    assert payload["note_rucher_moyenne"] == 4.0
    assert payload["taux_reine_vue"] == 0.5


def test_patch_visite_rejects_partial_update_with_incoherent_ruche_rucher_link() -> None:
    user = _register_user(_rand_email("vpatch"), prenom="VPatch")
    headers = _auth_headers(user["access_token"])

    rucher_a_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Patch A",
            "latitude": 46.61,
            "longitude": 4.61,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_a_resp.status_code == 201, rucher_a_resp.text
    rucher_a_id = rucher_a_resp.json()["id"]

    rucher_b_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Patch B",
            "latitude": 46.62,
            "longitude": 4.62,
            "type_terrain": "montagne",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_b_resp.status_code == 201, rucher_b_resp.text
    rucher_b_id = rucher_b_resp.json()["id"]

    ruche_a_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "PATCH-A",
            "rucher_id": rucher_a_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_a_resp.status_code == 201, ruche_a_resp.text
    ruche_a_id = ruche_a_resp.json()["id"]

    ruche_b_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "PATCH-B",
            "rucher_id": rucher_b_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_b_resp.status_code == 201, ruche_b_resp.text
    ruche_b_id = ruche_b_resp.json()["id"]

    visite_rucher_resp = requests.post(
        f"{API_BASE_URL}/visites-rucher",
        headers=headers,
        json={
            "rucher_id": rucher_a_id,
            "note_meteo": "nuageux",
            "impression_generale": "RAS",
            "note_globale": 3,
        },
        timeout=10,
    )
    assert visite_rucher_resp.status_code == 201, visite_rucher_resp.text
    visite_rucher_id = visite_rucher_resp.json()["id"]

    visite_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={
            "ruche_id": ruche_a_id,
            "visite_rucher_id": visite_rucher_id,
            "reine_vue": True,
            "presence_ponte": True,
            "etat_couvain": "normal",
            "nombre_cadres_couvain": 4,
            "reserves_nourriture": "correct",
            "agressivite": 2,
            "note_ruche": 4,
            "nombre_cadres_total": 10,
            "source_saisie": "manuelle",
            "statut_validation": "valide",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert visite_resp.status_code == 201, visite_resp.text
    visite_id = visite_resp.json()["id"]

    incoherent_patch = requests.patch(
        f"{API_BASE_URL}/visites/{visite_id}",
        headers=headers,
        json={
            "ruche_id": ruche_b_id,
            "visite_rucher_id": visite_rucher_id,
        },
        timeout=10,
    )
    assert incoherent_patch.status_code == 422, incoherent_patch.text
    assert incoherent_patch.json()["error"]["message"] == "La visite rucher doit correspondre au rucher de la ruche"


def test_visites_filters_reject_invalid_values_and_patch_requires_payload() -> None:
    user = _register_user(_rand_email("vguard"), prenom="VGuard")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Guard",
            "latitude": 46.71,
            "longitude": 4.71,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "GUARD-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    visite_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={
            "ruche_id": ruche_id,
            "visite_rucher_id": None,
            "reine_vue": True,
            "presence_ponte": True,
            "etat_couvain": "normal",
            "nombre_cadres_couvain": 4,
            "reserves_nourriture": "correct",
            "agressivite": 2,
            "note_ruche": 4,
            "nombre_cadres_total": 10,
            "source_saisie": "manuelle",
            "statut_validation": "valide",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert visite_resp.status_code == 201, visite_resp.text
    visite_id = visite_resp.json()["id"]

    bad_source = requests.get(
        f"{API_BASE_URL}/visites",
        headers=headers,
        params={"ruche_id": ruche_id, "source_saisie": "automatique"},
        timeout=10,
    )
    assert bad_source.status_code == 422, bad_source.text
    assert bad_source.json()["error"]["message"] == "source_saisie invalide"

    bad_statut = requests.get(
        f"{API_BASE_URL}/visites",
        headers=headers,
        params={"ruche_id": ruche_id, "statut_validation": "draft"},
        timeout=10,
    )
    assert bad_statut.status_code == 422, bad_statut.text
    assert bad_statut.json()["error"]["message"] == "statut_validation invalide"

    empty_patch = requests.patch(f"{API_BASE_URL}/visites/{visite_id}", headers=headers, json={}, timeout=10)
    assert empty_patch.status_code == 422, empty_patch.text
    assert empty_patch.json()["error"]["message"] == "Aucun champ a mettre a jour"


def test_visites_synthese_periode_rejects_invalid_date_range() -> None:
    user = _register_user(_rand_email("vsynthrange"), prenom="VSynthRange")
    headers = _auth_headers(user["access_token"])

    invalid_range_resp = requests.get(
        f"{API_BASE_URL}/visites/synthese/periode",
        headers=headers,
        params={"start_date": "2026-08-12", "end_date": "2026-08-01"},
        timeout=10,
    )
    assert invalid_range_resp.status_code == 422, invalid_range_resp.text
    assert invalid_range_resp.json()["error"]["message"] == "start_date doit etre <= end_date"


def test_quick_add_reference_option_can_be_used_immediately() -> None:
    user = _register_user(_rand_email("refs"), prenom="Refs")
    headers = _auth_headers(user["access_token"])

    create_option_resp = requests.post(
        f"{API_BASE_URL}/references/type-ruche",
        headers=headers,
        json={"libelle": "Langstroth perso"},
        timeout=10,
    )
    assert create_option_resp.status_code == 201, create_option_resp.text
    custom_type_ruche = create_option_resp.json()
    assert custom_type_ruche["libelle"] == "Langstroth perso"

    list_options_resp = requests.get(f"{API_BASE_URL}/references/type-ruche", headers=headers, timeout=10)
    assert list_options_resp.status_code == 200, list_options_resp.text
    list_options_payload = list_options_resp.json()
    assert any(option["id"] == custom_type_ruche["id"] for option in list_options_payload)

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Reference",
            "latitude": 45.81,
            "longitude": 3.81,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "REF-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": custom_type_ruche["id"],
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_payload = ruche_resp.json()
    assert ruche_payload["ref_type_ruche_id"] == custom_type_ruche["id"]

    get_ruche_resp = requests.get(f"{API_BASE_URL}/ruches/{ruche_payload['id']}", headers=headers, timeout=10)
    assert get_ruche_resp.status_code == 200, get_ruche_resp.text
    assert get_ruche_resp.json()["ref_type_ruche_id"] == custom_type_ruche["id"]


def test_ruche_cannot_use_another_user_reference_options() -> None:
    owner = _register_user(_rand_email("refowner"), prenom="RefOwner")
    outsider = _register_user(_rand_email("refoutsider"), prenom="RefOutsider")
    owner_headers = _auth_headers(owner["access_token"])
    outsider_headers = _auth_headers(outsider["access_token"])

    custom_type_resp = requests.post(
        f"{API_BASE_URL}/references/type-ruche",
        headers=owner_headers,
        json={"libelle": "Type Prive Owner"},
        timeout=10,
    )
    assert custom_type_resp.status_code == 201, custom_type_resp.text
    custom_type_id = custom_type_resp.json()["id"]

    custom_statut_resp = requests.post(
        f"{API_BASE_URL}/references/statut-ruche",
        headers=owner_headers,
        json={"libelle": "Statut Prive Owner"},
        timeout=10,
    )
    assert custom_statut_resp.status_code == 201, custom_statut_resp.text
    custom_statut_id = custom_statut_resp.json()["id"]

    outsider_rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=outsider_headers,
        json={
            "nom": "Rucher Outsider",
            "latitude": 45.95,
            "longitude": 3.95,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert outsider_rucher_resp.status_code == 201, outsider_rucher_resp.text

    outsider_create_ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=outsider_headers,
        json={
            "identifiant_personnalise": "OUT-REF-1",
            "rucher_id": outsider_rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": custom_type_id,
            "ref_statut_ruche_id": custom_statut_id,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert outsider_create_ruche.status_code == 404, outsider_create_ruche.text
    assert outsider_create_ruche.json()["error"]["message"] == "Type de ruche introuvable"


def test_move_multiple_ruches_between_rucher_and_atelier() -> None:
    user = _register_user(_rand_email("move"), prenom="Move")
    headers = _auth_headers(user["access_token"])

    source_rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Source",
            "latitude": 45.91,
            "longitude": 3.91,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert source_rucher_resp.status_code == 201, source_rucher_resp.text
    source_rucher_id = source_rucher_resp.json()["id"]

    target_rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Cible",
            "latitude": 45.92,
            "longitude": 3.92,
            "type_terrain": "montagne",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert target_rucher_resp.status_code == 201, target_rucher_resp.text
    target_rucher_id = target_rucher_resp.json()["id"]

    ruche_ids = []
    for identifiant in ("MOVE-1", "MOVE-2"):
        ruche_resp = requests.post(
            f"{API_BASE_URL}/ruches",
            headers=headers,
            json={
                "identifiant_personnalise": identifiant,
                "rucher_id": source_rucher_id,
                "is_at_atelier": False,
                "ref_type_ruche_id": None,
                "ref_statut_ruche_id": None,
                "reine_annee_marquage": 2026,
                "reine_race": "Buckfast",
                "reine_provenance": "Local",
            },
            timeout=10,
        )
        assert ruche_resp.status_code == 201, ruche_resp.text
        ruche_ids.append(ruche_resp.json()["id"])

    move_to_rucher_resp = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={
            "ruche_ids": ruche_ids,
            "target_rucher_id": target_rucher_id,
            "move_to_atelier": False,
        },
        timeout=10,
    )
    assert move_to_rucher_resp.status_code == 200, move_to_rucher_resp.text
    move_to_rucher_payload = move_to_rucher_resp.json()
    assert move_to_rucher_payload["moved_count"] == 2
    assert move_to_rucher_payload["target_rucher_id"] == target_rucher_id
    assert move_to_rucher_payload["move_to_atelier"] is False

    list_target_resp = requests.get(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        params={"rucher_id": target_rucher_id},
        timeout=10,
    )
    assert list_target_resp.status_code == 200, list_target_resp.text
    list_target_payload = list_target_resp.json()
    assert len([ruche for ruche in list_target_payload if ruche["id"] in ruche_ids]) == 2

    move_to_atelier_resp = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={
            "ruche_ids": ruche_ids,
            "target_rucher_id": None,
            "move_to_atelier": True,
        },
        timeout=10,
    )
    assert move_to_atelier_resp.status_code == 200, move_to_atelier_resp.text
    move_to_atelier_payload = move_to_atelier_resp.json()
    assert move_to_atelier_payload["moved_count"] == 2
    assert move_to_atelier_payload["target_rucher_id"] is None
    assert move_to_atelier_payload["move_to_atelier"] is True

    list_atelier_resp = requests.get(f"{API_BASE_URL}/ruches", headers=headers, params={"atelier_only": True}, timeout=10)
    assert list_atelier_resp.status_code == 200, list_atelier_resp.text
    list_atelier_payload = list_atelier_resp.json()
    assert len([ruche for ruche in list_atelier_payload if ruche["id"] in ruche_ids]) == 2


def test_move_ruches_validation_errors() -> None:
    user = _register_user(_rand_email("moveerr"), prenom="MoveErr")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Move Err",
            "latitude": 46.01,
            "longitude": 4.01,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "MOVE-ERR-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    both_modes_resp = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={
            "ruche_ids": [ruche_id],
            "target_rucher_id": rucher_resp.json()["id"],
            "move_to_atelier": True,
        },
        timeout=10,
    )
    assert both_modes_resp.status_code == 422, both_modes_resp.text
    assert both_modes_resp.json()["error"]["message"] == "Choisir atelier ou rucher, pas les deux"

    missing_target_resp = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={
            "ruche_ids": [ruche_id],
            "target_rucher_id": None,
            "move_to_atelier": False,
        },
        timeout=10,
    )
    assert missing_target_resp.status_code == 422, missing_target_resp.text
    assert missing_target_resp.json()["error"]["message"] == "Rucher cible obligatoire hors atelier"

    unknown_target_resp = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={
            "ruche_ids": [ruche_id],
            "target_rucher_id": "00000000-0000-0000-0000-000000000099",
            "move_to_atelier": False,
        },
        timeout=10,
    )
    assert unknown_target_resp.status_code == 404, unknown_target_resp.text
    assert unknown_target_resp.json()["error"]["message"] == "Rucher cible introuvable"


def test_empty_visite_payload_is_rejected() -> None:
    user = _register_user(_rand_email("visiteempty"), prenom="Visite")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Validation",
            "latitude": 45.7,
            "longitude": 3.7,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "VAL-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text

    empty_visite = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={
            "ruche_id": ruche_resp.json()["id"],
            "visite_rucher_id": None,
            "reine_vue": None,
            "presence_ponte": None,
            "etat_couvain": None,
            "nombre_cadres_couvain": None,
            "reserves_nourriture": None,
            "agressivite": None,
            "note_ruche": None,
            "nombre_cadres_total": None,
            "source_saisie": "manuelle",
            "statut_validation": "valide",
            "action_ids": [],
            "interventions": [],
            "mouvements_cadres": [],
            "mouvements_hausses": [],
        },
        timeout=10,
    )
    assert empty_visite.status_code == 422, empty_visite.text
    payload = empty_visite.json()
    assert payload["error"]["code"] == "http_422"
    assert "au moins une observation" in payload["error"]["message"]


def test_ia_vocale_analysis_can_save_draft_visit() -> None:
    user = _register_user(_rand_email("ia"), prenom="IA", is_premium=True)
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher IA",
            "latitude": 45.8,
            "longitude": 3.8,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "IA-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text

    analysis = requests.post(
        f"{API_BASE_URL}/ia-vocale/analyser-visite",
        headers=headers,
        json={
            "ruche_id": ruche_resp.json()["id"],
            "transcription": "reine vue, ponte presente, etat couvain normal, couvain 4 cadres, reserves correct, agressivite 2, note 4, 2 hausses",
            "audio_reference": "audio/test-001.wav",
            "save_as_draft": True,
        },
        timeout=10,
    )
    assert analysis.status_code == 200, analysis.text
    payload = analysis.json()
    assert payload["audio_reference"] == "audio/test-001.wav"
    assert payload["statut_validation"] == "valide"
    assert payload["confidence"] >= 0.8
    assert payload["saved_visite"] is not None
    assert payload["saved_visite"]["source_saisie"] == "ia_vocale"

    review = requests.get(
        f"{API_BASE_URL}/visites",
        headers=headers,
        params={"ruche_id": ruche_resp.json()["id"], "source_saisie": "ia_vocale", "statut_validation": "valide"},
        timeout=10,
    )
    assert review.status_code == 200, review.text
    review_payload = review.json()
    assert review_payload
    assert review_payload[0]["source_saisie"] == "ia_vocale"
    assert review_payload[0]["statut_validation"] == "valide"


def test_ia_vocale_audio_transcription_endpoint_for_premium() -> None:
    premium_user = _register_user(_rand_email("iatrans"), prenom="IATrans", is_premium=True)
    premium_headers = _auth_headers(premium_user["access_token"])

    transcribe_resp = requests.post(
        f"{API_BASE_URL}/ia-vocale/transcrire-audio",
        headers=premium_headers,
        files={"audio_file": ("visite.wav", b"RIFF....WAVEfmt ", "audio/wav")},
        timeout=10,
    )
    assert transcribe_resp.status_code == 200, transcribe_resp.text
    transcribe_payload = transcribe_resp.json()
    assert transcribe_payload["audio_reference"].startswith("audio/")
    assert transcribe_payload["transcription"]
    assert transcribe_payload["detected_language"] == "fr"
    assert transcribe_payload["duration_seconds_estimate"] >= 1.0

    free_user = _register_user(_rand_email("iatransfree"), prenom="IATransFree", is_premium=False)
    free_headers = _auth_headers(free_user["access_token"])
    forbidden = requests.post(
        f"{API_BASE_URL}/ia-vocale/transcrire-audio",
        headers=free_headers,
        files={"audio_file": ("visite.wav", b"RIFF....WAVEfmt ", "audio/wav")},
        timeout=10,
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["error"]["message"] == "Fonction reservee aux comptes premium"


def test_premium_flag_blocks_ia_vocale_for_standard_accounts() -> None:
    user = _register_user(_rand_email("premium"), prenom="Premium")
    headers = _auth_headers(user["access_token"])

    forbidden = requests.post(
        f"{API_BASE_URL}/ia-vocale/analyser-visite",
        headers=headers,
        json={
            "ruche_id": "00000000-0000-0000-0000-000000000001",
            "transcription": "reine vue, ponte presente, etat couvain normal, couvain 4 cadres, reserves correct, agressivite 2, note 4",
            "save_as_draft": False,
        },
        timeout=10,
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["error"]["message"] == "Fonction reservee aux comptes premium"


def test_ia_vocale_draft_review_endpoint_for_premium() -> None:
    premium_user = _register_user(_rand_email("iadraft"), prenom="IADraft", is_premium=True)
    premium_headers = _auth_headers(premium_user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=premium_headers,
        json={
            "nom": "Rucher IA Draft",
            "latitude": 46.51,
            "longitude": 4.51,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=premium_headers,
        json={
            "identifiant_personnalise": "IA-DRAFT-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    analyse_resp = requests.post(
        f"{API_BASE_URL}/ia-vocale/analyser-visite",
        headers=premium_headers,
        json={
            "ruche_id": ruche_id,
            "transcription": "reine vue",
            "audio_reference": "audio/draft-001.wav",
            "save_as_draft": True,
        },
        timeout=10,
    )
    assert analyse_resp.status_code == 200, analyse_resp.text
    analyse_payload = analyse_resp.json()
    assert analyse_payload["statut_validation"] == "brouillon"
    assert analyse_payload["saved_visite"] is not None
    saved_visite_id = analyse_payload["saved_visite"]["id"]

    review_resp = requests.get(
        f"{API_BASE_URL}/ia-vocale/brouillons",
        headers=premium_headers,
        params={"ruche_id": ruche_id},
        timeout=10,
    )
    assert review_resp.status_code == 200, review_resp.text
    review_payload = review_resp.json()
    assert any(item["id"] == saved_visite_id and item["statut_validation"] == "brouillon" for item in review_payload)

    free_user = _register_user(_rand_email("iadraftfree"), prenom="IADraftFree", is_premium=False)
    free_headers = _auth_headers(free_user["access_token"])
    forbidden_review = requests.get(f"{API_BASE_URL}/ia-vocale/brouillons", headers=free_headers, timeout=10)
    assert forbidden_review.status_code == 403, forbidden_review.text
    assert forbidden_review.json()["error"]["message"] == "Fonction reservee aux comptes premium"


def test_cadre_age_stats_and_alerts() -> None:
    user = _register_user(_rand_email("cadres"), prenom="Cadres")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Cadres",
            "latitude": 45.9,
            "longitude": 3.9,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "CAD-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text

    visite_payload = {
        "ruche_id": ruche_resp.json()["id"],
        "visite_rucher_id": None,
        "reine_vue": True,
        "presence_ponte": True,
        "etat_couvain": "normal",
        "nombre_cadres_couvain": 4,
        "reserves_nourriture": "correct",
        "agressivite": 2,
        "note_ruche": 4,
        "nombre_cadres_total": 10,
        "source_saisie": "manuelle",
        "statut_validation": "valide",
        "action_ids": [],
        "interventions": [],
        "mouvements_cadres": [
            {"ref_action_cadre_id": None, "quantite": 2, "annee_cire": 2021},
            {"ref_action_cadre_id": None, "quantite": 1, "annee_cire": 2024},
        ],
        "mouvements_hausses": [],
    }

    refs = requests.get(f"{API_BASE_URL}/references/action-cadre", headers=headers, timeout=10)
    assert refs.status_code == 200, refs.text
    action_cadre = refs.json()[0]
    visite_payload["mouvements_cadres"][0]["ref_action_cadre_id"] = action_cadre["id"]
    visite_payload["mouvements_cadres"][1]["ref_action_cadre_id"] = action_cadre["id"]

    visite_resp = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=visite_payload, timeout=10)
    assert visite_resp.status_code == 201, visite_resp.text

    stats_resp = requests.get(f"{API_BASE_URL}/cadres/stats/par-ruche", headers=headers, timeout=10)
    assert stats_resp.status_code == 200, stats_resp.text
    stats_payload = stats_resp.json()
    assert stats_payload
    ruche_stats = next(item for item in stats_payload if item["ruche_id"] == ruche_resp.json()["id"])
    assert ruche_stats["total_cadres_declares"] == 3
    assert ruche_stats["total_cadres_avec_annee_cire"] == 3
    assert ruche_stats["cadres_plus_de_3_ans"] == 2
    assert ruche_stats["alerte_renouvellement"] is True

    alerts_resp = requests.get(f"{API_BASE_URL}/cadres/alertes/renouvellement", headers=headers, timeout=10)
    assert alerts_resp.status_code == 200, alerts_resp.text
    alerts_payload = alerts_resp.json()
    assert any(item["ruche_id"] == ruche_resp.json()["id"] for item in alerts_payload)


def test_recolte_stats_and_stock_synthetique() -> None:
    user = _register_user(_rand_email("stats"), prenom="Stats")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Stats",
            "latitude": 45.5,
            "longitude": 3.5,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text
    rucher_id = rucher_resp.json()["id"]

    ruche_payload_common = {
        "is_at_atelier": False,
        "rucher_id": rucher_id,
        "ref_type_ruche_id": None,
        "ref_statut_ruche_id": None,
        "reine_annee_marquage": 2026,
        "reine_race": "Buckfast",
        "reine_provenance": "Elevage local",
    }

    ruche1_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={**ruche_payload_common, "identifiant_personnalise": "IT-R1"},
        timeout=10,
    )
    assert ruche1_resp.status_code == 201, ruche1_resp.text
    ruche1_id = ruche1_resp.json()["id"]

    ruche2_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={**ruche_payload_common, "identifiant_personnalise": "IT-R2"},
        timeout=10,
    )
    assert ruche2_resp.status_code == 201, ruche2_resp.text
    ruche2_id = ruche2_resp.json()["id"]

    visite_payload_common = {
        "visite_rucher_id": None,
        "reine_vue": True,
        "presence_ponte": True,
        "etat_couvain": "normal",
        "nombre_cadres_couvain": 4,
        "reserves_nourriture": "correct",
        "agressivite": 2,
        "note_ruche": 4,
        "nombre_cadres_total": 10,
        "source_saisie": "manuelle",
        "statut_validation": "valide",
        "action_ids": [],
        "interventions": [],
        "mouvements_cadres": [],
    }

    visite1_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={**visite_payload_common, "ruche_id": ruche1_id, "mouvements_hausses": [{"quantite_delta": 2, "note": "Pose 2"}]},
        timeout=10,
    )
    assert visite1_resp.status_code == 201, visite1_resp.text
    visite1_id = visite1_resp.json()["id"]

    visite2_resp = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={**visite_payload_common, "ruche_id": ruche2_id, "mouvements_hausses": [{"quantite_delta": 1, "note": "Pose 1"}]},
        timeout=10,
    )
    assert visite2_resp.status_code == 201, visite2_resp.text
    visite2_id = visite2_resp.json()["id"]

    recolte1 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche1_id, "visite_ruche_id": visite1_id, "poids_miel_kg": 15.0},
        timeout=10,
    )
    assert recolte1.status_code == 201, recolte1.text

    recolte2 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche2_id, "visite_ruche_id": visite2_id, "poids_miel_kg": 22.0},
        timeout=10,
    )
    assert recolte2.status_code == 201, recolte2.text

    rolling = requests.get(
        f"{API_BASE_URL}/recoltes/stats/periode-glissante",
        headers=headers,
        params={"days": 365},
        timeout=10,
    )
    assert rolling.status_code == 200, rolling.text
    rolling_payload = rolling.json()
    assert rolling_payload["total_recoltes"] == 2
    assert rolling_payload["poids_total_kg"] == pytest.approx(37.0)

    season = requests.get(f"{API_BASE_URL}/recoltes/stats/par-saison", headers=headers, timeout=10)
    assert season.status_code == 200, season.text
    season_payload = season.json()
    assert len(season_payload) >= 1
    assert season_payload[0]["season_start_month"] == 3

    types_resp = requests.get(f"{API_BASE_URL}/references/type-materiel", headers=headers, timeout=10)
    assert types_resp.status_code == 200, types_resp.text
    types_payload = types_resp.json()
    hausse_type = next((item for item in types_payload if item["libelle"] == "Hausse"), None)
    assert hausse_type is not None

    materiel_resp = requests.post(
        f"{API_BASE_URL}/materiel-atelier",
        headers=headers,
        json={
            "ref_type_materiel_id": hausse_type["id"],
            "modele": "Dadant hausse",
            "quantite_atelier": 6,
            "quantite_en_service": 1,
        },
        timeout=10,
    )
    assert materiel_resp.status_code == 201, materiel_resp.text

    stock_resp = requests.get(
        f"{API_BASE_URL}/materiel-atelier/stats/stock-synthetique-par-type",
        headers=headers,
        timeout=10,
    )
    assert stock_resp.status_code == 200, stock_resp.text
    stock_payload = stock_resp.json()

    hausse_stock = next((item for item in stock_payload if item["libelle_type_materiel"] == "Hausse"), None)
    assert hausse_stock is not None
    assert hausse_stock["quantite_atelier_totale"] == 6
    assert hausse_stock["quantite_en_service_manuelle_totale"] == 1
    assert hausse_stock["quantite_en_service_calculee"] == 3
    assert hausse_stock["quantite_en_service_totale"] == 4
    assert hausse_stock["quantite_stock_totale"] == 10


def test_materiel_atelier_crud_and_ownership() -> None:
    user_a = _register_user(_rand_email("matsA"), prenom="MatA")
    user_b = _register_user(_rand_email("matsB"), prenom="MatB")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    types_resp = requests.get(f"{API_BASE_URL}/references/type-materiel", headers=headers_a, timeout=10)
    assert types_resp.status_code == 200, types_resp.text
    hausse_type = next((item for item in types_resp.json() if item["libelle"] == "Hausse"), None)
    assert hausse_type is not None

    create_resp = requests.post(
        f"{API_BASE_URL}/materiel-atelier",
        headers=headers_a,
        json={
            "ref_type_materiel_id": hausse_type["id"],
            "modele": "Dadant hausse 2026",
            "quantite_atelier": 4,
            "quantite_en_service": 2,
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    materiel_id = create_resp.json()["id"]

    list_resp = requests.get(f"{API_BASE_URL}/materiel-atelier", headers=headers_a, timeout=10)
    assert list_resp.status_code == 200, list_resp.text
    assert any(item["id"] == materiel_id for item in list_resp.json())

    get_resp = requests.get(f"{API_BASE_URL}/materiel-atelier/{materiel_id}", headers=headers_a, timeout=10)
    assert get_resp.status_code == 200, get_resp.text
    get_payload = get_resp.json()
    assert get_payload["modele"] == "Dadant hausse 2026"
    assert get_payload["quantite_atelier"] == 4

    update_resp = requests.put(
        f"{API_BASE_URL}/materiel-atelier/{materiel_id}",
        headers=headers_a,
        json={
            "ref_type_materiel_id": hausse_type["id"],
            "modele": "Dadant hausse 2026 MAJ",
            "quantite_atelier": 7,
            "quantite_en_service": 1,
        },
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    update_payload = update_resp.json()
    assert update_payload["modele"] == "Dadant hausse 2026 MAJ"
    assert update_payload["quantite_atelier"] == 7
    assert update_payload["quantite_en_service_manuelle"] == 2

    forbidden_get = requests.get(f"{API_BASE_URL}/materiel-atelier/{materiel_id}", headers=headers_b, timeout=10)
    assert forbidden_get.status_code == 404, forbidden_get.text

    delete_resp = requests.delete(f"{API_BASE_URL}/materiel-atelier/{materiel_id}", headers=headers_a, timeout=10)
    assert delete_resp.status_code == 204, delete_resp.text


def test_material_stock_includes_computed_hive_formats_without_manual_rows() -> None:
    user = _register_user(_rand_email("stockfmt"), prenom="StockFmt")
    headers = _auth_headers(user["access_token"])

    types_resp = requests.get(f"{API_BASE_URL}/references/type-materiel", headers=headers, timeout=10)
    assert types_resp.status_code == 200, types_resp.text
    corps_type = next((item for item in types_resp.json() if item["libelle"] == "Corps"), None)
    assert corps_type is not None

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={"nom": "Rucher Stock Format", "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"},
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "FMT-DADANT-01",
            "rucher_id": rucher_resp.json()["id"],
            "format_ruche": "dadant",
            "has_corps": True,
            "is_at_atelier": False,
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text

    stock_resp = requests.get(
        f"{API_BASE_URL}/materiel-atelier/stats/stock-synthetique-par-type",
        headers=headers,
        timeout=10,
    )
    assert stock_resp.status_code == 200, stock_resp.text
    corps_dadant = next(
        (
            item
            for item in stock_resp.json()
            if item["ref_type_materiel_id"] == corps_type["id"] and item["format_materiel"] == "dadant"
        ),
        None,
    )
    assert corps_dadant is not None
    assert corps_dadant["libelle_type_materiel"] == "Corps"
    assert corps_dadant["quantite_atelier_totale"] == 0
    assert corps_dadant["quantite_en_service_calculee"] == 1
    assert corps_dadant["quantite_en_service_totale"] == 1


def test_recolte_crud_and_ownership() -> None:
    user_a = _register_user(_rand_email("reca"), prenom="RecA")
    user_b = _register_user(_rand_email("recb"), prenom="RecB")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers_a,
        json={
            "nom": "Rucher Recolte CRUD",
            "latitude": 46.11,
            "longitude": 4.11,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers_a,
        json={
            "identifiant_personnalise": "REC-CRUD-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    create_resp = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        json={
            "ruche_id": ruche_id,
            "visite_ruche_id": None,
            "poids_miel_kg": 12.5,
        },
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    recolte_id = create_resp.json()["id"]

    get_resp = requests.get(f"{API_BASE_URL}/recoltes/{recolte_id}", headers=headers_a, timeout=10)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["poids_miel_kg"] == pytest.approx(12.5)

    update_resp = requests.put(
        f"{API_BASE_URL}/recoltes/{recolte_id}",
        headers=headers_a,
        json={
            "ruche_id": ruche_id,
            "visite_ruche_id": None,
            "poids_miel_kg": 16.75,
        },
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["poids_miel_kg"] == pytest.approx(16.75)

    forbidden_get = requests.get(f"{API_BASE_URL}/recoltes/{recolte_id}", headers=headers_b, timeout=10)
    assert forbidden_get.status_code == 404, forbidden_get.text

    delete_resp = requests.delete(f"{API_BASE_URL}/recoltes/{recolte_id}", headers=headers_a, timeout=10)
    assert delete_resp.status_code == 204, delete_resp.text

    missing_resp = requests.get(f"{API_BASE_URL}/recoltes/{recolte_id}", headers=headers_a, timeout=10)
    assert missing_resp.status_code == 404, missing_resp.text


def test_recolte_stats_by_ruche_rucher_and_year() -> None:
    user = _register_user(_rand_email("statsd"), prenom="StatsD")
    headers = _auth_headers(user["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={
            "nom": "Rucher Stats Detail",
            "latitude": 46.21,
            "longitude": 4.21,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text
    rucher_id = rucher_resp.json()["id"]

    ruche_a_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "STATS-A",
            "rucher_id": rucher_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_a_resp.status_code == 201, ruche_a_resp.text
    ruche_a_id = ruche_a_resp.json()["id"]

    ruche_b_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={
            "identifiant_personnalise": "STATS-B",
            "rucher_id": rucher_id,
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_b_resp.status_code == 201, ruche_b_resp.text
    ruche_b_id = ruche_b_resp.json()["id"]

    recolte_a1 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche_a_id, "visite_ruche_id": None, "poids_miel_kg": 10.0},
        timeout=10,
    )
    assert recolte_a1.status_code == 201, recolte_a1.text

    recolte_a2 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche_a_id, "visite_ruche_id": None, "poids_miel_kg": 14.0},
        timeout=10,
    )
    assert recolte_a2.status_code == 201, recolte_a2.text

    recolte_b1 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche_b_id, "visite_ruche_id": None, "poids_miel_kg": 20.0},
        timeout=10,
    )
    assert recolte_b1.status_code == 201, recolte_b1.text

    by_ruche_resp = requests.get(f"{API_BASE_URL}/recoltes/stats/par-ruche", headers=headers, timeout=10)
    assert by_ruche_resp.status_code == 200, by_ruche_resp.text
    by_ruche_payload = by_ruche_resp.json()

    stats_a = next(item for item in by_ruche_payload if item["ruche_id"] == ruche_a_id)
    assert stats_a["total_recoltes"] == 2
    assert stats_a["poids_total_kg"] == pytest.approx(24.0)

    stats_b = next(item for item in by_ruche_payload if item["ruche_id"] == ruche_b_id)
    assert stats_b["total_recoltes"] == 1
    assert stats_b["poids_total_kg"] == pytest.approx(20.0)

    by_rucher_resp = requests.get(f"{API_BASE_URL}/recoltes/stats/par-rucher", headers=headers, timeout=10)
    assert by_rucher_resp.status_code == 200, by_rucher_resp.text
    by_rucher_payload = by_rucher_resp.json()
    rucher_stats = next(item for item in by_rucher_payload if item["rucher_id"] == rucher_id)
    assert rucher_stats["total_recoltes"] == 3
    assert rucher_stats["poids_total_kg"] == pytest.approx(44.0)

    by_year_resp = requests.get(f"{API_BASE_URL}/recoltes/stats/par-annee", headers=headers, timeout=10)
    assert by_year_resp.status_code == 200, by_year_resp.text
    by_year_payload = by_year_resp.json()
    assert by_year_payload
    current_year = datetime.now().year
    year_stats = next(item for item in by_year_payload if item["annee"] == current_year)
    assert year_stats["total_recoltes"] >= 3
    assert year_stats["poids_total_kg"] >= 44.0


def test_recolte_stats_validation_errors() -> None:
    user = _register_user(_rand_email("statsv"), prenom="StatsV")
    headers = _auth_headers(user["access_token"])

    rolling_invalid = requests.get(
        f"{API_BASE_URL}/recoltes/stats/periode-glissante",
        headers=headers,
        params={"days": 0},
        timeout=10,
    )
    assert rolling_invalid.status_code == 422, rolling_invalid.text
    assert rolling_invalid.json()["error"]["message"] == "Le nombre de jours doit etre positif"

    season_invalid = requests.get(
        f"{API_BASE_URL}/recoltes/stats/par-saison",
        headers=headers,
        params={"season_start_month": 13},
        timeout=10,
    )
    assert season_invalid.status_code == 422, season_invalid.text
    assert season_invalid.json()["error"]["message"] == "Le mois de debut de saison doit etre compris entre 1 et 12"


def test_references_update_delete_and_system_protection() -> None:
    user = _register_user(_rand_email("refcrud"), prenom="RefCrud")
    headers = _auth_headers(user["access_token"])

    create_resp = requests.post(
        f"{API_BASE_URL}/references/type-materiel",
        headers=headers,
        json={"libelle": "Nourrisseur perso"},
        timeout=10,
    )
    assert create_resp.status_code == 201, create_resp.text
    custom_option = create_resp.json()

    update_resp = requests.put(
        f"{API_BASE_URL}/references/type-materiel/{custom_option['id']}",
        headers=headers,
        json={"libelle": "Nourrisseur perso MAJ"},
        timeout=10,
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["libelle"] == "Nourrisseur perso MAJ"

    delete_resp = requests.delete(
        f"{API_BASE_URL}/references/type-materiel/{custom_option['id']}",
        headers=headers,
        timeout=10,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    list_resp = requests.get(f"{API_BASE_URL}/references/type-materiel", headers=headers, timeout=10)
    assert list_resp.status_code == 200, list_resp.text
    assert not any(item["id"] == custom_option["id"] for item in list_resp.json())

    system_option = next((item for item in list_resp.json() if item["is_system"]), None)
    assert system_option is not None

    forbidden_update = requests.put(
        f"{API_BASE_URL}/references/type-materiel/{system_option['id']}",
        headers=headers,
        json={"libelle": "Interdit"},
        timeout=10,
    )
    assert forbidden_update.status_code == 403, forbidden_update.text
    assert forbidden_update.json()["error"]["message"] == "Une option systeme ne peut pas etre modifiee"

    forbidden_delete = requests.delete(
        f"{API_BASE_URL}/references/type-materiel/{system_option['id']}",
        headers=headers,
        timeout=10,
    )
    assert forbidden_delete.status_code == 403, forbidden_delete.text
    assert forbidden_delete.json()["error"]["message"] == "Une option systeme ne peut pas etre supprimee"


def test_recolte_list_filters_and_ruche_ownership() -> None:
    user_a = _register_user(_rand_email("reclfA"), prenom="ReclFA")
    user_b = _register_user(_rand_email("reclfB"), prenom="ReclFB")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    rucher_resp = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers_a,
        json={
            "nom": "Rucher Recolte Filtres",
            "latitude": 46.41,
            "longitude": 4.41,
            "type_terrain": "plaine",
            "statut_activite": "actif",
            "statut_peuplement": "peuple",
        },
        timeout=10,
    )
    assert rucher_resp.status_code == 201, rucher_resp.text

    ruche_resp = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers_a,
        json={
            "identifiant_personnalise": "RECF-1",
            "rucher_id": rucher_resp.json()["id"],
            "is_at_atelier": False,
            "ref_type_ruche_id": None,
            "ref_statut_ruche_id": None,
            "reine_annee_marquage": 2026,
            "reine_race": "Buckfast",
            "reine_provenance": "Local",
        },
        timeout=10,
    )
    assert ruche_resp.status_code == 201, ruche_resp.text
    ruche_id = ruche_resp.json()["id"]

    rec1 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        json={"ruche_id": ruche_id, "visite_ruche_id": None, "poids_miel_kg": 9.0},
        timeout=10,
    )
    assert rec1.status_code == 201, rec1.text

    rec2 = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        json={"ruche_id": ruche_id, "visite_ruche_id": None, "poids_miel_kg": 11.0},
        timeout=10,
    )
    assert rec2.status_code == 201, rec2.text

    by_ruche_resp = requests.get(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        params={"ruche_id": ruche_id},
        timeout=10,
    )
    assert by_ruche_resp.status_code == 200, by_ruche_resp.text
    by_ruche_payload = by_ruche_resp.json()
    assert len(by_ruche_payload) == 2

    by_year_resp = requests.get(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        params={"year": datetime.now().year},
        timeout=10,
    )
    assert by_year_resp.status_code == 200, by_year_resp.text
    by_year_payload = by_year_resp.json()
    assert len(by_year_payload) >= 2

    today_iso = datetime.now().date().isoformat()
    by_date_resp = requests.get(
        f"{API_BASE_URL}/recoltes",
        headers=headers_a,
        params={"start_date": today_iso, "end_date": today_iso},
        timeout=10,
    )
    assert by_date_resp.status_code == 200, by_date_resp.text
    by_date_payload = by_date_resp.json()
    assert len(by_date_payload) >= 2

    forbidden_ruche_filter = requests.get(
        f"{API_BASE_URL}/recoltes",
        headers=headers_b,
        params={"ruche_id": ruche_id},
        timeout=10,
    )
    assert forbidden_ruche_filter.status_code == 404, forbidden_ruche_filter.text


def test_reference_conflict_and_unknown_type_errors() -> None:
    user = _register_user(_rand_email("referr"), prenom="RefErr")
    headers = _auth_headers(user["access_token"])

    first_create = requests.post(
        f"{API_BASE_URL}/references/type-ruche",
        headers=headers,
        json={"libelle": "Test conflit ref"},
        timeout=10,
    )
    assert first_create.status_code == 201, first_create.text

    duplicate_create = requests.post(
        f"{API_BASE_URL}/references/type-ruche",
        headers=headers,
        json={"libelle": "Test conflit ref"},
        timeout=10,
    )
    assert duplicate_create.status_code == 409, duplicate_create.text
    assert duplicate_create.json()["error"]["message"] == "Cette option existe deja"

    unknown_type = requests.get(
        f"{API_BASE_URL}/references/type-inexistant",
        headers=headers,
        timeout=10,
    )
    assert unknown_type.status_code == 404, unknown_type.text
    assert unknown_type.json()["error"]["message"] == "Type de dictionnaire introuvable"


def test_queen_lifecycle_and_automatic_visit_link() -> None:
    user = _register_user(_rand_email("queen"), prenom="Queen")
    headers = _auth_headers(user["access_token"])
    rucher = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={"nom": "Rucher Reines", "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"},
        timeout=10,
    ).json()
    ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "QUEEN-1", "rucher_id": rucher["id"], "is_at_atelier": False},
        timeout=10,
    ).json()
    first = requests.post(
        f"{API_BASE_URL}/ruches/{ruche['id']}/reines",
        headers=headers,
        json={"date_mise_en_place": "2026-01-01T00:00:00Z", "origine": "apport_reine_fecondee", "race": "Buckfast"},
        timeout=10,
    )
    assert first.status_code == 201, first.text
    second = requests.post(
        f"{API_BASE_URL}/ruches/{ruche['id']}/reines",
        headers=headers,
        json={"date_mise_en_place": "2026-06-01T00:00:00Z", "origine": "remerage", "race": "Noire"},
        timeout=10,
    )
    assert second.status_code == 201, second.text
    history = requests.get(f"{API_BASE_URL}/ruches/{ruche['id']}/reines", headers=headers, timeout=10).json()
    assert len(history) == 2
    assert {item["statut"] for item in history} == {"active", "terminee"}

    visit = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": ruche["id"], "reine_vue": True, "etat_couvain": "normal", "nombre_cadres_couvain": 5, "nombre_cadres_total": 10, "note_ruche": 4, "source_saisie": "manuelle", "statut_validation": "valide", "action_ids": [], "interventions": [], "mouvements_cadres": [], "mouvements_hausses": []},
        timeout=10,
    )
    assert visit.status_code == 201, visit.text
    assert visit.json()["reine_id"] == second.json()["id"]


def test_advanced_synthesis_reports_brood_frame_ratio_and_scopes() -> None:
    user = _register_user(_rand_email("advanced"), prenom="Advanced")
    headers = _auth_headers(user["access_token"])
    rucher = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={"nom": "Rucher Stats", "type_terrain": "bocage", "statut_activite": "actif", "statut_peuplement": "peuple"},
        timeout=10,
    ).json()
    ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "STATS-1", "rucher_id": rucher["id"], "is_at_atelier": False},
        timeout=10,
    ).json()
    requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": ruche["id"], "reine_vue": True, "etat_couvain": "excellent", "nombre_cadres_couvain": 5, "nombre_cadres_total": 10, "note_ruche": 4, "source_saisie": "manuelle", "statut_validation": "valide", "action_ids": [], "interventions": [], "mouvements_cadres": [], "mouvements_hausses": []},
        timeout=10,
    )
    response = requests.get(f"{API_BASE_URL}/visites/synthese/avancee", headers=headers, params={"window_days": 30, "ruche_id": ruche["id"]}, timeout=10)
    assert response.status_code == 200, response.text
    current = response.json()["current"]
    assert current["taux_couvain"] == 1.0
    assert current["taux_cadres_couvain"] == 0.5
    assert current["cadres_total_moyens"] == 10.0


def test_ai_draft_rejection_removes_draft() -> None:
    user = _register_user(_rand_email("reject"), prenom="Reject", is_premium=True)
    headers = _auth_headers(user["access_token"])
    rucher = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={"nom": "Rucher Rejet IA", "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"},
        timeout=10,
    ).json()
    ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "REJECT-1", "rucher_id": rucher["id"], "is_at_atelier": False},
        timeout=10,
    ).json()
    analyse = requests.post(
        f"{API_BASE_URL}/ia-vocale/analyser-visite",
        headers=headers,
        json={"ruche_id": ruche["id"], "transcription": "reine vue, couvain normal, note 2", "save_as_draft": True},
        timeout=10,
    )
    assert analyse.status_code == 200, analyse.text
    draft_id = analyse.json()["saved_visite"]["id"]
    rejected = requests.delete(f"{API_BASE_URL}/ia-vocale/brouillons/{draft_id}", headers=headers, timeout=10)
    assert rejected.status_code == 204, rejected.text
    drafts = requests.get(f"{API_BASE_URL}/ia-vocale/brouillons", headers=headers, timeout=10)
    assert drafts.status_code == 200, drafts.text
    assert not any(item["id"] == draft_id for item in drafts.json())


def test_visit_creation_is_idempotent_with_repeated_key() -> None:
    user = _register_user(_rand_email("idem"), prenom="Idem")
    headers = _auth_headers(user["access_token"])
    rucher = requests.post(f"{API_BASE_URL}/ruchers", headers=headers, json={"nom": "Rucher Idem", "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"}, timeout=10).json()
    ruche = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "IDEM-1", "rucher_id": rucher["id"], "is_at_atelier": False}, timeout=10).json()
    payload = {"ruche_id": ruche["id"], "note_ruche": 4, "nombre_cadres_couvain": 4, "nombre_cadres_total": 10, "source_saisie": "manuelle", "statut_validation": "valide", "action_ids": [], "interventions": [], "mouvements_cadres": [], "mouvements_hausses": []}
    idem_headers = {**headers, "Idempotency-Key": "idem-test-001"}
    first = requests.post(f"{API_BASE_URL}/visites", headers=idem_headers, json=payload, timeout=10)
    second = requests.post(f"{API_BASE_URL}/visites", headers=idem_headers, json=payload, timeout=10)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]
    visits = requests.get(f"{API_BASE_URL}/visites?ruche_id={ruche['id']}", headers=headers, timeout=10).json()
    assert len(visits) == 1


def test_visit_update_rejects_stale_client_version() -> None:
    user = _register_user(_rand_email("conflict"), prenom="Conflict")
    headers = _auth_headers(user["access_token"])
    rucher = requests.post(f"{API_BASE_URL}/ruchers", headers=headers, json={"nom": "Rucher Conflict", "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"}, timeout=10).json()
    ruche = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "CONFLICT-1", "rucher_id": rucher["id"], "is_at_atelier": False}, timeout=10).json()
    visit = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": ruche["id"], "note_ruche": 3, "source_saisie": "manuelle", "statut_validation": "valide", "action_ids": [], "interventions": [], "mouvements_cadres": [], "mouvements_hausses": []}, timeout=10).json()
    stale = visit["updated_at"]
    updated = requests.patch(f"{API_BASE_URL}/visites/{visit['id']}", headers=headers, json={"note_ruche": 5}, timeout=10)
    assert updated.status_code == 200, updated.text
    conflict = requests.patch(f"{API_BASE_URL}/visites/{visit['id']}", headers={**headers, "X-Client-Base-Updated-At": stale}, json={"note_ruche": 2}, timeout=10)
    assert conflict.status_code == 409, conflict.text


def test_observability_summary_is_scoped_to_authenticated_user() -> None:
    user = _register_user(_rand_email("obs"), prenom="Obs")
    headers = _auth_headers(user["access_token"])
    requests.get(f"{API_BASE_URL}/ruchers", headers=headers, timeout=10)
    summary = requests.get(f"{API_BASE_URL}/events/summary", headers=headers, timeout=10)
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["requests"] >= 1
    assert payload["errors"] >= 0
    assert payload["average_duration_ms"] >= 0
    assert payload["p95_duration_ms"] >= 0


def test_forgot_password_does_not_reveal_whether_account_exists() -> None:
    known_email = _rand_email("forgot")
    _register_user(known_email, prenom="Forgot")

    known = requests.post(
        f"{API_BASE_URL}/auth/forgot-password", json={"email": known_email}, timeout=10
    )
    unknown = requests.post(
        f"{API_BASE_URL}/auth/forgot-password",
        json={"email": _rand_email("nobody")},
        timeout=10,
    )

    assert known.status_code == 200, known.text
    assert unknown.status_code == 200, unknown.text
    assert known.json()["message"] == unknown.json()["message"]
    assert "debug_reset_url" not in unknown.json()


def test_password_reset_changes_password_and_revokes_old_sessions_in_dev() -> None:
    email = _rand_email("reset")
    registered = _register_user(email, prenom="Reset")
    old_headers = _auth_headers(registered["access_token"])

    requested = requests.post(
        f"{API_BASE_URL}/auth/forgot-password", json={"email": email}, timeout=10
    )
    assert requested.status_code == 200, requested.text
    debug_reset_url = requested.json().get("debug_reset_url")
    assert debug_reset_url, requested.text
    token = parse_qs(urlparse(debug_reset_url).query)["token"][0]

    reset = requests.post(
        f"{API_BASE_URL}/auth/reset-password",
        json={"token": token, "password": "nouveaumotdepasse123"},
        timeout=10,
    )
    assert reset.status_code == 200, reset.text

    old_session = requests.get(f"{API_BASE_URL}/auth/me", headers=old_headers, timeout=10)
    assert old_session.status_code == 401, old_session.text

    old_password = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": "motdepasse123"},
        timeout=10,
    )
    assert old_password.status_code == 401, old_password.text

    new_password = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": "nouveaumotdepasse123"},
        timeout=10,
    )
    assert new_password.status_code == 200, new_password.text

    reused = requests.post(
        f"{API_BASE_URL}/auth/reset-password",
        json={"token": token, "password": "autremotdepasse123"},
        timeout=10,
    )
    assert reused.status_code == 400, reused.text


def test_reset_password_rejects_unknown_token() -> None:
    response = requests.post(
        f"{API_BASE_URL}/auth/reset-password",
        json={"token": "x" * 43, "password": "nouveaumotdepasse123"},
        timeout=10,
    )
    assert response.status_code == 400, response.text


def test_reset_password_rejects_short_password() -> None:
    response = requests.post(
        f"{API_BASE_URL}/auth/reset-password",
        json={"token": "x" * 43, "password": "court"},
        timeout=10,
    )
    assert response.status_code == 422, response.text


def test_forgot_password_rejects_malformed_email() -> None:
    response = requests.post(
        f"{API_BASE_URL}/auth/forgot-password", json={"email": "pas-un-email"}, timeout=10
    )
    assert response.status_code == 422, response.text


def _create_rucher_and_hive(headers: dict[str, str], identifiant: str, nom: str = "Rucher L1") -> tuple[str, str]:
    rucher = requests.post(
        f"{API_BASE_URL}/ruchers",
        headers=headers,
        json={"nom": nom, "latitude": 45.9, "longitude": 3.9, "type_terrain": "plaine", "statut_activite": "actif", "statut_peuplement": "peuple"},
        timeout=10,
    )
    assert rucher.status_code == 201, rucher.text
    ruche = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": identifiant, "rucher_id": rucher.json()["id"], "is_at_atelier": False},
        timeout=10,
    )
    assert ruche.status_code == 201, ruche.text
    return rucher.json()["id"], ruche.json()["id"]


def test_delete_rucher_is_refused_while_it_still_holds_hives() -> None:
    user = _register_user(_rand_email("delrucher"), prenom="DelRucher")
    headers = _auth_headers(user["access_token"])
    rucher_id, ruche_id = _create_rucher_and_hive(headers, "DEL-1")

    refused = requests.delete(f"{API_BASE_URL}/ruchers/{rucher_id}", headers=headers, timeout=10)
    assert refused.status_code == 409, refused.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10)
    assert hive.status_code == 200 and hive.json()["rucher_id"] == rucher_id

    moved = requests.post(
        f"{API_BASE_URL}/ruches/move",
        headers=headers,
        json={"ruche_ids": [ruche_id], "target_rucher_id": None, "move_to_atelier": True},
        timeout=10,
    )
    assert moved.status_code == 200, moved.text
    deleted = requests.delete(f"{API_BASE_URL}/ruchers/{rucher_id}", headers=headers, timeout=10)
    assert deleted.status_code == 204, deleted.text


def test_queen_replacement_updates_hive_queen_summary() -> None:
    user = _register_user(_rand_email("queensync"), prenom="QueenSync")
    headers = _auth_headers(user["access_token"])
    _, ruche_id = _create_rucher_and_hive(headers, "R17")

    replaced = requests.post(
        f"{API_BASE_URL}/ruches/{ruche_id}/reines",
        headers=headers,
        json={"date_mise_en_place": "2025-06-01T00:00:00Z", "origine": "remerage", "race": "Buckfast", "provenance": "Elevage local"},
        timeout=10,
    )
    assert replaced.status_code == 201, replaced.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10).json()
    assert hive["reine_race"] == "Buckfast"
    assert hive["reine_provenance"] == "Elevage local"
    assert hive["reine_annee_marquage"] == 2025


def test_cheptel_visit_coverage_ignores_atelier_hives_and_counts_old_queens() -> None:
    user = _register_user(_rand_email("cheptel"), prenom="Cheptel")
    headers = _auth_headers(user["access_token"])
    _, visited_id = _create_rucher_and_hive(headers, "COV-1")
    atelier = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "COV-ATELIER", "rucher_id": None, "is_at_atelier": True},
        timeout=10,
    )
    assert atelier.status_code == 201, atelier.text
    visit = requests.post(
        f"{API_BASE_URL}/visites",
        headers=headers,
        json={"ruche_id": visited_id, "visite_rucher_id": None, "reine_vue": True, "statut_validation": "valide"},
        timeout=10,
    )
    assert visit.status_code == 201, visit.text
    old_queen = requests.post(
        f"{API_BASE_URL}/ruches/{visited_id}/reines",
        headers=headers,
        json={"date_mise_en_place": "2022-05-01T00:00:00Z", "origine": "inconnue"},
        timeout=10,
    )
    assert old_queen.status_code == 201, old_queen.text

    cheptel = requests.get(f"{API_BASE_URL}/statistiques/cheptel", headers=headers, timeout=10)
    assert cheptel.status_code == 200, cheptel.text
    payload = cheptel.json()
    assert payload["ruches_suivies"] == 1
    assert payload["ruches_atelier"] == 1
    assert payload["ruches_visitees_annee"] == 1
    assert payload["ruches_sans_visite_recente"] == 0
    assert payload["reines_plus_2_ans"] == 1


def test_statistics_dashboard_follows_selected_period() -> None:
    user = _register_user(_rand_email("statperiod"), prenom="StatPeriod")
    headers = _auth_headers(user["access_token"])
    _, ruche_id = _create_rucher_and_hive(headers, "PER-1")
    harvest = requests.post(
        f"{API_BASE_URL}/recoltes",
        headers=headers,
        json={"ruche_id": ruche_id, "visite_ruche_id": None, "poids_miel_kg": 15.0},
        timeout=10,
    )
    assert harvest.status_code == 201, harvest.text

    year = datetime.now().year
    current = requests.get(
        f"{API_BASE_URL}/statistiques/tableau-de-bord",
        headers=headers,
        params={"start_date": f"{year}-01-01", "end_date": f"{year}-12-31"},
        timeout=10,
    )
    assert current.status_code == 200, current.text
    assert current.json()["miel_total_kg"] == 15.0
    assert current.json()["start_date"] == f"{year}-01-01"

    last_season = requests.get(
        f"{API_BASE_URL}/statistiques/tableau-de-bord",
        headers=headers,
        params={"start_date": f"{year - 1}-01-01", "end_date": f"{year - 1}-12-31"},
        timeout=10,
    )
    assert last_season.status_code == 200, last_season.text
    assert last_season.json()["miel_total_kg"] == 0
    assert last_season.json()["recoltes_count"] == 0

    inverted = requests.get(
        f"{API_BASE_URL}/statistiques/tableau-de-bord",
        headers=headers,
        params={"start_date": f"{year}-12-31", "end_date": f"{year}-01-01"},
        timeout=10,
    )
    assert inverted.status_code == 422, inverted.text


def test_offline_visit_carries_tags_applied_once_on_replay() -> None:
    user = _register_user(_rand_email("offtags"), prenom="OffTags")
    headers = _auth_headers(user["access_token"])
    _, ruche_id = _create_rucher_and_hive(headers, "OFF-1")
    body = {
        "ruche_id": ruche_id,
        "visite_rucher_id": None,
        "note_ruche": 3,
        "statut_validation": "valide",
        "tags_ajoutes": ["a nourrir", "a nourrir", "quarantaine"],
    }
    sync_headers = {**headers, "Idempotency-Key": f"offtags-{random.randint(100000, 999999)}"}
    first = requests.post(f"{API_BASE_URL}/visites", headers=sync_headers, json=body, timeout=10)
    assert first.status_code == 201, first.text
    replay = requests.post(f"{API_BASE_URL}/visites", headers=sync_headers, json=body, timeout=10)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    tags = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}/tags", headers=headers, timeout=10).json()
    manual = sorted(tag["libelle"] for tag in tags if tag["source"] == "manuel")
    assert manual == ["a nourrir", "quarantaine"]
    visits = requests.get(f"{API_BASE_URL}/visites", headers=headers, params={"ruche_id": ruche_id}, timeout=10).json()
    assert len(visits) == 1


def test_hive_queen_summary_creates_and_updates_active_queen() -> None:
    user = _register_user(_rand_email("queenform"), prenom="QueenForm")
    headers = _auth_headers(user["access_token"])
    rucher_id, _ = _create_rucher_and_hive(headers, "QF-0")
    created = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "QF-1", "rucher_id": rucher_id, "is_at_atelier": False, "reine_race": "Carnica", "reine_annee_marquage": 2024},
        timeout=10,
    )
    assert created.status_code == 201, created.text
    hive = created.json()
    queens = requests.get(f"{API_BASE_URL}/ruches/{hive['id']}/reines", headers=headers, timeout=10).json()
    assert len(queens) == 1 and queens[0]["statut"] == "active"
    # Annee passee sans date precise : 1er juillet, pas 1er janvier.
    assert queens[0]["race"] == "Carnica" and queens[0]["date_mise_en_place"].startswith("2024-07-01")
    assert hive["reine_date_mise_en_place"] == "2024-07-01"

    update = {key: hive[key] for key in ("identifiant_personnalise", "rucher_id", "is_at_atelier", "reine_annee_marquage", "reine_provenance")}
    update["reine_race"] = "Buckfast"
    updated = requests.put(f"{API_BASE_URL}/ruches/{hive['id']}", headers=headers, json=update, timeout=10)
    assert updated.status_code == 200, updated.text
    queens = requests.get(f"{API_BASE_URL}/ruches/{hive['id']}/reines", headers=headers, timeout=10).json()
    assert len(queens) == 1 and queens[0]["race"] == "Buckfast"

    cheptel = requests.get(f"{API_BASE_URL}/statistiques/cheptel", headers=headers, timeout=10).json()
    assert cheptel["reines_actives"] == 1


def test_hive_queen_age_counts_from_placement_day() -> None:
    user = _register_user(_rand_email("queenday"), prenom="QueenDay")
    headers = _auth_headers(user["access_token"])
    rucher_id, _ = _create_rucher_and_hive(headers, "QD-0")
    body = {"identifiant_personnalise": "QD-1", "rucher_id": rucher_id, "is_at_atelier": False, "reine_date_mise_en_place": "2025-05-10"}
    created = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json=body, timeout=10)
    assert created.status_code == 201, created.text
    hive = created.json()
    assert hive["reine_date_mise_en_place"] == "2025-05-10" and hive["reine_annee_marquage"] == 2025
    queens = requests.get(f"{API_BASE_URL}/ruches/{hive['id']}/reines", headers=headers, timeout=10).json()
    assert len(queens) == 1 and queens[0]["date_mise_en_place"].startswith("2025-05-10")

    # Correction du jour J sur la meme reine : pas de nouvelle reine.
    update = {**body, "reine_annee_marquage": 2025, "reine_date_mise_en_place": "2025-06-02"}
    updated = requests.put(f"{API_BASE_URL}/ruches/{hive['id']}", headers=headers, json=update, timeout=10)
    assert updated.status_code == 200, updated.text
    assert updated.json()["reine_date_mise_en_place"] == "2025-06-02"
    queens = requests.get(f"{API_BASE_URL}/ruches/{hive['id']}/reines", headers=headers, timeout=10).json()
    assert len(queens) == 1 and queens[0]["date_mise_en_place"].startswith("2025-06-02")
    listed = requests.get(f"{API_BASE_URL}/ruches", headers=headers, params={"rucher_id": rucher_id}, timeout=10).json()
    assert next(item for item in listed if item["id"] == hive["id"])["reine_date_mise_en_place"] == "2025-06-02"

    # Reine de l'annee en cours sans date : comptee depuis le jour de saisie.
    this_year = datetime.now(timezone.utc).year
    fresh = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "QD-2", "rucher_id": rucher_id, "is_at_atelier": False, "reine_annee_marquage": this_year},
        timeout=10,
    ).json()
    assert fresh["reine_date_mise_en_place"] == datetime.now(timezone.utc).date().isoformat()


def test_latest_visit_frame_total_updates_hive_frame_count() -> None:
    user = _register_user(_rand_email("framecount"), prenom="FrameCount")
    headers = _auth_headers(user["access_token"])
    _, ruche_id = _create_rucher_and_hive(headers, "FC-1")
    body = {"ruche_id": ruche_id, "visite_rucher_id": None, "note_ruche": 4, "nombre_cadres_total": 8, "statut_validation": "valide"}
    created = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=body, timeout=10)
    assert created.status_code == 201, created.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10).json()
    assert hive["nombre_cadres"] == 8

    # Visite plus ancienne synchronisee en retard : la fiche ne bouge pas.
    old = {**body, "nombre_cadres_total": 5, "date_visite": "2025-06-01T10:00:00Z"}
    late = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=old, timeout=10)
    assert late.status_code == 201, late.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10).json()
    assert hive["nombre_cadres"] == 8

    # Correction de la derniere visite : la fiche suit.
    patched = requests.patch(f"{API_BASE_URL}/visites/{created.json()['id']}", headers=headers, json={"nombre_cadres_total": 10}, timeout=10)
    assert patched.status_code == 200, patched.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{ruche_id}", headers=headers, timeout=10).json()
    assert hive["nombre_cadres"] == 10


def test_parallel_offline_sync_with_same_key_creates_one_visit() -> None:
    from concurrent.futures import ThreadPoolExecutor

    user = _register_user(_rand_email("parallel"), prenom="Parallel")
    headers = _auth_headers(user["access_token"])
    _, ruche_id = _create_rucher_and_hive(headers, "PAR-1")
    sync_headers = {**headers, "Idempotency-Key": f"parallel-{random.randint(100000, 999999)}"}
    body = {"ruche_id": ruche_id, "visite_rucher_id": None, "note_ruche": 4, "statut_validation": "valide", "tags_ajoutes": ["a nourrir"]}

    def send(_: int) -> requests.Response:
        return requests.post(f"{API_BASE_URL}/visites", headers=sync_headers, json=body, timeout=15)

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(send, range(4)))
    assert [response.status_code for response in responses] == [201] * 4, [response.text for response in responses]
    assert len({response.json()["id"] for response in responses}) == 1
    visits = requests.get(f"{API_BASE_URL}/visites", headers=headers, params={"ruche_id": ruche_id}, timeout=10).json()
    assert len(visits) == 1


# --- Lot L4 : cycle de vie du materiel ------------------------------------------

def _material_types(headers: dict[str, str]) -> dict[str, str]:
    rows = requests.get(f"{API_BASE_URL}/references/type-materiel", headers=headers, timeout=10).json()
    return {row["libelle"].lower(): row["id"] for row in rows}


def _add_stock(headers: dict[str, str], types: dict[str, str], format_materiel: str, quantities: dict[str, int]) -> None:
    for label, quantity in quantities.items():
        response = requests.post(
            f"{API_BASE_URL}/materiel-atelier",
            headers=headers,
            json={"ref_type_materiel_id": types[label], "format_materiel": format_materiel, "quantite_atelier": quantity, "quantite_en_service": 0},
            timeout=10,
        )
        assert response.status_code == 201, response.text


def _stock(headers: dict[str, str]) -> dict[tuple[str, str | None], dict]:
    rows = requests.get(f"{API_BASE_URL}/materiel-atelier/stats/stock-synthetique-par-type", headers=headers, timeout=10).json()
    return {(row["libelle_type_materiel"].lower(), row["format_materiel"]): row for row in rows}


def _new_beekeeper(prefix: str) -> tuple[dict[str, str], str, dict[str, str]]:
    user = _register_user(_rand_email(prefix), prenom=prefix.capitalize(), is_premium=True)
    headers = _auth_headers(user["access_token"])
    rucher_id, _ = _create_rucher_and_hive(headers, f"{prefix.upper()}-0")
    return headers, rucher_id, _material_types(headers)


def test_hive_created_from_stock_consumes_stock_and_purchase_does_not() -> None:
    headers, rucher_id, types = _new_beekeeper("fromstock")
    _add_stock(headers, types, "dadant", {"corps": 1, "plancher": 1, "toit": 1, "cadre": 10})
    hive = {"rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "dadant", "nombre_cadres": 10}

    created = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={**hive, "identifiant_personnalise": "ST-1", "origine_materiel": "stock", "elements_stock": ["plancher", "corps", "toit", "cadres"]}, timeout=10)
    assert created.status_code == 201, created.text
    stock = _stock(headers)
    assert stock[("corps", "dadant")]["quantite_atelier_totale"] == 0
    assert stock[("corps", "dadant")]["quantite_en_service_calculee"] == 1
    assert stock[("cadre", "dadant")]["quantite_atelier_totale"] == 0
    assert stock[("corps", "dadant")]["quantite_stock_totale"] == 1

    refused = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={**hive, "identifiant_personnalise": "ST-2", "origine_materiel": "stock", "elements_stock": ["corps"]}, timeout=10)
    assert refused.status_code == 409, refused.text
    assert "corps (0/1)" in refused.text
    names = [item["identifiant_personnalise"] for item in requests.get(f"{API_BASE_URL}/ruches", headers=headers, timeout=10).json()]
    assert "ST-2" not in names

    bought = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={**hive, "identifiant_personnalise": "ST-3"}, timeout=10)
    assert bought.status_code == 201, bought.text
    assert _stock(headers)[("corps", "dadant")]["quantite_stock_totale"] == 2


def test_dismantled_hive_returns_elements_and_keeps_history() -> None:
    headers, rucher_id, types = _new_beekeeper("demont")
    created = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "DM-1", "rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "dadant", "nombre_cadres": 9, "has_partition": True, "reine_race": "Buckfast"},
        timeout=10,
    ).json()
    visit = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": created["id"], "visite_rucher_id": None, "note_ruche": 2, "statut_validation": "valide"}, timeout=10)
    assert visit.status_code == 201, visit.text
    assert _stock(headers)[("partition", "dadant")]["quantite_en_service_calculee"] == 1

    dismantled = requests.post(f"{API_BASE_URL}/ruches/demontage", headers=headers, json={"ruche_ids": [created["id"]]}, timeout=10)
    assert dismantled.status_code == 200, dismantled.text
    stock = _stock(headers)
    assert stock[("corps", "dadant")]["quantite_atelier_totale"] == 1
    assert stock[("cadre", "dadant")]["quantite_atelier_totale"] == 9
    assert stock[("partition", "dadant")]["quantite_atelier_totale"] == 1
    assert stock[("corps", "dadant")]["quantite_en_service_calculee"] == 0

    names = [item["identifiant_personnalise"] for item in requests.get(f"{API_BASE_URL}/ruches", headers=headers, timeout=10).json()]
    assert "DM-1" not in names
    history = requests.get(f"{API_BASE_URL}/visites", headers=headers, params={"ruche_id": created["id"]}, timeout=10).json()
    assert len(history) == 1
    queens = requests.get(f"{API_BASE_URL}/ruches/{created['id']}/reines", headers=headers, timeout=10).json()
    assert all(queen["statut"] == "terminee" for queen in queens)
    late_visit = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": created["id"], "visite_rucher_id": None, "note_ruche": 3, "statut_validation": "valide"}, timeout=10)
    assert late_visit.status_code == 409, late_visit.text
    reused = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "DM-1", "rucher_id": rucher_id, "is_at_atelier": False}, timeout=10)
    assert reused.status_code == 201, reused.text


def test_hive_stored_at_atelier_keeps_its_material_in_stock_total() -> None:
    headers, _, _ = _new_beekeeper("stored")
    stored = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "PREP-1", "rucher_id": None, "is_at_atelier": True, "format_ruche": "ruchette", "nombre_cadres": 6}, timeout=10)
    assert stored.status_code == 201, stored.text
    stock = _stock(headers)
    assert stock[("corps", "ruchette")]["quantite_ruches_atelier_calculee"] == 1
    # Cadres d une ruchette Dadant : ranges et comptes au format Dadant.
    assert ("cadre", "ruchette") not in stock
    assert stock[("cadre", "dadant")]["quantite_ruches_atelier_calculee"] == 6
    assert stock[("corps", "ruchette")]["quantite_stock_totale"] == 1


def test_transvasement_moves_colony_to_new_container() -> None:
    headers, rucher_id, types = _new_beekeeper("transv")
    _add_stock(headers, types, "dadant", {"corps": 1, "plancher": 1, "toit": 1, "cadre": 4})
    colony = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "RT-1", "rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "ruchette", "nombre_cadres": 6, "reine_race": "Carnica"},
        timeout=10,
    ).json()
    visit = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": colony["id"], "visite_rucher_id": None, "note_ruche": 4, "statut_validation": "valide"}, timeout=10)
    assert visit.status_code == 201

    moved = requests.post(
        f"{API_BASE_URL}/ruches/{colony['id']}/transvasements",
        headers=headers,
        json={"format_apres": "dadant", "provenance": "stock", "elements": ["plancher", "corps", "toit"], "cadres_transferes": 6, "cadres_ajoutes": 4, "annee_cire": 2026, "nouvel_identifiant": "RT-1D"},
        timeout=10,
    )
    assert moved.status_code == 201, moved.text
    assert moved.json()["tag_suggestions"] == ["production"]
    hive = requests.get(f"{API_BASE_URL}/ruches/{colony['id']}", headers=headers, timeout=10).json()
    assert hive["format_ruche"] == "dadant" and hive["nombre_cadres"] == 10 and hive["identifiant_personnalise"] == "RT-1D"
    assert hive["reine_race"] == "Carnica"
    stock = _stock(headers)
    assert stock[("corps", "ruchette")]["quantite_atelier_totale"] == 1
    assert stock[("corps", "dadant")]["quantite_atelier_totale"] == 0
    assert stock[("cadre", "dadant")]["quantite_atelier_totale"] == 0
    assert stock[("corps", "dadant")]["quantite_en_service_calculee"] == 1
    assert len(requests.get(f"{API_BASE_URL}/visites", headers=headers, params={"ruche_id": colony["id"]}, timeout=10).json()) == 1
    assert len(requests.get(f"{API_BASE_URL}/ruches/{colony['id']}/transvasements", headers=headers, timeout=10).json()) == 1


def test_transvasement_into_prepared_hive_archives_it() -> None:
    headers, rucher_id, _ = _new_beekeeper("transprep")
    colony = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "TP-1", "rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "ruchette", "nombre_cadres": 5}, timeout=10).json()
    prepared = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "PREP-D", "rucher_id": None, "is_at_atelier": True, "format_ruche": "dadant", "nombre_cadres": 10, "has_partition": True}, timeout=10).json()
    moved = requests.post(
        f"{API_BASE_URL}/ruches/{colony['id']}/transvasements",
        headers=headers,
        json={"format_apres": "dadant", "provenance": "ruche_atelier", "ruche_atelier_id": prepared["id"], "cadres_transferes": 5, "cadres_ajoutes": 5},
        timeout=10,
    )
    assert moved.status_code == 201, moved.text
    hive = requests.get(f"{API_BASE_URL}/ruches/{colony['id']}", headers=headers, timeout=10).json()
    assert hive["format_ruche"] == "dadant" and hive["has_partition"] is True and hive["nombre_cadres"] == 10
    assert requests.get(f"{API_BASE_URL}/ruches/{prepared['id']}", headers=headers, timeout=10).json()["motif_archive"] == "transvasement"
    stock = _stock(headers)
    assert stock[("cadre", "dadant")]["quantite_atelier_totale"] == 5
    assert stock[("corps", "ruchette")]["quantite_atelier_totale"] == 1


def test_visit_carries_transvasement_and_capture_date() -> None:
    headers, rucher_id, _ = _new_beekeeper("visittrans")
    colony = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "VT-1", "rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "ruchette", "nombre_cadres": 6}, timeout=10).json()
    body = {
        "ruche_id": colony["id"],
        "visite_rucher_id": None,
        "note_ruche": 4,
        "statut_validation": "valide",
        "date_visite": "2026-05-02T08:40:00Z",
        "transvasement": {"format_apres": "dadant", "provenance": "stock", "cadres_transferes": 6, "cadres_ajoutes": 4, "annee_cire": 2026},
    }
    refused_stock = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=body, timeout=10)
    assert refused_stock.status_code == 201, refused_stock.text
    assert refused_stock.json()["date_visite"].startswith("2026-05-02T08:40")
    assert refused_stock.json()["avertissements"] and "Stock atelier insuffisant" in refused_stock.json()["avertissements"][0]
    assert requests.get(f"{API_BASE_URL}/ruches/{colony['id']}", headers=headers, timeout=10).json()["format_ruche"] == "ruchette"

    body["transvasement"]["provenance"] = "achat"
    applied = requests.post(f"{API_BASE_URL}/visites", headers=headers, json=body, timeout=10)
    assert applied.status_code == 201, applied.text
    assert applied.json()["avertissements"] == []
    assert "production" in applied.json()["tag_suggestions"]
    assert requests.get(f"{API_BASE_URL}/ruches/{colony['id']}", headers=headers, timeout=10).json()["format_ruche"] == "dadant"


def test_watch_tag_is_derived_from_criteria_and_not_duplicated() -> None:
    headers, rucher_id, _ = _new_beekeeper("watch")
    hive = requests.post(f"{API_BASE_URL}/ruches", headers=headers, json={"identifiant_personnalise": "W-1", "rucher_id": rucher_id, "is_at_atelier": False}, timeout=10).json()

    def watch_tags() -> list[dict]:
        hives = requests.get(f"{API_BASE_URL}/ruches", headers=headers, params={"rucher_id": rucher_id}, timeout=10).json()
        return [tag for tag in next(item for item in hives if item["id"] == hive["id"])["tags"] if tag["libelle"] == "a surveiller"]

    assert watch_tags() == []
    low = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": hive["id"], "visite_rucher_id": None, "note_ruche": 2, "statut_validation": "valide"}, timeout=10)
    assert low.status_code == 201, low.text
    tags = watch_tags()
    assert len(tags) == 1 and tags[0]["source"] == "derive"
    own_tags = requests.get(f"{API_BASE_URL}/ruches/{hive['id']}/tags", headers=headers, timeout=10).json()
    assert any(tag["libelle"] == "a surveiller" and tag["source"] == "derive" for tag in own_tags)
    cheptel = requests.get(f"{API_BASE_URL}/statistiques/cheptel", headers=headers, params={"rucher_id": rucher_id}, timeout=10).json()
    assert any("Note faible (2/5)" in entry["motifs"] for entry in cheptel["ruches_a_surveiller"])

    manual = requests.post(f"{API_BASE_URL}/ruches/{hive['id']}/tags", headers=headers, json={"libelle": "a surveiller"}, timeout=10)
    assert manual.status_code == 201, manual.text
    assert [tag["source"] for tag in watch_tags()] == ["manuel"]

    requests.delete(f"{API_BASE_URL}/ruches/{hive['id']}/tags/{manual.json()['id']}", headers=headers, timeout=10)
    good = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": hive["id"], "visite_rucher_id": None, "note_ruche": 4, "statut_validation": "valide"}, timeout=10)
    assert good.status_code == 201, good.text
    assert watch_tags() == []


# --- Lot L6 : fiches Statistiques ---------------------------------------------

def test_hive_and_apiary_sheets_follow_period_and_show_all_hives() -> None:
    headers, rucher_id, _ = _new_beekeeper("sheets")
    hive = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "SH-1", "rucher_id": rucher_id, "is_at_atelier": False, "format_ruche": "dadant", "nombre_cadres": 10, "reine_race": "Buckfast", "reine_annee_marquage": 2025},
        timeout=10,
    ).json()
    visit = requests.post(f"{API_BASE_URL}/visites", headers=headers, json={"ruche_id": hive["id"], "visite_rucher_id": None, "note_ruche": 4, "nombre_cadres_total": 10, "nombre_cadres_couvain": 5, "statut_validation": "valide"}, timeout=10)
    assert visit.status_code == 201, visit.text
    harvest = requests.post(f"{API_BASE_URL}/recoltes", headers=headers, json={"ruche_id": hive["id"], "visite_ruche_id": None, "poids_miel_kg": 12.5}, timeout=10)
    assert harvest.status_code == 201, harvest.text
    year = datetime.now().year
    season = {"start_date": f"{year}-01-01", "end_date": f"{year}-12-31"}
    last_season = {"start_date": f"{year - 1}-01-01", "end_date": f"{year - 1}-12-31"}

    sheet = requests.get(f"{API_BASE_URL}/statistiques/fiche-ruche", headers=headers, params={"ruche_id": hive["id"], **season}, timeout=10)
    assert sheet.status_code == 200, sheet.text
    data = sheet.json()
    assert data["reine_active"]["race"] == "Buckfast" and data["rucher_nom"] == "Rucher L1"
    assert data["materiel"]["corps"] == 1 and data["materiel"]["cadres"] == 10
    assert len(data["visites"]) == 1 and data["visites"][0]["nombre_cadres_couvain"] == 5
    assert data["miel_total_kg"] == 12.5
    old = requests.get(f"{API_BASE_URL}/statistiques/fiche-ruche", headers=headers, params={"ruche_id": hive["id"], **last_season}, timeout=10).json()
    assert old["visites"] == [] and old["miel_total_kg"] == 0

    apiary = requests.get(f"{API_BASE_URL}/statistiques/fiche-rucher", headers=headers, params={"rucher_id": rucher_id, **season}, timeout=10)
    assert apiary.status_code == 200, apiary.text
    summary = apiary.json()
    assert summary["ruches_actives"] == 2
    assert [item["poids_total_kg"] for item in summary["miel_par_ruche"]] == [12.5, 0.0]
    assert summary["couvain_moyen"] == 0.5 and summary["note_moyenne"] == 4

    other = _register_user(_rand_email("sheetsother"), prenom="Other")
    forbidden = requests.get(f"{API_BASE_URL}/statistiques/fiche-ruche", headers=_auth_headers(other["access_token"]), params={"ruche_id": hive["id"]}, timeout=10)
    assert forbidden.status_code == 404
    forbidden_apiary = requests.get(f"{API_BASE_URL}/statistiques/fiche-rucher", headers=_auth_headers(other["access_token"]), params={"rucher_id": rucher_id}, timeout=10)
    assert forbidden_apiary.status_code == 404


def test_stock_keeps_one_row_per_type_and_format() -> None:
    # Retour beta : des doublons type + format faisaient qu'une modification ne
    # touchait qu'une ligne, un retrait devenait alors un ajout.
    user = _register_user(_rand_email("stockone"), prenom="StockOne")
    headers = _auth_headers(user["access_token"])
    types = _material_types(headers)
    _add_stock(headers, types, "dadant", {"corps": 5})
    _add_stock(headers, types, "dadant", {"corps": 6})
    rows = [
        row for row in requests.get(f"{API_BASE_URL}/materiel-atelier", headers=headers, timeout=10).json()
        if row["ref_type_materiel_id"] == types["corps"]
    ]
    assert len(rows) == 1
    assert rows[0]["quantite_atelier"] == 11
    assert rows[0]["format_materiel"] == "dadant"
    assert _stock(headers)[("corps", "dadant")]["quantite_atelier_totale"] == 11

    update = requests.put(
        f"{API_BASE_URL}/materiel-atelier/{rows[0]['id']}",
        headers=headers,
        json={"ref_type_materiel_id": types["corps"], "format_materiel": "dadant", "quantite_atelier": 8, "quantite_en_service": 0},
        timeout=10,
    )
    assert update.status_code == 200, update.text
    assert _stock(headers)[("corps", "dadant")]["quantite_atelier_totale"] == 8

    _add_stock(headers, types, "ruchette", {"corps": 2})
    ruchette_row = next(
        row for row in requests.get(f"{API_BASE_URL}/materiel-atelier", headers=headers, timeout=10).json()
        if row["ref_type_materiel_id"] == types["corps"] and row["format_materiel"] == "ruchette"
    )
    conflict = requests.put(
        f"{API_BASE_URL}/materiel-atelier/{ruchette_row['id']}",
        headers=headers,
        json={"ref_type_materiel_id": types["corps"], "format_materiel": "dadant", "quantite_atelier": 1, "quantite_en_service": 0},
        timeout=10,
    )
    assert conflict.status_code == 409, conflict.text


def test_frames_and_partitions_use_frame_format_for_ruchettes() -> None:
    # Une ruchette Dadant porte des cadres et une partition Dadant : pas de
    # format "ruchette" pour ces deux types, contrairement au corps.
    headers, rucher_id, types = _new_beekeeper("framefmt")
    _add_stock(headers, types, "ruchette", {"cadre": 12, "partition": 2, "corps": 3})
    _add_stock(headers, types, "dadant", {"cadre": 8})
    hive = requests.post(
        f"{API_BASE_URL}/ruches",
        headers=headers,
        json={"identifiant_personnalise": "FRAME-RUCHETTE", "rucher_id": rucher_id, "format_ruche": "ruchette", "nombre_cadres": 6, "has_corps": True, "has_partition": True, "is_at_atelier": False},
        timeout=10,
    )
    assert hive.status_code == 201, hive.text

    stock = _stock(headers)
    assert ("cadre", "ruchette") not in stock
    assert ("partition", "ruchette") not in stock
    assert stock[("cadre", "dadant")]["quantite_atelier_totale"] == 20
    assert stock[("partition", "dadant")]["quantite_atelier_totale"] == 2
    assert stock[("corps", "ruchette")]["quantite_atelier_totale"] == 3
    assert stock[("corps", "ruchette")]["quantite_en_service_calculee"] == 1
    # Les cadres et la partition de la ruchette comptent en Dadant.
    assert stock[("partition", "dadant")]["quantite_en_service_calculee"] >= 1
    dadant_frames = stock[("cadre", "dadant")]["quantite_en_service_calculee"]
    assert dadant_frames >= 6


def test_dashboard_frame_occupancy_uses_body_capacity() -> None:
    headers, rucher_id, _ = _new_beekeeper("occupancy")
    hives = requests.get(f"{API_BASE_URL}/ruches", headers=headers, timeout=10).json()
    for hive in hives:
        requests.delete(f"{API_BASE_URL}/ruches/{hive['id']}", headers=headers, timeout=10)
    for identifiant, format_ruche, frames in (("OCC-RUCHETTE", "ruchette", 6), ("OCC-DADANT", "dadant", 5)):
        created = requests.post(
            f"{API_BASE_URL}/ruches",
            headers=headers,
            json={"identifiant_personnalise": identifiant, "rucher_id": rucher_id, "format_ruche": format_ruche, "nombre_cadres": frames, "is_at_atelier": False},
            timeout=10,
        )
        assert created.status_code == 201, created.text
    cheptel = requests.get(f"{API_BASE_URL}/statistiques/cheptel", headers=headers, timeout=10)
    assert cheptel.status_code == 200, cheptel.text
    payload = cheptel.json()
    assert payload["cadres_moyens_par_ruche"] == 5.5
    # Ruchette pleine (6/6) et Dadant a moitie (5/10) : 75 %, pas 5,5 cadres.
    assert payload["taux_occupation_cadres"] == 0.75
