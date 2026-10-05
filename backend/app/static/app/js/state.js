export const state = {
  config: null,
  apiBaseUrl: "",
  // Le navigateur utilise le cookie HttpOnly emis par l'API. `token` ne sert
  // qu'a migrer une ancienne session Bearer pendant ce chargement.
  token: localStorage.getItem("bee.token") || "",
  authenticated: false,
  pendingTab: null,
  // Tags choisis hors ligne pendant la saisie d'une visite : envoyes avec elle.
  pendingVisitTags: [],
  isPremium: false,
  // Creation rapide : modeles (Premium), lignes de l'apercu, rucher cible.
  modelesRuche: [],
  quickRows: [],
  quickTargetRucher: null,
  // Import : fichier lu (base64) et lignes verifiees de l'apercu.
  importFile: null,
  importLines: [],
  // Tags choisis dans la popup, poses ensemble (cle en minuscules).
  stagedRucheTags: new Map(),
  // Transvasement saisi dans la popup de visite : envoye avec la visite.
  pendingTransvasement: null,
  selectedRucher: null,
  selectedRuche: null,
  ruchers: [],
  ruches: [],
  allRuches: [],
  rucheSort: { cle: "nom", croissant: true },
  atelierRuches: [],
  selectedRucheTags: [],
  tagFavorites: [],
  resumeDialogAfterTags: null,
  selectedRucheIds: new Set(),
  pendingBulkMoveIds: [],
  latestVisitsByRuche: new Map(),
  onboarding: { ruchers: 0, ruches: 0, hasVisit: false },
  onboardingFlowActive: false,
  references: { types: new Map(), statuses: new Map(), cadreActions: new Map() },
  mergeOperationId: null
};

export const TAG_CATALOG = [
  { category: "Type de ruche", tags: ["production", "essaim", "starter", "finisseur", "nuclei", "banque a males", "ruche pedagogique", "ruche piege"] },
  { category: "Format", tags: ["dadant", "langstroth", "warre", "ruchette", "nucleus"] },
  { category: "Priorite Terrain", tags: ["a surveiller"] },
  { category: "Nourrissement", tags: ["a nourrir", "nourrissement en cours", "reserves faibles", "candi pose", "sirop donne"] },
  { category: "Reine", tags: ["reine non vue", "orpheline", "bourdonneuse", "remereage en cours", "reine a remplacer", "jeune reine", "vieille reine", "cellules royales", "ponte absente", "ponte faible"] },
  { category: "Couvain", tags: ["couvain faible", "couvain irregulier", "absence couvain", "cadres couvain a prelever"] },
  { category: "Production", tags: ["1 hausse posee", "2 hausses posees", "3 hausses posees", "4 hausses posees", "5 hausses posees", "hausse a poser", "hausse a retirer", "prete recolte", "forte production", "faible production"] },
  { category: "Sanitaire", tags: ["suspicion maladie", "varroa a controler", "traitement varroa", "quarantaine", "pillage", "fausse teigne", "colonie faible", "colonie morte"] },
  { category: "Comportement", tags: ["douce", "agressive", "essaimeuse", "hygienique"] },
  { category: "Elevage / Selection", tags: ["souche interessante", "a multiplier", "donneuse greffage", "starter", "finisseur", "nuclei", "banque a males", "test genetique"] },
  { category: "Materiel", tags: ["cadres a renouveler", "cadres neufs", "manque cadres", "plancher a nettoyer", "toit a verifier", "nourrisseur present", "grille a reine"] },
  { category: "Statut / Cycle", tags: ["active", "inactive", "atelier", "hivernage", "division prevue", "essaim recent", "ruche piege"] },
];

export const DEFAULT_TAG_FAVORITES = [
  "production",
  "essaim",
  "starter",
  "ruche pedagogique",
  "dadant",
  "ruchette",
  "a surveiller",
  "a nourrir",
  "reserves faibles",
  "orpheline",
  "bourdonneuse",
  "reine a remplacer",
  "1 hausse posee",
  "hausse a poser",
  "prete recolte",
  "varroa a controler",
  "quarantaine",
  "souche interessante",
  "cadres a renouveler",
];

export const FORMAT_LABELS = {
  dadant: "Dadant",
  langstroth: "Langstroth",
  warre: "Warre",
  ruchette: "Ruchette",
  nucleus: "Nucleus",
  autre: "Autre",
};

export const WATCHLIST_TIP = "Ruches a surveiller : reine de 2 ans ou plus, note de 2/5 ou moins, pas de ponte ou reine non vue, couvain faible en saison, visite trop ancienne (21 jours en saison, 60 jours hors saison) ou tag orpheline. Le tag a surveiller est pose et retire automatiquement.";

export const MATERIAL_SHEET_LABELS = { plancher: "Plancher", corps: "Corps", couvre_cadre: "Couvre-cadre", toit: "Toit", partition: "Partition", grille: "Grille a reine", nourrisseur: "Nourrisseur", cadres: "Cadres", hausses: "Hausses" };
export const QUEEN_ORIGIN_LABELS = { essaimage: "Essaimage", remerage: "Remerage", apport_reine_fecondee: "Reine fecondee achetee", apport_reine_vierge: "Reine vierge", cellule_royale: "Cellule royale", inconnue: "Origine inconnue" };
