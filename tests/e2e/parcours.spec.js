// Tests de parcours utilisateur.
// Ils couvrent ce que les tests d API ne voient pas: une erreur de syntaxe dans
// app.js rend l application inutilisable alors que toute l API reste verte.
const { test, expect } = require("@playwright/test");

const BASE_URL = process.env.BEEVARIUM_APP_URL || "http://127.0.0.1:18001";
const MOT_DE_PASSE = "motdepasse123";

function emailUnique(prefixe) {
  return `${prefixe}${Date.now()}${Math.floor(Math.random() * 1000)}@example.com`;
}

async function creerCompte(page, email) {
  const reponse = await page.request.post(`${BASE_URL}/auth/register`, {
    data: { email, prenom: "E2E", password: MOT_DE_PASSE, is_premium: true },
  });
  expect(reponse.status()).toBe(201);
  await page.context().clearCookies();
}

async function seConnecter(page, email) {
  await page.goto(`${BASE_URL}/app/`);
  await page.fill("#email", email);
  await page.fill("#password", MOT_DE_PASSE);
  await page.click("#btn-login");
  await expect(page.locator("#dashboard-card")).toBeVisible();
}

async function ouvrirOnglet(page, onglet) {
  await page.click("#btn-open-nav");
  await page.click(`button[data-tab="${onglet}"]`);
  // Comme un utilisateur, le curseur quitte le menu, qui se referme.
  const largeur = page.viewportSize()?.width || 1280;
  await page.mouse.move(largeur - 20, 400);
  await expect(page.locator("#main-nav")).not.toHaveClass(/is-open/);
}

// Le bouton de deconnexion vit dans un <details> replie.
async function ouvrirMenuProfil(page) {
  await page.click("#profile-pill");
  await expect(page.locator("#btn-logout")).toBeVisible();
}

test("un testeur cree son compte depuis l ecran de connexion @critical", async ({ page }) => {
  await page.goto(`${BASE_URL}/app/`);
  await page.click("#btn-register-open");
  await expect(page.locator("#register-card")).toBeVisible();
  await page.fill("#register-prenom", "Testeur");
  await page.fill("#register-email", emailUnique("e2einscription"));
  await page.fill("#register-password", MOT_DE_PASSE);
  await page.click("#btn-register-submit");
  await expect(page.locator("#register-hint")).toContainText("conditions");
  await page.check("#register-terms");
  await page.click("#btn-register-submit");
  await expect(page.locator("#dashboard-card")).toBeVisible();
  await expect(page.locator("#register-card")).toBeHidden();
});

test("aucune erreur JavaScript au chargement @critical", async ({ page }) => {
  const erreurs = [];
  page.on("pageerror", (erreur) => erreurs.push(erreur.message));
  await page.goto(`${BASE_URL}/app/`);
  await expect(page.locator("#btn-login")).toBeVisible();
  // Le statut prouve que bootstrap est alle jusqu au bout.
  await expect(page.locator("#status")).toContainText("Client pret");
  expect(erreurs).toEqual([]);
});

test("le bouton de connexion reagit", async ({ page }) => {
  const email = emailUnique("e2elogin");
  await creerCompte(page, email);
  await seConnecter(page, email);
  await ouvrirMenuProfil(page);
});

