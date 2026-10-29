"""Creation rapide (gratuite), modeles de ruche et import de tableur (Premium)."""

import base64
import io
import os
import random

import requests

API_BASE_URL = os.getenv("BEEVARIUM_API_URL", "http://localhost:8000").rstrip("/")


def _user(premium: bool) -> dict[str, str]:
    email = f"rapide{random.randint(10**8, 10**9)}@example.com"
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={"email": email, "password": "motdepasse123", "is_premium": premium},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _hives(prefix: str, count: int, **extra) -> list[dict]:
    return [{"identifiant_personnalise": f"{prefix}{index:02d}", **extra} for index in range(1, count + 1)]


def test_quick_create_rucher_with_hives_for_free_account() -> None:
    headers = _user(premium=False)
    body = {
        "rucher": {"nom": "Les Tilleuls", "type_terrain": "plaine"},
        "ruches": _hives("T", 12, format_ruche="Dadant", has_grille_a_reine=True),
    }
    created = requests.post(f"{API_BASE_URL}/ruchers/creation-rapide", headers=headers, json=body, timeout=15)
    assert created.status_code == 201, created.text
    assert created.json()["ruches_creees"] == 12
    rucher_id = created.json()["rucher"]["id"]
    hives = requests.get(f"{API_BASE_URL}/ruches", headers=headers, params={"rucher_id": rucher_id}, timeout=10).json()
    assert len(hives) == 12
    first = next(hive for hive in hives if hive["identifiant_personnalise"] == "T01")
    assert first["format_ruche"] == "dadant" and first["nombre_cadres"] == 10
    assert first["has_grille_a_reine"] is True and first["has_hausse"] is False
    # Pas de reine creee : elles se saisissent a la main.
    assert requests.get(f"{API_BASE_URL}/ruches/{first['id']}/reines", headers=headers, timeout=10).json() == []

    # Ajout de ruches a un rucher existant.
    more = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=headers,
        json={"rucher_id": rucher_id, "ruches": _hives("E", 2, format_ruche="ruchette")},
        timeout=10,
    )
    assert more.status_code == 201, more.text
    hives = requests.get(f"{API_BASE_URL}/ruches", headers=headers, params={"rucher_id": rucher_id}, timeout=10).json()
    assert len(hives) == 14
    assert next(hive for hive in hives if hive["identifiant_personnalise"] == "E01")["nombre_cadres"] == 6


def test_quick_create_is_all_or_nothing() -> None:
    headers = _user(premium=False)
    first = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=headers,
        json={"rucher": {"nom": "A"}, "ruches": _hives("R", 3)},
        timeout=10,
    )
    assert first.status_code == 201, first.text
    # R03 existe deja : ni le rucher B ni ses ruches ne sont crees.
    clash = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=headers,
        json={"rucher": {"nom": "B"}, "ruches": _hives("R", 5)},
        timeout=10,
    )
    assert clash.status_code == 409, clash.text
    assert "R03" in clash.text
    ruchers = requests.get(f"{API_BASE_URL}/ruchers", headers=headers, timeout=10).json()
    assert [rucher["nom"] for rucher in ruchers] == ["A"]

    # Doublon dans la demande elle-meme.
    double = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=headers,
        json={"rucher_id": ruchers[0]["id"], "ruches": [{"identifiant_personnalise": "X1"}, {"identifiant_personnalise": "x1"}]},
        timeout=10,
    )
    assert double.status_code == 409

    # Limite gratuite : deux ruchers au plus.
    second = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide", headers=headers, json={"rucher": {"nom": "C"}, "ruches": _hives("C", 1)}, timeout=10
    )
    assert second.status_code == 201
    third = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide", headers=headers, json={"rucher": {"nom": "D"}, "ruches": _hives("D", 1)}, timeout=10
    )
    assert third.status_code == 403
    too_many = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide", headers=headers, json={"rucher_id": ruchers[0]["id"], "ruches": _hives("Z", 201)}, timeout=10
    )
    assert too_many.status_code == 422


