#!/usr/bin/env python3
"""Genere des comptes et des donnees qui ressemblent a un usage reel.

Sert a deux choses : disposer de comptes de demonstration credibles, et fournir
un volume realiste aux tests de montee en charge.

N'utilise que la bibliotheque standard : le VPS n'a pas de gestionnaire de
paquets Python disponible.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

# Un profil decrit un type d'apiculteur, pas seulement un volume : la frequence
# des visites et la variete du materiel changent aussi le realisme des donnees.
PROFILS = {
    "amateur": {
        "ruchers": (1, 1),
        "ruches_par_rucher": (2, 4),
        "visites_par_ruche": (2, 5),
        "taux_recolte": 0.4,
        "formats": ["dadant"],
    },
    "pluriactif": {
        "ruchers": (2, 3),
        "ruches_par_rucher": (6, 12),
        "visites_par_ruche": (4, 9),
        "taux_recolte": 0.7,
        "formats": ["dadant", "ruchette"],
    },
    "pro": {
        "ruchers": (5, 8),
        "ruches_par_rucher": (20, 35),
        "visites_par_ruche": (6, 12),
        "taux_recolte": 0.85,
        "formats": ["dadant", "ruchette", "langstroth"],
    },
}

NOMS_RUCHERS = [
    "Les Tilleuls", "Grand Pre", "Coteau Sud", "La Chenaie", "Val Fleuri",
    "Les Acacias", "Plateau Nord", "Bois Joli", "La Prairie", "Font Vive",
    "Les Ruisseaux", "Haut Verger",
]
TERRAINS = ["plaine", "bocage", "montagne", "foret", "ville", "littoral"]
RACES = ["Buckfast", "Carnica", "Noire (mellifera)", "Ligustica", "Caucasienne", "Hybride"]
PROVENANCES = ["Elevage personnel", "Achat eleveur", "Essaim recupere", "Division", "Remerage naturel"]
ETATS_COUVAIN = ["faible", "normal", "excellent"]
RESERVES = ["critique", "correct", "abondant"]


class Api:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def appel(self, methode: str, chemin: str, corps: dict | None = None) -> dict:
        donnees = json.dumps(corps).encode() if corps is not None else None
        requete = urllib.request.Request(f"{self.base_url}{chemin}", data=donnees, method=methode)
        requete.add_header("Content-Type", "application/json")
        if self.token:
            requete.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                charge = reponse.read().decode()
                return json.loads(charge) if charge else {}
        except urllib.error.HTTPError as erreur:
            detail = erreur.read().decode()[:200]
            raise RuntimeError(f"{methode} {chemin} -> {erreur.code} {detail}") from erreur


def nom_de_ruche(index: int, style: str) -> str:
    if style == "numerique":
        return f"{index:03d}"
    if style == "prefixe":
        return f"R-{index:02d}"
    if style == "complexe":
        return f"{random.choice('ABCDEF')}{index}-{random.choice(['bis', 'ter', ''])}".rstrip("-")
    return f"Ruche {index}"


def creer_profil(base_url: str, email: str, profil: str, premium: bool) -> dict:
    config = PROFILS[profil]
    api = Api(base_url)
    compte = api.appel(
        "POST",
        "/auth/register",
        {"email": email, "prenom": profil.capitalize(), "password": "motdepasse123", "is_premium": premium},
    )
    api.token = compte["access_token"]

    style = random.choice(["numerique", "prefixe", "complexe", "nomme"])
    aujourd_hui = date.today()
    total_ruches = 0
    total_visites = 0
    total_recoltes = 0
    index_ruche = 1

    nb_ruchers = random.randint(*config["ruchers"])
    # Le plan gratuit est limite a 2 ruchers: la generation doit le respecter.
    if not premium:
        nb_ruchers = min(nb_ruchers, 2)

    for nom_rucher in random.sample(NOMS_RUCHERS, nb_ruchers):
        rucher = api.appel(
            "POST",
            "/ruchers",
            {
                "nom": nom_rucher,
                "type_terrain": random.choice(TERRAINS),
                "statut_activite": "actif" if random.random() > 0.1 else "inactif",
                "statut_peuplement": "peuple",
                "latitude": round(random.uniform(43.0, 49.5), 6),
                "longitude": round(random.uniform(-1.5, 6.5), 6),
            },
        )

        for _ in range(random.randint(*config["ruches_par_rucher"])):
            format_ruche = random.choice(config["formats"])
            cadres = 6 if format_ruche == "ruchette" else random.choice([9, 10, 10, 12])
            ruche = api.appel(
                "POST",
                "/ruches",
                {
                    "identifiant_personnalise": nom_de_ruche(index_ruche, style),
                    "rucher_id": rucher["id"],
                    "is_at_atelier": False,
                    "format_ruche": format_ruche,
                    "nombre_cadres": cadres,
                    "reine_annee_marquage": random.choice([aujourd_hui.year, aujourd_hui.year - 1, aujourd_hui.year - 2]),
                    "reine_race": random.choice(RACES),
                    "reine_provenance": random.choice(PROVENANCES),
                },
            )
            index_ruche += 1
            total_ruches += 1

            nb_visites = random.randint(*config["visites_par_ruche"])
            # Les visites s'etalent de mars a aujourd'hui, comme une vraie saison.
            debut_saison = date(aujourd_hui.year, 3, 1)
            jours_saison = max((aujourd_hui - debut_saison).days, 1)
            for _ in range(nb_visites):
                jour = debut_saison + timedelta(days=random.randint(0, jours_saison))
                cadres_couvain = random.randint(0, max(cadres - 2, 1))
                api.appel(
                    "POST",
                    "/visites",
                    {
                        "ruche_id": ruche["id"],
                        "date_visite": f"{jour.isoformat()}T10:00:00Z",
                        "reine_vue": random.random() > 0.35,
                        "presence_ponte": random.random() > 0.15,
                        "etat_couvain": random.choice(ETATS_COUVAIN),
                        "nombre_cadres_couvain": cadres_couvain,
                        "nombre_cadres_total": cadres,
                        "reserves_nourriture": random.choice(RESERVES),
                        "agressivite": random.randint(1, 5),
                        "note_ruche": random.choices([1, 2, 3, 4, 5], weights=[3, 7, 25, 40, 25])[0],
                        "source_saisie": "manuelle",
                        "statut_validation": "valide",
                        "action_ids": [],
                        "interventions": [],
                        "mouvements_cadres": [],
                        "mouvements_hausses": [],
                    },
                )
                total_visites += 1

            if random.random() < config["taux_recolte"] and format_ruche != "ruchette":
                api.appel(
                    "POST",
                    "/recoltes",
                    {"ruche_id": ruche["id"], "poids_miel_kg": round(random.uniform(4.0, 28.0), 1)},
                )
                total_recoltes += 1

    # Stock d'atelier coherent avec le cheptel.
    types = {t["libelle"].lower(): t["id"] for t in api.appel("GET", "/references/type-materiel")}
    for format_materiel in config["formats"]:
        for libelle in ("corps", "plancher", "toit", "hausse"):
            if libelle in types:
                api.appel(
                    "POST",
                    "/materiel-atelier",
                    {
                        "ref_type_materiel_id": types[libelle],
                        "format_materiel": format_materiel,
                        "quantite_atelier": random.randint(2, 20),
                        "quantite_en_service": 0,
                    },
                )

    return {
        "email": email,
        "profil": profil,
        "premium": premium,
        "ruchers": nb_ruchers,
        "ruches": total_ruches,
        "visites": total_visites,
        "recoltes": total_recoltes,
    }


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--api-base-url", default="http://127.0.0.1:18001")
    parseur.add_argument("--amateurs", type=int, default=3)
    parseur.add_argument("--pluriactifs", type=int, default=2)
    parseur.add_argument("--pros", type=int, default=1)
    parseur.add_argument("--parallelisme", type=int, default=3)
    parseur.add_argument("--graine", type=int, default=None)
    parseur.add_argument("--prefixe", default="demo")
    parseur.add_argument("--sortie-json", default=None, help="Fichier ou ecrire les comptes crees")
    parseur.add_argument(
        "--autoriser-production",
        action="store_true",
        help="Necessaire pour viser un environnement autre que local",
    )
    args = parseur.parse_args()

    # Garde-fou: ces donnees ne doivent jamais atterrir sur la beta par megarde.
    if "127.0.0.1" not in args.api_base_url and "localhost" not in args.api_base_url:
        if not args.autoriser_production:
            print(
                f"[seed] Refus d'ecrire sur {args.api_base_url}.\n"
                "[seed] Utiliser --autoriser-production si c'est reellement voulu.",
                file=sys.stderr,
            )
            return 2

    if args.graine is not None:
        random.seed(args.graine)

    horodatage = int(time.time())
    taches = []
    for index in range(args.amateurs):
        taches.append((f"{args.prefixe}-amateur{index}-{horodatage}@example.com", "amateur", False))
    for index in range(args.pluriactifs):
        taches.append((f"{args.prefixe}-pluri{index}-{horodatage}@example.com", "pluriactif", True))
    for index in range(args.pros):
        taches.append((f"{args.prefixe}-pro{index}-{horodatage}@example.com", "pro", True))

    print(f"[seed] {len(taches)} compte(s) a creer sur {args.api_base_url}")
    debut = time.time()
    resultats = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallelisme) as executeur:
        futurs = {
            executeur.submit(creer_profil, args.api_base_url, email, profil, premium): email
            for email, profil, premium in taches
        }
        for futur in concurrent.futures.as_completed(futurs):
            try:
                resultat = futur.result()
            except Exception as erreur:  # noqa: BLE001
                print(f"[seed] ECHEC {futurs[futur]}: {erreur}", file=sys.stderr)
                continue
            resultats.append(resultat)
            print(
                f"[seed] {resultat['profil']:<11} {resultat['email']:<45} "
                f"{resultat['ruchers']} rucher(s), {resultat['ruches']} ruche(s), "
                f"{resultat['visites']} visite(s), {resultat['recoltes']} recolte(s)"
            )

    duree = time.time() - debut
    print(
        f"\n[seed] Termine en {duree:.1f}s : {len(resultats)} compte(s), "
        f"{sum(r['ruches'] for r in resultats)} ruche(s), "
        f"{sum(r['visites'] for r in resultats)} visite(s)"
    )
    print("[seed] Mot de passe commun : motdepasse123")

    if args.sortie_json:
        chemin = pathlib.Path(args.sortie_json)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(
            json.dumps({"mot_de_passe": "motdepasse123", "comptes": resultats}, indent=2),
            encoding="utf-8",
        )
        print(f"[seed] Comptes ecrits dans {chemin}")

    return 0 if len(resultats) == len(taches) else 1


if __name__ == "__main__":
    raise SystemExit(main())