test("un nouveau compte cree son rucher et ses ruches d un coup", async ({ page }) => {
  const email = emailUnique("e2eonboarding");
  await creerCompte(page, email);
  await seConnecter(page, email);
  await expect(page.locator("#onboarding-card")).toBeVisible();
  await expect(page.locator("#btn-onboarding-next")).toHaveText("Creer mon premier rucher");
  await page.click("#btn-onboarding-next");
  await expect(page.locator("#quick-create-dialog")).toBeVisible();
  await page.fill("#quick-rucher-name", "Rucher Onboarding");
  await page.fill("#quick-count", "4");
  await page.fill("#quick-prefix", "OB");
  await expect(page.locator("#quick-preview-body tr")).toHaveCount(4);
  await expect(page.locator('[data-quick-row="0"][data-quick-field="identifiant"]')).toHaveValue("OB01");
  // Une ligne corrigee a la main dans l apercu.
  await page.fill('[data-quick-row="3"][data-quick-field="identifiant"]', "ONBOARD-01");
  await page.selectOption('[data-quick-row="3"][data-quick-field="format"]', "ruchette");
  await expect(page.locator("#btn-quick-submit")).toHaveText("Creer 4 ruche(s)");
  await page.click("#btn-quick-submit");
  await expect(page.locator("#quick-create-dialog")).toBeHidden();
  await expect(page.locator("#btn-onboarding-next")).toHaveText("Enregistrer ma premiere visite");
  const ruches = await page.evaluate(async () => (await (await fetch("/ruches", { credentials: "include" })).json()));
  expect(ruches.map((ruche) => ruche.identifiant_personnalise).sort()).toEqual(["OB01", "OB02", "OB03", "ONBOARD-01"]);
  const ruchette = ruches.find((ruche) => ruche.identifiant_personnalise === "ONBOARD-01");
  expect([ruchette.format_ruche, ruchette.nombre_cadres]).toEqual(["ruchette", 6]);
  const types = await page.evaluate(async () => (await (await fetch("/references/type-ruche", { credentials: "include" })).json()));
  const typeId = (libelle) => types.find((item) => item.libelle === libelle).id;
  // Type par defaut : production.
  expect(new Set(ruches.map((ruche) => ruche.ref_type_ruche_id))).toEqual(new Set([typeId("Production")]));
  await page.click("#btn-onboarding-next");
  await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "visites");
  await expect(page.locator("#visit-create-dialog")).toBeVisible();
  // Le type se change pendant la visite.
  await expect(page.locator("#visite-type-ruche")).toHaveValue(typeId("Production"));
  await page.selectOption("#visite-type-ruche", { label: "Essaim" });
  await page.fill("#visite-note", "4");
  await page.click('#visite-form button[type="submit"]');
  await expect(page.locator("#visit-create-dialog")).toBeHidden();
  await expect.poll(async () => page.evaluate(async () => {
    const liste = await (await fetch("/ruches", { credentials: "include" })).json();
    return liste.map((ruche) => ruche.ref_type_ruche_id);
  })).toContain(typeId("Essaim"));
});

test("compte gratuit : creation rapide libre, modeles et import grises", async ({ page }) => {
  const email = emailUnique("e2egratuit");
  const inscription = await page.request.post(`${BASE_URL}/auth/register`, {
    data: { email, prenom: "Free", password: MOT_DE_PASSE, is_premium: false },
  });
  expect(inscription.status()).toBe(201);
  await page.context().clearCookies();
  await seConnecter(page, email);
  await ouvrirOnglet(page, "ruchers");
  await expect(page.locator("#btn-import-open")).toBeDisabled();
  await page.click("#btn-quick-create");
  await expect(page.locator("#quick-template")).toBeDisabled();
  await expect(page.locator("#btn-quick-save-template")).toBeDisabled();
  await page.fill("#quick-rucher-name", "Prairie");
  await page.fill("#quick-count", "3");
  await page.click("#btn-quick-submit");
  await expect(page.locator("#quick-create-dialog")).toBeHidden();
  await expect(page.locator("#ruches-list")).toContainText("R03");
  // Ajout de plusieurs ruches au rucher selectionne : la numerotation continue.
  await page.click("#btn-quick-add-hives");
  await expect(page.locator("#quick-rucher-target")).toContainText("Prairie");
  await expect(page.locator('[data-quick-row="0"][data-quick-field="identifiant"]')).toHaveValue("R04");
  await page.fill("#quick-count", "2");
  await page.click("#btn-quick-submit");
  await expect(page.locator("#quick-create-dialog")).toBeHidden();
  await expect(page.locator("#ruches-list")).toContainText("R05");
});

test("compte premium : modele de ruche et import d un tableur", async ({ page }) => {
  const email = emailUnique("e2eimport");
  await creerCompte(page, email);
  await seConnecter(page, email);
  await ouvrirOnglet(page, "ruchers");
  await page.click("#btn-quick-create");
  await page.selectOption("#quick-format", "langstroth");
  await page.check("#quick-has-hausse");
  page.once("dialog", (dialogue) => dialogue.accept("Langstroth hausse"));
  await page.click("#btn-quick-save-template");
  await expect(page.locator("#quick-create-hint")).toContainText("enregistre");
  await page.click("#btn-close-quick-create");

  await page.click("#btn-import-open");
  await expect(page.locator("#import-dialog")).toBeVisible();
  const csv = "Rucher;N° ruche;Type\nColline;C01;Dadant\nColline;C02;Kenyane\n";
  await page.setInputFiles("#import-file", { name: "cheptel.csv", mimeType: "text/csv", buffer: Buffer.from(csv, "utf8") });
  await expect(page.locator("#import-summary")).toContainText("1 en erreur");
  await expect(page.locator("#import-map-identifiant")).toHaveValue("N° ruche");
  await page.fill('[data-import-row="1"][data-import-field="format_ruche"]', "warre");
  await page.click("#btn-import-submit");
  await expect(page.locator("#import-dialog")).toBeHidden();
  await expect(page.locator("#ruchers-list")).toContainText("Colline");
  const ruches = await page.evaluate(async () => (await (await fetch("/ruches", { credentials: "include" })).json()));
  expect(ruches.map((ruche) => ruche.format_ruche).sort()).toEqual(["dadant", "warre"]);
});