def test_hive_templates_are_premium() -> None:
    free = _user(premium=False)
    assert requests.get(f"{API_BASE_URL}/modeles-ruche", headers=free, timeout=10).status_code == 403
    assert requests.post(f"{API_BASE_URL}/modeles-ruche", headers=free, json={"nom": "Dadant 10"}, timeout=10).status_code == 403

    premium = _user(premium=True)
    body = {"nom": "Dadant production", "format_ruche": "D10", "nombre_cadres": 10, "has_grille_a_reine": True, "has_hausse": True}
    created = requests.post(f"{API_BASE_URL}/modeles-ruche", headers=premium, json=body, timeout=10)
    assert created.status_code == 201, created.text
    assert created.json()["format_ruche"] == "dadant"
    assert requests.post(f"{API_BASE_URL}/modeles-ruche", headers=premium, json={"nom": " dadant PRODUCTION "}, timeout=10).status_code == 409
    listed = requests.get(f"{API_BASE_URL}/modeles-ruche", headers=premium, timeout=10).json()
    assert [item["nom"] for item in listed] == ["Dadant production"]
    other = _user(premium=True)
    assert requests.delete(f"{API_BASE_URL}/modeles-ruche/{listed[0]['id']}", headers=other, timeout=10).status_code == 404
    assert requests.delete(f"{API_BASE_URL}/modeles-ruche/{listed[0]['id']}", headers=premium, timeout=10).status_code == 204


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def test_import_csv_guesses_columns_reports_errors_then_imports() -> None:
    premium = _user(premium=True)
    requests.post(f"{API_BASE_URL}/ruchers", headers=premium, json={"nom": "Bois Joli"}, timeout=10)
    csv_text = (
        "Nom du rucher;N° ruche;Type;Nb cadres\n"
        "bois joli;B01;dadant 10;10\n"
        "Bois Joli;B02;Langstrot;\n"
        "Les Granges;G01;D10;8\n"
        "\n"
        "Les Granges;g01;ruchette;6\n"
        "Les Granges;G02;Kenyane;abc\n"
    )
    analyse = requests.post(
        f"{API_BASE_URL}/import/ruches/analyse",
        headers=premium,
        json={"nom_fichier": "cheptel.csv", "contenu_base64": _b64(csv_text.encode("cp1252"))},
        timeout=15,
    )
    assert analyse.status_code == 200, analyse.text
    result = analyse.json()
    # "Type" contient des formats : il devient la colonne format.
    assert result["correspondance"] == {"rucher": "Nom du rucher", "identifiant": "N° ruche", "type_ruche": None, "format": "Type", "nombre_cadres": "Nb cadres"}
    lines = result["lignes"]
    assert len(lines) == 5
    assert lines[0]["rucher_existant"] is True and lines[0]["format_ruche"] == "dadant"
    assert lines[1]["format_ruche"] == "langstroth" and not lines[1]["erreurs"]
    assert any("double" in error for error in lines[3]["erreurs"])
    assert len(lines[4]["erreurs"]) == 2
    assert result["nb_erreurs"] == 2 and result["ruchers_a_creer"] == ["Les Granges"]

    # Rien n'est cree tant qu'il reste une erreur.
    refused = requests.post(f"{API_BASE_URL}/import/ruches", headers=premium, json={"lignes": lines}, timeout=15)
    assert refused.status_code == 422
    assert len(requests.get(f"{API_BASE_URL}/ruches", headers=premium, timeout=10).json()) == 0

    fixed = [dict(line) for line in lines]
    fixed[3]["identifiant"] = "G03"
    fixed[4]["format_ruche"] = "warre"
    fixed[4]["nombre_cadres"] = "8"
    check = requests.post(f"{API_BASE_URL}/import/ruches/verifier", headers=premium, json={"lignes": fixed}, timeout=15)
    assert check.status_code == 200 and check.json()["nb_erreurs"] == 0, check.text
    done = requests.post(f"{API_BASE_URL}/import/ruches", headers=premium, json={"lignes": fixed}, timeout=15)
    assert done.status_code == 201, done.text
    assert done.json() == {"ruches_creees": 5, "ruchers_crees": 1}
    ruchers = requests.get(f"{API_BASE_URL}/ruchers", headers=premium, timeout=10).json()
    assert sorted(rucher["nom"] for rucher in ruchers) == ["Bois Joli", "Les Granges"]


