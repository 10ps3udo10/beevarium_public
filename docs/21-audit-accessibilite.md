# Audit d'accessibilite (R13) - WCAG 2.1 AA / RGAA 4.1

Date : 2026-10-28. Version auditee : 1.37.0 (client servi par une API jetable, base locale).
Statut : audit technique outille, **pas une declaration de conformite RGAA** (un audit
complet exige une relecture humaine, des lecteurs d'ecran et l'echantillon de pages RGAA).

## Methode

1. Automatique : axe-core 4.10.2 (regles `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`) injecte par
   une spec Playwright temporaire, en 1440 px et 390 px, sur : connexion, inscription, tableau
   de bord, onglets Ruchers / Visites / Atelier / Statistiques, dialogue de nouvelle visite,
   dialogue des tags, dialogue Profil, 16 autres dialogues (ouverts via `showModal`),
   `privacy`, `legal`, `terms`, `reset-password`, `feedback`. Les Ruches et les Recoltes vivent
   dans les onglets Ruchers et Visites. axe-core n'est pas ajoute au depot (installation
   `--no-save` dans le conteneur Playwright).
2. Manuel outille : navigation clavier (connexion, nouvelle visite), focus visible, piege de
   focus et Echap dans les `<dialog>`, retour du focus, cibles tactiles, reflow a 320 px
   (equivalent zoom 200 % sur 640 px), libelles, alternatives, langue, titres, contrastes de
   la palette (ratios calcules).
3. Limites : pas de lecteur d'ecran (NVDA, VoiceOver), pas de test de zoom texte seul, pas
   d'audit du contenu des donnees saisies, pas de revue des PDF/exports.

## Resultats automatiques (noeuds en violation, 2 largeurs cumulees par page)

| Gravite axe | Avant (1440 / 390) | Apres (1440 / 390) |
|---|---|---|
| critique | 28 / 28 | 0 / 0 |
| serieuse | 24 / 25 | 1 / 1 (transitoire, voir ci-dessous) |
| Total | 52 / 53 | 1 / 1 |