test("l oeil affiche puis masque le mot de passe", async ({ page }) => {
  await page.goto(`${BASE_URL}/app/`);
  await page.fill("#password", "secret-visible");
  const oeil = page.locator('[data-password-for="password"]');
  await oeil.click();
  await expect(page.locator("#password")).toHaveAttribute("type", "text");
  await expect(oeil).toHaveAttribute("aria-pressed", "true");
  await oeil.click();
  await expect(page.locator("#password")).toHaveAttribute("type", "password");
});

test("la connexion par touche Entree fonctionne", async ({ page }) => {
  const email = emailUnique("e2eenter");
  await creerCompte(page, email);
  await page.goto(`${BASE_URL}/app/`);
  await page.fill("#email", email);
  await page.fill("#password", MOT_DE_PASSE);
  await page.press("#password", "Enter");
  await expect(page.locator("#dashboard-card")).toBeVisible();
});

test("le parcours mot de passe oublie est accessible", async ({ page }) => {
  await page.goto(`${BASE_URL}/app/`);
  await page.click("#btn-forgot-open");
  await expect(page.locator("#forgot-card")).toBeVisible();
  await page.fill("#forgot-email", "inconnu@example.com");
  await page.click("#btn-forgot-submit");
  await expect(page.locator("#forgot-hint")).toContainText("Si un compte existe");
});

test("un testeur connecte peut envoyer un retour", async ({ page }) => {
  const email = emailUnique("e2efeedback");
  await creerCompte(page, email);
  await seConnecter(page, email);
  await page.goto(`${BASE_URL}/app/feedback.html`);
  await page.selectOption("#feedback-category", "idee");
  await page.fill("#feedback-message", "Une vue de saison serait utile pour preparer les visites.");
  await page.fill("#feedback-context", "Tableau de bord");
  await page.click('#feedback-form button[type="submit"]');
  await expect(page.locator("#feedback-status")).toContainText("votre retour a bien ete envoye");
});

test("creer un rucher puis une ruche puis une visite @critical", async ({ page }) => {
  const email = emailUnique("e2eparcours");
  await creerCompte(page, email);
  await seConnecter(page, email);

  await ouvrirOnglet(page, "ruchers");
  await page.click("#btn-show-rucher-form");
  await page.fill("#create-rucher-name", "Rucher E2E");
  await page.click('#rucher-create-form button[type="submit"]');
  await expect(page.locator("#ruchers-list")).toContainText("Rucher E2E");

  await page.click('#ruchers-list button:has-text("Rucher E2E")');
  await expect(page.locator("#rucher-selected-panel")).toBeVisible();

  await page.click("#btn-show-ruche-form");
  await page.fill("#ruche-identifiant", "E2E-01");
  await page.selectOption("#ruche-format", "dadant");
  await page.fill("#ruche-cadres", "10");
  await page.click('#ruche-form button[type="submit"]');
  await expect(page.locator("#ruches-list")).toContainText("E2E-01");
  await expect(page.locator("#dashboard-ruches-count")).toHaveText("1");
  await ouvrirOnglet(page, "atelier");
  await expect(page.locator("#atelier-stock-list")).toContainText("Corps · Dadant");

  await ouvrirOnglet(page, "visites");
  await page.selectOption("#visite-scope-rucher", { label: "Rucher E2E" });
  await expect(page.locator("#visite-scope-ruche")).toContainText("E2E-01");
  await page.selectOption("#visite-scope-ruche", { label: "E2E-01" });
  await expect(page.locator("#visite-scope-reminder")).toContainText("E2E-01");
  await page.click("#btn-new-visit");
  await expect(page.locator("#visit-create-dialog")).toBeVisible();
  await page.fill("#visite-note", "4");
  await page.fill("#visite-cadres-total", "10");
  await page.fill("#visite-cadres-couvain", "4");
  await page.click('#visite-form button[type="submit"]');
  await expect(page.locator("#visite-form-hint")).toContainText("Visite enregistree");

  // On doit rester sur l onglet Visites, ruche toujours selectionnee.
  await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "visites");
  await expect(page.locator("#visite-scope-ruche")).toHaveValue(/.+/);

  // La visite suivante reprend les cadres de la ruche et de cette visite.
  if (await page.locator("#visit-create-dialog").isVisible()) await page.click("#btn-close-create-visit");
  await page.click("#btn-new-visit");
  await expect(page.locator("#visite-cadres-total")).toHaveValue("10");
  await expect(page.locator("#visite-cadres-couvain")).toHaveValue("4");
  await expect(page.locator("#visite-form-hint")).toContainText("pre-remplis");

  // Un ajout de cadres augmente le total, un retrait le diminue.
  await page.selectOption("#visite-cadres-action", { label: "Ajout cadre construit sec" });
  await page.fill("#visite-cadres-quantite", "2");
  await page.locator("#visite-cadres-quantite").dispatchEvent("change");
  await expect(page.locator("#visite-cadres-total")).toHaveValue("12");
  await expect(page.locator("#visite-cadres-annee")).not.toHaveValue("");
  await page.selectOption("#visite-cadres-action", { label: "Retrait vieux cadre" });
  await expect(page.locator("#visite-cadres-total")).toHaveValue("8");
});

