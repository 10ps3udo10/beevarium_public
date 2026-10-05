// Tir de charge sur les parcours reellement empruntes par un apiculteur.
//
// Ne vise jamais la beta: l environnement de test et la beta partagent le meme
// VPS, une charge mal calibree ferait tomber les deux.
import http from "k6/http";
import { check, sleep, fail } from "k6";
import { Trend, Rate } from "k6/metrics";
import { SharedArray } from "k6/data";

const BASE_URL = __ENV.BEEVARIUM_API_URL || "http://127.0.0.1:18001";
// k6 resout open() depuis le dossier du script: un chemin absolu evite toute ambiguite.
const FICHIER_COMPTES = __ENV.BEEVARIUM_COMPTES || "/w/artifacts/charge/comptes.json";

if (!BASE_URL.includes("127.0.0.1") && !BASE_URL.includes("localhost") && __ENV.AUTORISER_PRODUCTION !== "1") {
  fail(`Refus de tirer sur ${BASE_URL}. Definir AUTORISER_PRODUCTION=1 si c est reellement voulu.`);
}

const comptes = new SharedArray("comptes", () => {
  const donnees = JSON.parse(open(FICHIER_COMPTES));
  return donnees.comptes.map((compte) => ({ email: compte.email, profil: compte.profil }));
});

const MOT_DE_PASSE = "motdepasse123";

const dureeTableauDeBord = new Trend("duree_tableau_de_bord", true);
const dureeSelectionRucher = new Trend("duree_selection_rucher", true);
const dureeSaisieVisite = new Trend("duree_saisie_visite", true);
const echecsMetier = new Rate("echecs_metier");

const PALIER_MAX = Number(__ENV.PALIER_MAX || 20);

export const options = {
  // Paliers progressifs: on cherche le point de rupture, pas a casser la machine.
  stages: [
    { duration: "30s", target: Math.ceil(PALIER_MAX * 0.25) },
    { duration: "1m", target: Math.ceil(PALIER_MAX * 0.5) },
    { duration: "1m", target: PALIER_MAX },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    // Arret immediat si la latence ou les erreurs derapent.
    http_req_failed: [{ threshold: "rate<0.02", abortOnFail: true, delayAbortEval: "20s" }],
    http_req_duration: [{ threshold: "p(95)<2000", abortOnFail: true, delayAbortEval: "30s" }],
    echecs_metier: ["rate<0.02"],
    duree_tableau_de_bord: ["p(95)<2500"],
  },
};

function entetes(jeton) {
  return { headers: { "Content-Type": "application/json", Authorization: `Bearer ${jeton}` } };
}

export default function () {
  const compte = comptes[Math.floor(Math.random() * comptes.length)];

  const connexion = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: compte.email, password: MOT_DE_PASSE }),
    { headers: { "Content-Type": "application/json" }, tags: { parcours: "connexion" } }
  );
  const connecte = check(connexion, { "connexion acceptee": (r) => r.status === 200 });
  echecsMetier.add(!connecte);
  if (!connecte) {
    sleep(1);
    return;
  }
  const jeton = connexion.json("access_token");

  // 1. Ouverture du tableau de bord
  const debutTableau = Date.now();
  const cheptel = http.get(`${BASE_URL}/statistiques/cheptel`, {
    ...entetes(jeton),
    tags: { parcours: "tableau_de_bord" },
  });
  dureeTableauDeBord.add(Date.now() - debutTableau);
  echecsMetier.add(!check(cheptel, { "cheptel charge": (r) => r.status === 200 }));

  // 2. Consultation des ruchers
  const ruchers = http.get(`${BASE_URL}/ruchers`, { ...entetes(jeton), tags: { parcours: "ruchers" } });
  echecsMetier.add(!check(ruchers, { "ruchers charges": (r) => r.status === 200 }));
  const listeRuchers = ruchers.status === 200 ? ruchers.json() : [];
  if (listeRuchers.length === 0) {
    sleep(1);
    return;
  }

  sleep(Math.random() * 2);

  // 3. Selection d un rucher: ruches puis dernieres visites
  const rucher = listeRuchers[Math.floor(Math.random() * listeRuchers.length)];
  const debutSelection = Date.now();
  const ruches = http.get(`${BASE_URL}/ruches?rucher_id=${rucher.id}`, {
    ...entetes(jeton),
    tags: { parcours: "selection_rucher" },
  });
  const dernieres = http.get(`${BASE_URL}/statistiques/dernieres-visites?rucher_id=${rucher.id}`, {
    ...entetes(jeton),
    tags: { parcours: "selection_rucher" },
  });
  dureeSelectionRucher.add(Date.now() - debutSelection);
  echecsMetier.add(!check(ruches, { "ruches chargees": (r) => r.status === 200 }));
  echecsMetier.add(!check(dernieres, { "dernieres visites chargees": (r) => r.status === 200 }));

  const listeRuches = ruches.status === 200 ? ruches.json() : [];

  sleep(Math.random() * 2);

  // 4. Une saisie de visite une fois sur quatre: l apiculteur lit plus qu il n ecrit.
  if (listeRuches.length > 0 && Math.random() < 0.25) {
    const ruche = listeRuches[Math.floor(Math.random() * listeRuches.length)];
    const debutSaisie = Date.now();
    const visite = http.post(
      `${BASE_URL}/visites`,
      JSON.stringify({
        ruche_id: ruche.id,
        reine_vue: true,
        presence_ponte: true,
        etat_couvain: "normal",
        nombre_cadres_couvain: 4,
        nombre_cadres_total: 10,
        reserves_nourriture: "correct",
        note_ruche: 4,
        source_saisie: "manuelle",
        statut_validation: "valide",
        action_ids: [],
        interventions: [],
        mouvements_cadres: [],
        mouvements_hausses: [],
      }),
      { ...entetes(jeton), tags: { parcours: "saisie_visite" } }
    );
    dureeSaisieVisite.add(Date.now() - debutSaisie);
    echecsMetier.add(!check(visite, { "visite enregistree": (r) => r.status === 201 || r.status === 200 }));
  }

  sleep(1 + Math.random() * 2);
}