def test_import_xlsx_and_premium_gate() -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Rucher", "Ruche", "Format", "Cadres"])
    sheet.append(["Coteau", "C01", "Dadant", 10])
    sheet.append(["Coteau", "C02", "Ruchette", 6.0])
    buffer = io.BytesIO()
    workbook.save(buffer)
    body = {"nom_fichier": "ruches.xlsx", "contenu_base64": _b64(buffer.getvalue())}

    free = _user(premium=False)
    assert requests.post(f"{API_BASE_URL}/import/ruches/analyse", headers=free, json=body, timeout=10).status_code == 403

    premium = _user(premium=True)
    analyse = requests.post(f"{API_BASE_URL}/import/ruches/analyse", headers=premium, json=body, timeout=15)
    assert analyse.status_code == 200, analyse.text
    assert analyse.json()["nb_erreurs"] == 0
    assert [line["nombre_cadres"] for line in analyse.json()["lignes"]] == ["10", "6"]
    xls = requests.post(
        f"{API_BASE_URL}/import/ruches/analyse", headers=premium, json={"nom_fichier": "vieux.xls", "contenu_base64": _b64(b"x")}, timeout=10
    )
    assert xls.status_code == 422 and ".xlsx" in xls.text


def _type_ids(headers: dict[str, str]) -> dict[str, str]:
    rows = requests.get(f"{API_BASE_URL}/references/type-ruche", headers=headers, timeout=10).json()
    return {row["libelle"].lower(): row["id"] for row in rows}


def test_hive_type_in_quick_create_templates_import_and_visit() -> None:
    premium = _user(premium=True)
    types = _type_ids(premium)
    created = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=premium,
        json={"rucher": {"nom": "Typage"}, "ruches": [
            {"identifiant_personnalise": "P1", "ref_type_ruche_id": types["production"]},
            {"identifiant_personnalise": "E1", "ref_type_ruche_id": types["essaim"], "format_ruche": "ruchette"},
        ]},
        timeout=10,
    )
    assert created.status_code == 201, created.text
    hives = {hive["identifiant_personnalise"]: hive for hive in requests.get(f"{API_BASE_URL}/ruches", headers=premium, timeout=10).json()}
    assert hives["P1"]["ref_type_ruche_id"] == types["production"]
    assert hives["E1"]["ref_type_ruche_id"] == types["essaim"]

    # Type inconnu : rien n'est cree.
    bad = requests.post(
        f"{API_BASE_URL}/ruchers/creation-rapide",
        headers=premium,
        json={"rucher_id": created.json()["rucher"]["id"], "ruches": [{"identifiant_personnalise": "X9", "ref_type_ruche_id": "00000000-0000-0000-0000-000000000000"}]},
        timeout=10,
    )
    assert bad.status_code == 404

    modele = requests.post(f"{API_BASE_URL}/modeles-ruche", headers=premium, json={"nom": "Essaim", "ref_type_ruche_id": types["essaim"]}, timeout=10)
    assert modele.status_code == 201 and modele.json()["ref_type_ruche_id"] == types["essaim"]

    # L'essaim devient une ruche de production a la visite.
    visit = requests.post(
        f"{API_BASE_URL}/visites",
        headers=premium,
        json={"ruche_id": hives["E1"]["id"], "visite_rucher_id": None, "statut_validation": "valide", "ref_type_ruche_id": types["production"]},
        timeout=10,
    )
    assert visit.status_code == 201, visit.text
    assert requests.get(f"{API_BASE_URL}/ruches/{hives['E1']['id']}", headers=premium, timeout=10).json()["ref_type_ruche_id"] == types["production"]

    csv_text = "Rucher;Ruche;Type de ruche;Format\nTypage;T1;production;dadant\nTypage;T2;Essaims;ruchette\nTypage;T3;Kenyane;dadant\n"
    analyse = requests.post(
        f"{API_BASE_URL}/import/ruches/analyse",
        headers=premium,
        json={"nom_fichier": "types.csv", "contenu_base64": _b64(csv_text.encode())},
        timeout=10,
    ).json()
    assert analyse["correspondance"]["type_ruche"] == "Type de ruche" and analyse["correspondance"]["format"] == "Format"
    assert [bool(line["erreurs"]) for line in analyse["lignes"]] == [False, False, True]
    lines = analyse["lignes"][:2]
    done = requests.post(f"{API_BASE_URL}/import/ruches", headers=premium, json={"lignes": lines}, timeout=10)
    assert done.status_code == 201, done.text
    hives = {hive["identifiant_personnalise"]: hive for hive in requests.get(f"{API_BASE_URL}/ruches", headers=premium, timeout=10).json()}
    assert hives["T2"]["ref_type_ruche_id"] == types["essaim"]