test("le formulaire de ruche s ouvre en edition", async ({ page }) => {
  const email = emailUnique("e2eedition");
  await creerCompte(page, email);
  await seConnecter(page, email);

  await ouvrirOnglet(page, "ruchers");
  await page.click("#btn-show-rucher-form");
  await page.fill("#create-rucher-name", "Rucher Edition");
  await page.click('#rucher-create-form button[type="submit"]');
  await page.click('#ruchers-list button:has-text("Rucher Edition")');
  await page.click("#btn-show-ruche-form");
  await page.fill("#ruche-identifiant", "EDIT-01");
  await page.click('#ruche-form button[type="submit"]');

  await page.click('#ruches-list button:has-text("EDIT-01")');
  await page.click("#btn-ruche-edit");
  await expect(page.locator("#ruche-form")).toBeVisible();
  await expect(page.locator("#ruche-identifiant")).toHaveValue("EDIT-01");
});

test("le detail du rucher reste dans son onglet", async ({ page }) => {
  const email = emailUnique("e2eonglet");
  await creerCompte(page, email);
  await seConnecter(page, email);

  await ouvrirOnglet(page, "ruchers");
  await page.click("#btn-show-rucher-form");
  await page.fill("#create-rucher-name", "Rucher Onglet");
  await page.click('#rucher-create-form button[type="submit"]');
  await page.click('#ruchers-list button:has-text("Rucher Onglet")');
  await expect(page.locator("#rucher-selected-panel")).toBeVisible();

  await ouvrirOnglet(page, "visites");
  await expect(page.locator("#rucher-selected-panel")).toBeHidden();
  await ouvrirOnglet(page, "stats");
  await expect(page.locator("#rucher-selected-panel")).toBeHidden();
});

test("les colonnes de ruches sont triables", async ({ page }) => {
  const email = emailUnique("e2etri");
  await creerCompte(page, email);
  await seConnecter(page, email);

  await ouvrirOnglet(page, "ruchers");
  await page.click("#btn-show-rucher-form");
  await page.fill("#create-rucher-name", "Rucher Tri");
  await page.click('#rucher-create-form button[type="submit"]');
  await page.click('#ruchers-list button:has-text("Rucher Tri")');

  for (const nom of ["TRI-03", "TRI-01", "TRI-02"]) {
    await page.click("#btn-show-ruche-form");
    await page.fill("#ruche-identifiant", nom);
    await page.click('#ruche-form button[type="submit"]');
    await expect(page.locator("#ruches-list")).toContainText(nom);
  }

  const noms = () => page.$$eval("#ruches-list table tbody button.table-link", (els) => els.map((e) => e.textContent));
  expect(await noms()).toEqual(["TRI-01", "TRI-02", "TRI-03"]);
  await page.click('.th-sort[data-sort="nom"]');
  expect(await noms()).toEqual(["TRI-03", "TRI-02", "TRI-01"]);
});

test("la deconnexion invalide la session @critical", async ({ page }) => {
  const email = emailUnique("e2elogout");
  await creerCompte(page, email);
  await seConnecter(page, email);
  await ouvrirMenuProfil(page);
  await page.click("#btn-logout");
  await expect(page.locator("#auth-card")).toBeVisible();
  await page.reload();
  await expect(page.locator("#auth-card")).toBeVisible();
});

// --- Lot L1 (retours concepteur 2026-10) -----------------------------------