Le « avant » inclut 3 faux positifs de `feedback.html` (animation d'entree capturee en cours de
fondu, ratios 1.4 a 2.4) ; le « apres » attend la fin de l'animation. Le reliquat est le
bouton `#btn-register-submit` de l'inscription mesure en pleine transition de couleur
(4.15 mesure a mi-transition, 4.9 a l'etat final) : faux positif.

## Non-conformites

| # | Critere WCAG / RGAA | Page(s) | Gravite | Occurrences (avant) | Correction | Statut |
|---|---|---|---|---|---|---|
| 1 | 4.1.2 Nom, role, valeur / RGAA 7.1 : `aria-selected` sur des `<button>` sans `role=tab` | toutes les pages connectees (barre d'onglets) | majeur | 5 boutons x 5 vues = 25 | `aria-current` (etat « page courante ») a la place, dans `index.html` et `js/navigation.js` | corrige |
| 2 | 1.4.3 Contraste minimum / RGAA 3.2 : texte `#fbfaf5` sur bouton `--sage` `#78917f` = 3.26:1 | tous les boutons primaires (connexion, inscription, enregistrer, dialogues...) | majeur | ~20 types de boutons, 1 a 2 par vue | nouvelle variable `--sage-btn: #557560` (4.9:1) pour `.btn` ; `--sage` inchange partout ailleurs | corrige |
| 3 | 1.4.3 : texte `--ok` `#5d7f65` sur fonds teintes = 3.8 a 4.0:1 (statut synchro, onboarding, pastille de l'annee) | dialogue visite, tableau de bord mobile, statistiques | majeur | 5 | `--ok` passe a `#4f7058` (4.75 a 5.4:1) | corrige |
| 4 | 1.4.3 : bouton danger `#b85b38` = 4.37:1 | dialogue rucher, profil | mineur | 2 | `--danger` passe a `#b05434` (4.83:1) | corrige |
| 5 | 4.1.2 / 1.3.1, RGAA 11.1 : 3 `<select>` de filtre des visites sans nom | onglet Visites | majeur | 3 | `aria-label` (Type d'entree, Statut, Source) | corrige |
| 6 | 1.3.1 / 3.3.2, RGAA 11.1 : champs sans libelle (recherche des visites ; nombre de hausses x2, dans le `<label>` d'une case) | onglet Visites, dialogues visite | mineur | 3 | `aria-label` | corrige |
| 7 | 2.5.5 (AAA, recommande) cibles tactiles : menus de portee (36 px), options (32 px), pastille profil (33 px) | Visites, Ruchers, entete | mineur | ~25 elements | `min-height: 2.75rem` sous `@media (pointer: coarse)` | corrige |
| 8 | 1.3.1 / RGAA 9.1 : hierarchie de titres - l'application connectee n'expose que des `h3` (pas de `h1`/`h2`) | application connectee | mineur | 1 | Ajouter un `h1` (« Beevarium ») et passer les titres de section en `h2` ; touche le CSS des titres | **non applique** (rendu) |
| 9 | 2.4.1 / RGAA 12.7 : pas de lien d'evitement « Aller au contenu » | toutes | mineur | 1 | Lien visible au focus vers `#dashboard-card` | **non applique** (ajout d'UI, zone `index.html` modifiee en parallele) |
| 10 | 4.1.3 / RGAA 7.5 : messages de statut (`#status`, hints de formulaires) - verifier `role="status"` / `aria-live` partout | formulaires | mineur | a verifier | Ajouter `aria-live="polite"` aux conteneurs de message | **non applique** (logique JS) |
| 11 | 4.1.2 : onglets en `<button>` sans `role=tablist/tab/tabpanel` | navigation | mineur | 1 | Option : motif ARIA tabs complet avec fleches. A decider avec le concepteur | **non applique** (JS) |
| 12 | 1.4.3 : `--accent` `#b88b2f` avec texte `--ink` = 4.28:1 (non remonte par axe, a verifier dans les usages) | pastilles accent | mineur | a verifier | Assombrir l'accent ou texte plus fonce | **non applique** (identite visuelle) |

## Controles manuels

| Controle | Resultat |
|---|---|
| Ordre du focus, connexion | conforme : logo, e-mail, mot de passe, boutons, liens ; Entree soumet |
| Focus visible | conforme : contour natif ou 2 px sur tous les elements testes (aucun element sans indicateur) |
| Dialogue de visite : piege de focus | conforme (`showModal` natif) : 60 Tab successifs sans sortie |
| Echap | conforme : ferme le dialogue des tags puis celui de la visite ; focus rendu a `#btn-new-visit` |
| Reflow 320 px (zoom 200 %) | conforme : aucun defilement horizontal (connexion, tableau de bord, visite) ; le viewport ne bloque pas le zoom |
| Cibles tactiles >= 44 px | partiel avant correction (#7) ; boutons `.btn` et champs deja >= 43 px ; liens de pied de page en ligne (17 px) tolere (liens dans un texte) |
| Libelles de champs | 6 manques, corriges (#5, #6) |
| Textes alternatifs | conforme : aucune `<img>` ni SVG sans alternative |
| Langue | conforme : `lang="fr"` sur toutes les pages |
| Dialogues nommes | conforme : chaque `<dialog>` contient un titre |
| Titres | non conforme (#8) |

## Contrastes de la palette (apres correction)

| Paire | Ratio |
|---|---|
| `--ink` / `--card` | 13.1 |
| `--muted` / `--card`, `--bg-1`, `--bg-2` | 5.7 / 5.3 / 5.1 |
| `--sage-dark` / `--sage-soft` | 6.5 |
| `#fbfaf5` / `--sage-btn` | 4.9 |
| `#fbfaf5` / `--danger` | 4.8 |
| `--ok` / `--card`, `#e6f0e9` | 5.4 / 4.75 |
| `--line` / blanc (bordures de champs, 1.4.11) | 10.9 |
| `--sage` / `--card` (decor) | 3.35 (>= 3 pour un composant non textuel) |
| `--ink` / `--accent` | 4.28 (a corriger, #12) |

## Taux de conformite estime

Sur les 50 criteres WCAG 2.1 A + AA, les controles outilles ne trouvent plus de violation
automatique apres correction ; restent les points 8 a 12 (criteres 1.3.1, 2.4.1, 4.1.3, 1.4.3
partiels). Estimation : **environ 90 % des criteres testables conformes** (avant : ~80 %).
Ce chiffre est indicatif : seuls 30 a 40 % des criteres sont detectables automatiquement et
aucun test avec lecteur d'ecran n'a ete fait. Pas de declaration RGAA tant que le plan ci-dessous
n'est pas termine.

## Plan d'actions

1. Court terme : decider des points 8, 9, 11 (titres, lien d'evitement, motif ARIA tabs) ; ajouter
   `aria-live` aux messages (10) ; corriger l'accent (12).
2. Tests lecteur d'ecran (VoiceOver iOS, TalkBack, NVDA) sur les parcours connexion, visite, tags.
3. Publier une declaration d'accessibilite (obligatoire seulement pour les organismes soumis ;
   recommandee) et une page de contact accessibilite.
4. Garde-fou : le test `accessibilite : langue, libelles des champs et titres des dialogues`
   (`tests/e2e/parcours.spec.js`) verifie `lang="fr"`, un nom accessible pour chaque champ visible
   (connexion, onglet Visites, dialogue de visite) et un titre pour chaque `<dialog>`. Rejouer
   axe-core a chaque refonte visuelle (hors depot).