async function compteAvecRucher(page, prefixe, autresRuchers = []) {
  const email = emailUnique(prefixe);
  const inscription = await page.request.post(`${BASE_URL}/auth/register`, {
    data: { email, prenom: "E2E", password: MOT_DE_PASSE, is_premium: true },
  });
  expect(inscription.status()).toBe(201);
  const headers = { Authorization: `Bearer ${(await inscription.json()).access_token}` };
  const rucher = await (await page.request.post(`${BASE_URL}/ruchers`, {
    headers,
    data: { nom: "Bois Joli", latitude: 45.9, longitude: 3.9, type_terrain: "plaine", statut_activite: "actif", statut_peuplement: "peuple" },
  })).json();
  for (const nom of autresRuchers) {
    await page.request.post(`${BASE_URL}/ruchers`, { headers, data: { nom, type_terrain: "plaine", statut_activite: "actif", statut_peuplement: "peuple" } });
  }
  for (const identifiant of ["R17", "E22"]) {
    const reponse = await page.request.post(`${BASE_URL}/ruches`, {
      headers,
      data: { identifiant_personnalise: identifiant, rucher_id: rucher.id, is_at_atelier: false },
    });
    expect(reponse.status()).toBe(201);
  }
  await page.context().clearCookies();
  const erreurs = [];
  page.on("pageerror", (erreur) => erreurs.push(erreur.message));
  await seConnecter(page, email);
  return erreurs;
}

test("Nouvelle recolte s ouvre depuis Visites sans ruche choisie", async ({ page }) => {
  const erreurs = await compteAvecRucher(page, "e2erecolte");
  await ouvrirOnglet(page, "visites");
  await page.click("#btn-new-harvest");
  await expect(page.locator("#harvest-dialog")).toBeVisible();
  await expect(page.locator("#harvest-dialog-title")).toHaveText("Nouvelle recolte");
  await expect(page.locator("#btn-delete-harvest")).toBeHidden();
  expect(erreurs).toEqual([]);
});

test("l actualisation conserve l onglet actif", async ({ page }) => {
  await compteAvecRucher(page, "e2eonglethash");
  await ouvrirOnglet(page, "visites");
  await expect(page).toHaveURL(/#visites$/);
  await page.reload();
  await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "visites");
  await expect(page.locator("#visites-type-filter")).toHaveValue("");
});

test("la recherche Statistiques selectionne la ruche", async ({ page }) => {
  await compteAvecRucher(page, "e2estatsearch");
  await ouvrirOnglet(page, "stats");
  await expect(page.locator("#period-window")).toHaveValue("season");
  await page.fill("#stats-search", "r17");
  await page.press("#stats-search", "Enter");
  await expect(page.locator("#stats-scope-ruche option:checked")).toHaveText("R17");
  await expect(page.locator("#stats-scope-rucher option:checked")).toHaveText("Bois Joli");
});

test.describe("mobile", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("Visites tient dans un ecran de telephone", async ({ page }) => {
    await compteAvecRucher(page, "e2evisitesmobile");
    await ouvrirOnglet(page, "visites");
    const debordements = await page.evaluate(() => {
      const largeur = document.documentElement.clientWidth;
      return [...document.querySelectorAll("[data-panel~='visites'] *")]
        .filter((el) => el.offsetParent && el.getBoundingClientRect().right > largeur + 1)
        .map((el) => `${el.tagName}.${el.className}`);
    });
    expect(debordements).toEqual([]);
  });

  test("un tag choisi hors ligne est pose a la synchronisation", async ({ page, context }) => {
    await compteAvecRucher(page, "e2etagoffline");
    await ouvrirOnglet(page, "visites");
    await page.selectOption("#visite-scope-rucher", { label: "Bois Joli" });
    await page.selectOption("#visite-scope-ruche", { label: "E22" });
    await context.setOffline(true);
    await page.click("#btn-new-visit");
    await page.fill("#visite-note", "3");
    await page.click("#btn-visit-tags");
    // Plusieurs tags d'un coup : deux du catalogue et un saisi a la main.
    await page.locator('#tag-dialog-catalog button.tag-quick:text-is("a nourrir")').click();
    await page.locator('#tag-dialog-catalog button.tag-quick:text-is("reine non vue")').click();
    await page.fill("#ruche-tag-input", "cire neuve");
    await expect(page.locator("#btn-add-ruche-tags")).toHaveText("Ajouter 3 tags");
    await page.click("#btn-add-ruche-tags");
    await expect(page.locator("#tag-dialog")).toBeHidden();
    await expect(page.locator("#visit-selected-tags")).toContainText("a nourrir");
    await expect(page.locator("#visit-selected-tags")).toContainText("reine non vue");
    await expect(page.locator("#visit-selected-tags")).toContainText("cire neuve");
    await page.click('#visite-form button[type="submit"]');
    await expect(page.locator("#visit-create-dialog")).toBeHidden();
    await expect(page.locator("#status")).toContainText("attente de synchronisation");
    await context.setOffline(false);
    await expect.poll(async () => page.evaluate(async () => {
      const ruches = await (await fetch("/ruches", { credentials: "include" })).json();
      const ruche = ruches.find((item) => item.identifiant_personnalise === "E22");
      const tags = await (await fetch(`/ruches/${ruche.id}/tags`, { credentials: "include" })).json();
      return tags.map((tag) => tag.libelle).sort();
    }), { timeout: 15000 }).toEqual(expect.arrayContaining(["a nourrir", "cire neuve", "reine non vue"]));
  });

  test("cocher des ruches ne decale pas la liste sous le doigt", async ({ page }) => {
    await compteAvecRucher(page, "e2ecochemobile");
    // Assez de ruches pour que la liste depasse l'ecran.
    await page.evaluate(async () => {
      const ruchers = await (await fetch("/ruchers", { credentials: "include" })).json();
      const rucher = ruchers.find((item) => item.nom === "Bois Joli");
      for (let rang = 1; rang <= 12; rang += 1) {
        await fetch("/ruches", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ identifiant_personnalise: `M${String(rang).padStart(2, "0")}`, rucher_id: rucher.id, format_ruche: "dadant", is_at_atelier: false }),
        });
      }
    });
    await page.reload();
    await expect(page.locator("#dashboard-card")).toBeVisible();
    await ouvrirRucher(page, "Bois Joli");
    // Safari iOS n'a pas d'ancrage du defilement : on le coupe pour reproduire.
    await page.addStyleTag({ content: "* { overflow-anchor: none !important; }" });
    // Les tags de la ruche arrivent apres le clic et changeaient la mise en
    // page : on mesure une fois le chargement termine.
    for (const nom of ["M03", "M04"]) {
      const caseRuche = page.getByLabel(`Selectionner ${nom}`, { exact: true });
      await caseRuche.scrollIntoViewIfNeeded();
      const avant = (await caseRuche.boundingBox()).y;
      await caseRuche.check();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(400);
      const apres = (await caseRuche.boundingBox()).y;
      expect(Math.abs(apres - avant)).toBeLessThan(2);
    }
  });
});

// --- Lot L3 -------------------------------------------------------------------

async function ouvrirRucher(page, nom) {
  await ouvrirOnglet(page, "ruchers");
  await page.click(`#ruchers-list button:has-text("${nom}")`);
  await expect(page.locator("#rucher-selected-panel")).toBeVisible();
}

test("modifier un rucher garde ses ruches et ses coordonnees", async ({ page }) => {
  await compteAvecRucher(page, "e2erucheredit");
  await ouvrirRucher(page, "Bois Joli");
  await page.click("#btn-edit-rucher");
  await expect(page.locator("#edit-rucher-latitude")).toHaveValue("45.9");
  await page.fill("#edit-rucher-name", "Bois Joli Haut");
  await page.selectOption("#edit-rucher-type", "foret");
  await page.click('#rucher-edit-form button[type="submit"]');
  await expect(page.locator("#rucher-dialog")).toBeHidden();
  await expect(page.locator("#ruchers-list")).toContainText("Bois Joli Haut");
  await expect(page.locator("#ruches-list")).toContainText("R17");
  const rucher = await page.evaluate(async () => (await (await fetch("/ruchers", { credentials: "include" })).json())[0]);
  expect(rucher.latitude).toBe(45.9);
  expect(rucher.type_terrain).toBe("foret");
});

test("supprimer un rucher occupe propose de transhumer ses ruches", async ({ page }) => {
  await compteAvecRucher(page, "e2erucherdel", ["Les Granges"]);
  await ouvrirRucher(page, "Bois Joli");
  await page.click("#btn-edit-rucher");
  await page.click("#btn-delete-rucher");
  await expect(page.locator("#rucher-delete-move-step")).toBeVisible();
  await expect(page.locator("#rucher-delete-move-text")).toContainText("2 ruche(s)");
  // Colonies vivantes : seulement vers un autre rucher, jamais l'Atelier.
  await expect(page.locator("#rucher-delete-target option")).toHaveText(["Les Granges"]);
  await page.selectOption("#rucher-delete-target", { label: "Les Granges" });
  await page.click("#btn-rucher-delete-move");
  await expect(page.locator("#rucher-delete-confirm-step")).toBeVisible();
  await page.click("#btn-rucher-delete-confirm");
  await expect(page.locator("#rucher-delete-dialog")).toBeHidden();
  await expect(page.locator("#ruchers-list")).not.toContainText("Bois Joli");
  await expect(page.locator("#dashboard-atelier-count")).toHaveText("0");
  await ouvrirRucher(page, "Les Granges");
  await expect(page.locator("#ruches-list")).toContainText("R17");
});

test("la popup de visite permet de choisir rucher puis ruche", async ({ page }) => {
  await compteAvecRucher(page, "e2evisitscope");
  await ouvrirOnglet(page, "visites");
  await page.click("#btn-new-visit");
  await expect(page.locator("#visit-create-ruche")).toBeDisabled();
  await page.selectOption("#visit-create-rucher", { label: "Bois Joli" });
  await page.selectOption("#visit-create-ruche", { label: "R17" });
  await expect(page.locator("#visite-scope-reminder")).toContainText("R17");
  await page.fill("#visite-note", "4");
  await page.click('#visite-form button[type="submit"]');
  await expect(page.locator("#visit-create-dialog")).toBeHidden();
  await expect(page.locator("#visites-list")).toContainText("R17");
});

test("le logo ramene au tableau de bord et l aide est accessible", async ({ page }) => {
  await compteAvecRucher(page, "e2elogo");
  await ouvrirOnglet(page, "stats");
  await page.click("#brand-home");
  await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "dashboard");
  await ouvrirMenuProfil(page);
  await page.click("#btn-open-help");
  await expect(page.locator("#help-dialog")).toBeVisible();
  await expect(page.locator('#help-dialog a[href="./feedback.html"]')).toBeVisible();
});

// --- Lot L4 -------------------------------------------------------------------

async function ajouterStock(page, format, quantites) {
  const types = await page.evaluate(async () => (await (await fetch("/references/type-materiel", { credentials: "include" })).json()));
  for (const [libelle, quantite] of Object.entries(quantites)) {
    const type = types.find((item) => item.libelle.toLowerCase() === libelle);
    const statut = await page.evaluate(async ({ typeId, format, quantite }) => {
      const csrf = document.cookie.split("; ").find((item) => item.startsWith("bee_csrf="))?.split("=")[1];
      const reponse = await fetch("/materiel-atelier", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {}) },
        body: JSON.stringify({ ref_type_materiel_id: typeId, format_materiel: format, quantite_atelier: quantite, quantite_en_service: 0 }),
      });
      return reponse.status;
    }, { typeId: type.id, format, quantite });
    expect(statut).toBe(201);
  }
}

test("une ruche montee depuis le stock atelier consomme le stock", async ({ page }) => {
  await compteAvecRucher(page, "e2eruchestock");
  await ajouterStock(page, "dadant", { corps: 1, plancher: 1, toit: 1, cadre: 10 });
  await ouvrirOnglet(page, "atelier");
  await page.click("#btn-show-atelier-ruche-form");
  await page.fill("#atelier-ruche-identifiant", "PREP-01");
  await page.selectOption("#atelier-ruche-format", "dadant");
  await page.fill("#atelier-ruche-cadres", "10");
  await page.selectOption("#atelier-ruche-origine-materiel", "stock");
  await page.click("#atelier-ruche-submit");
  await expect(page.locator("#atelier-ruche-dialog")).toBeHidden();
  const tuile = page.locator("#atelier-stock-list .stock-card", { hasText: "Corps" }).filter({ hasText: "Dadant" });
  await expect(tuile).toContainText("0 range");
  await expect(tuile).toContainText("1 ruches atelier");
});

test("modifier un stock avec - retire sans creer de doublon", async ({ page }) => {
  // Retour beta : "Modifier" creait une nouvelle ligne, un retrait devenait un ajout.
  await compteAvecRucher(page, "e2estockedit");
  await ajouterStock(page, "dadant", { corps: 5 });
  // Stock ajoute par l'API : recharger pour que l'Atelier le voie.
  await page.reload();
  await expect(page.locator("#dashboard-card")).toBeVisible();
  await ouvrirOnglet(page, "atelier");
  const tuile = page.locator("#atelier-stock-list .stock-card", { hasText: "Corps" }).filter({ hasText: "Dadant" });
  await expect(tuile).toContainText("5 range");
  await tuile.locator(".stock-edit").click();
  await expect(page.locator("#stock-atelier-quantity")).toHaveValue("5");
  await page.click("#stock-quantity-minus");
  await page.click("#stock-quantity-minus");
  await expect(page.locator("#stock-atelier-quantity")).toHaveValue("3");
  await page.click('#stock-form button[type="submit"]');
  await expect(page.locator("#stock-dialog")).toBeHidden();
  await expect(tuile).toContainText("3 range");
  await expect(page.locator("#atelier-stock-list .stock-card", { hasText: "Corps" }).filter({ hasText: "Dadant" })).toHaveCount(1);
});

test("demonter une ruche remet ses elements en stock", async ({ page }) => {
  await compteAvecRucher(page, "e2edemontage");
  await ouvrirRucher(page, "Bois Joli");
  await page.locator('#ruches-list button:has-text("R17")').dispatchEvent("click");
  await page.click("#btn-ruche-move");
  await page.selectOption("#bulk-move-target", "demonter");
  page.once("dialog", (dialogue) => dialogue.accept());
  await page.click('#bulk-move-form button[type="submit"]');
  await expect(page.locator("#bulk-move-dialog")).toBeHidden();
  await expect(page.locator("#ruches-list")).not.toContainText("R17");
  await ouvrirOnglet(page, "atelier");
  await expect(page.locator("#atelier-stock-list .stock-card", { hasText: "Corps" }).first()).toContainText("1 range");
});

test("transvaser une colonie depuis la popup de visite", async ({ page }) => {
  await compteAvecRucher(page, "e2etransvasement");
  await ouvrirOnglet(page, "visites");
  await page.click("#btn-new-visit");
  await page.selectOption("#visit-create-rucher", { label: "Bois Joli" });
  await page.selectOption("#visit-create-ruche", { label: "E22" });
  await page.click("#btn-visit-transvasement");
  await expect(page.locator("#transvasement-dialog")).toBeVisible();
  await page.selectOption("#transvasement-format", "dadant");
  await page.selectOption("#transvasement-provenance", "achat");
  await page.fill("#transvasement-cadres-transferes", "6");
  await page.fill("#transvasement-cadres-ajoutes", "4");
  await page.click('#transvasement-form button[type="submit"]');
  await expect(page.locator("#transvasement-dialog")).toBeHidden();
  await expect(page.locator("#visit-transvasement-summary")).toContainText("Dadant");
  await page.click('#visite-form button[type="submit"]');
  await expect(page.locator("#visit-create-dialog")).toBeHidden();
  const ruche = await page.evaluate(async () => (await (await fetch("/ruches", { credentials: "include" })).json()).find((item) => item.identifiant_personnalise === "E22"));
  expect(ruche.format_ruche).toBe("dadant");
  expect(ruche.nombre_cadres).toBe(10);
});

// --- Lot L6 -------------------------------------------------------------------

async function peuplerStatistiques(page) {
  return page.evaluate(async () => {
    const post = (url, body) => fetch(url, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json());
    const ruches = await (await fetch("/ruches", { credentials: "include" })).json();
    const r17 = ruches.find((item) => item.identifiant_personnalise === "R17");
    const annee = new Date().getFullYear();
    for (const [mois, total, couvain, note] of [["03", 8, 2, 3], ["05", 10, 6, 4], ["07", 10, 7, 5]]) {
      await post("/visites", { ruche_id: r17.id, visite_rucher_id: null, date_visite: `${annee}-${mois}-10T09:00:00Z`, nombre_cadres_total: total, nombre_cadres_couvain: couvain, note_ruche: note, statut_validation: "valide" });
    }
    await post("/recoltes", { ruche_id: r17.id, visite_ruche_id: null, poids_miel_kg: 18 });
    await post(`/ruches/${r17.id}/reines`, { date_mise_en_place: `${annee - 1}-05-01T00:00:00Z`, origine: "remerage", race: "Buckfast", provenance: "Elevage personnel" });
  });
}

test("Statistiques affiche la fiche du rucher puis celle de la ruche", async ({ page }) => {
  await compteAvecRucher(page, "e2efiches");
  await peuplerStatistiques(page);
  await ouvrirOnglet(page, "stats");
  await expect(page.locator(".stats-breakdowns")).toBeVisible();
  await expect(page.locator("#stats-honey-by-ruche")).toContainText("E22");
  await page.click("#stats-scope-rucher-menu summary");
  await page.click('#stats-scope-rucher-menu .scope-menu-options button:has-text("Bois Joli")');
  await expect(page.locator("#stats-rucher-sheet")).toBeVisible();
  await expect(page.locator(".stats-breakdowns")).toBeHidden();
  await expect(page.locator("#stats-rucher-sheet")).toContainText("18.0 kg");
  await expect(page.locator('#stats-rucher-sheet [data-bars="honey"]')).toContainText("0 kg");
  await page.fill("#stats-search", "R17");
  await page.press("#stats-search", "Enter");
  await expect(page.locator("#stats-hive-sheet")).toBeVisible();
  await expect(page.locator("#stats-rucher-sheet")).toBeHidden();
  await expect(page.locator("#stats-hive-sheet")).toContainText("Buckfast");
  await expect(page.locator("#stats-hive-sheet svg.frames-chart circle")).toHaveCount(6);
  if (process.env.CAPTURE) await page.screenshot({ path: "artifacts/capture/fiche-ruche-desktop.png", fullPage: true });
});
