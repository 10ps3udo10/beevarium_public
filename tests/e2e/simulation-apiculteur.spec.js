// Simulation d'usage par un apiculteur professionnel (plan : docs/05-qualite-et-tests.md).
// Lancement : bash scripts/linux/simulation_apiculteur.sh http://localhost:8000
// Jamais sur la beta. Les effets metier sont verifies par l'API (moins couteux
// que la lecture du DOM) ; captures limitees aux ecrans cles, en 1440 et 390 px.
const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const BASE_URL = process.env.BEEVARIUM_APP_URL || "http://127.0.0.1:18001";
const MOT_DE_PASSE = "motdepasse123";
const SORTIE = path.join(process.cwd(), "artifacts", "simulation");
const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };
const ANNEE = new Date().getFullYear();

const journal = [];
const note = (scenario, constat) => journal.push({ scenario, constat });

test.describe.configure({ mode: "serial" });
test.setTimeout(6 * 60 * 1000);

test.afterAll(() => {
  fs.mkdirSync(SORTIE, { recursive: true });
  const lignes = ["# Simulation apiculteur professionnel", "", `Date : ${new Date().toISOString()}`, `Cible : ${BASE_URL}`, ""];
  for (const { scenario, constat } of journal) lignes.push(`- **${scenario}** : ${constat}`);
  fs.writeFileSync(path.join(SORTIE, "journal.md"), `${lignes.join("\n")}\n`);
});

async function api(page, method, url, data) {
  const reponse = await page.request.fetch(`${BASE_URL}${url}`, { method, data });
  const corps = reponse.status() === 204 ? null : await reponse.json().catch(() => null);
  return { status: reponse.status(), corps };
}

async function capture(page, nom) {
  fs.mkdirSync(SORTIE, { recursive: true });
  await page.screenshot({ path: path.join(SORTIE, `${nom}.png`), fullPage: false });
}

async function onglet(page, nom) {
  await page.click("#btn-open-nav");
  await page.click(`button[data-tab="${nom}"]`);
  await page.mouse.move((page.viewportSize()?.width || 1280) - 20, 400);
  await expect(page.locator("#main-nav")).not.toHaveClass(/is-open/);
}

async function stock(page) {
  const lignes = (await api(page, "GET", "/materiel-atelier/stats/stock-synthetique-par-type")).corps;
  const parCle = {};
  for (const ligne of lignes) parCle[`${ligne.libelle_type_materiel.toLowerCase()}|${ligne.format_materiel}`] = ligne;
  return parCle;
}

async function ruches(page) {
  return (await api(page, "GET", "/ruches")).corps;
}

test("journee d'un apiculteur professionnel @simulation", async ({ page, context }) => {
  const erreurs = [];
  page.on("pageerror", (erreur) => erreurs.push(`pageerror ${erreur.message}`));
  page.on("console", (message) => { if (message.type() === "error" && !/40[13]|Failed to load resource/.test(message.text())) erreurs.push(`console ${message.text()}`); });
  await page.setViewportSize(DESKTOP);

  const email = `simulation${Date.now()}@example.com`;
  await test.step("Compte et connexion", async () => {
    const inscription = await page.request.post(`${BASE_URL}/auth/register`, { data: { email, prenom: "Simon", password: MOT_DE_PASSE, is_premium: true } });
    expect(inscription.status()).toBe(201);
    await page.context().clearCookies();
    await page.goto(`${BASE_URL}/app/`);
    await page.fill("#email", email);
    await page.fill("#password", MOT_DE_PASSE);
    const debut = Date.now();
    await page.click("#btn-login");
    await expect(page.locator("#dashboard-card")).toBeVisible();
    note("Connexion", `tableau de bord affiche en ${Date.now() - debut} ms`);
  });

  let types;
  await test.step("S1 Installation : ruchers, stock, ruches depuis le stock et achetees", async () => {
    await onglet(page, "ruchers");
    for (const [nom, biotope] of [["Les Granges", "bocage"], ["Bois Joli", "foret"]]) {
      await page.click("#btn-show-rucher-form");
      await page.fill("#create-rucher-name", nom);
      await page.selectOption("#create-rucher-type", biotope);
      await page.click('#rucher-create-form button[type="submit"]');
      await expect(page.locator("#ruchers-list")).toContainText(nom);
    }
    types = Object.fromEntries((await api(page, "GET", "/references/type-materiel")).corps.map((type) => [type.libelle.toLowerCase(), type.id]));
    for (const [format, quantites] of [["dadant", { corps: 3, plancher: 3, toit: 3, cadre: 30, partition: 1 }], ["ruchette", { corps: 2, plancher: 2, toit: 2, cadre: 12 }]]) {
      for (const [libelle, quantite] of Object.entries(quantites)) {
        const ajout = await api(page, "POST", "/materiel-atelier", { ref_type_materiel_id: types[libelle], format_materiel: format, quantite_atelier: quantite, quantite_en_service: 0 });
        expect(ajout.status).toBe(201);
      }
    }
    await page.reload();
    await onglet(page, "ruchers");
    await page.locator('#ruchers-list button:has-text("Les Granges")').dispatchEvent("click");
    await page.click("#btn-show-ruche-form");
    await page.fill("#ruche-identifiant", "G01");
    await page.selectOption("#ruche-format", "dadant");
    await page.fill("#ruche-cadres", "10");
    await page.selectOption("#ruche-origine-materiel", "stock");
    await page.click('#ruche-form button[type="submit"]');
    await expect(page.locator("#ruches-list")).toContainText("G01");
    const apres = await stock(page);
    expect(apres["corps|dadant"].quantite_atelier_totale).toBe(2);
    expect(apres["cadre|dadant"].quantite_atelier_totale).toBe(20);
    note("S1", "ruche G01 montee depuis le stock : corps 3 -> 2, cadres 30 -> 20 ; materiel en service = 1 corps");

    // Le reste du cheptel est saisi par l'API : un pro ne cree pas 20 ruches a la main pour un test.
    const rucherIds = Object.fromEntries((await api(page, "GET", "/ruchers")).corps.map((rucher) => [rucher.nom, rucher.id]));
    for (let numero = 2; numero <= 12; numero += 1) {
      const creation = await api(page, "POST", "/ruches", { identifiant_personnalise: `G${String(numero).padStart(2, "0")}`, rucher_id: rucherIds["Les Granges"], is_at_atelier: false, format_ruche: "dadant", nombre_cadres: 10, reine_race: "Buckfast", reine_annee_marquage: numero % 4 === 0 ? ANNEE - 3 : ANNEE - 1 });
      expect(creation.status).toBe(201);
    }
    for (const id of ["B01", "B02", "B03", "E22"]) {
      const creation = await api(page, "POST", "/ruches", { identifiant_personnalise: id, rucher_id: rucherIds["Bois Joli"], is_at_atelier: false, format_ruche: id === "E22" ? "ruchette" : "dadant", nombre_cadres: id === "E22" ? 6 : 10 });
      expect(creation.status).toBe(201);
    }
    const achat = await api(page, "POST", "/ruches", { identifiant_personnalise: "PREP-D1", rucher_id: null, is_at_atelier: true, format_ruche: "dadant", nombre_cadres: 10, origine_materiel: "achat" });
    expect(achat.status).toBe(201);
    const stockFinal = await stock(page);
    expect(stockFinal["corps|dadant"].quantite_ruches_atelier_calculee).toBe(1);
    note("S1", `cheptel de ${(await ruches(page)).length} ruches ; ruche achetee PREP-D1 rangee montee a l'atelier comptee dans le total (colonne ruches atelier)`);
    await page.reload();
    await capture(page, "s1-tableau-de-bord-1440");
  });

  await test.step("S2 Tournee de visites sur telephone, dont hors ligne", async () => {
    await page.setViewportSize(MOBILE);
    await onglet(page, "visites");
    await capture(page, "s2-visites-390");
    const debordement = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(debordement).toBe(false);
    for (const [ruche, total, couvain, noteRuche] of [["B01", 10, 6, 4], ["B02", 10, 2, 2]]) {
      await page.click("#btn-new-visit");
      await page.selectOption("#visit-create-rucher", { label: "Bois Joli" });
      await page.selectOption("#visit-create-ruche", { label: ruche });
      await page.fill("#visite-note", String(noteRuche));
      await page.fill("#visite-cadres-total", String(total));
      await page.fill("#visite-cadres-couvain", String(couvain));
      await page.selectOption("#visite-reine-vue", noteRuche > 2 ? "true" : "false");
      await page.click('#visite-form button[type="submit"]');
      await expect(page.locator("#visit-create-dialog")).toBeHidden();
    }
    // Hors ligne : visite de E22 avec tag et transvasement ruchette -> Dadant achete.
    await page.click("#btn-new-visit");
    await page.selectOption("#visit-create-rucher", { label: "Bois Joli" });
    await page.selectOption("#visit-create-ruche", { label: "E22" });
    await context.setOffline(true);
    const saisie = Date.now();
    await page.fill("#visite-note", "4");
    await page.click("#btn-visit-tags");
    await page.locator('#tag-dialog-catalog button.tag-quick:has-text("a nourrir")').click();
    await page.click("#btn-add-ruche-tags");
    await page.click("#btn-visit-transvasement");
    await page.selectOption("#transvasement-format", "dadant");
    await page.selectOption("#transvasement-provenance", "achat");
    await page.fill("#transvasement-cadres-transferes", "6");
    await page.fill("#transvasement-cadres-ajoutes", "4");
    await page.click('#transvasement-form button[type="submit"]');
    await page.click('#visite-form button[type="submit"]');
    await expect(page.locator("#visit-create-dialog")).toBeHidden();
    await page.waitForTimeout(2000);
    await context.setOffline(false);
    await expect.poll(async () => (await ruches(page)).find((ruche) => ruche.identifiant_personnalise === "E22")?.format_ruche, { timeout: 20000 }).toBe("dadant");
    const e22 = (await ruches(page)).find((ruche) => ruche.identifiant_personnalise === "E22");
    const visitesE22 = (await api(page, "GET", `/visites?ruche_id=${e22.id}`)).corps;
    expect(visitesE22).toHaveLength(1);
    const ecart = Math.abs(new Date(visitesE22[0].date_visite).getTime() - saisie);
    expect(ecart).toBeLessThan(60000);
    expect(e22.tags.map((tag) => tag.libelle)).toContain("a nourrir");
    note("S2", `visite hors ligne de E22 synchronisee une seule fois, heure de saisie conservee (ecart ${Math.round(ecart / 1000)} s), tag et transvasement ruchette -> Dadant appliques`);
  });

  await test.step("S3 Recoltes par ruche et par rucher entier", async () => {
    await page.click("#btn-new-harvest");
    await page.selectOption("#harvest-rucher", { label: "Bois Joli" });
    await page.selectOption("#harvest-ruche", { label: "B01" });
    await page.fill("#harvest-weight", "18");
    await page.click('#harvest-form button[type="submit"]');
    await expect(page.locator("#harvest-dialog")).toBeHidden();
    await page.click("#btn-new-harvest");
    await page.selectOption("#harvest-rucher", { label: "Les Granges" });
    await page.selectOption("#harvest-ruche", "");
    await page.fill("#harvest-weight", "120");
    let alerte = "";
    page.once("dialog", (dialogue) => { alerte = dialogue.message(); dialogue.accept(); });
    await page.click('#harvest-form button[type="submit"]');
    await expect(page.locator("#harvest-dialog")).toBeHidden();
    expect(alerte).toContain("parts egales");
    const parRucher = (await api(page, "GET", `/recoltes/stats/par-rucher?start_date=${ANNEE}-01-01&end_date=${ANNEE}-12-31`)).corps;
    const granges = parRucher.find((item) => item.nom_rucher === "Les Granges");
    expect(granges.poids_total_kg).toBeCloseTo(120, 1);
    note("S3", `120 kg repartis sur ${granges.total_recoltes} ruches des Granges (${(120 / granges.total_recoltes).toFixed(1)} kg chacune) : la repartition egale masque les ecarts reels entre ruches`);
  });

  await test.step("S4 Remplacement de reine depuis la fiche ruche", async () => {
    await page.setViewportSize(DESKTOP);
    await onglet(page, "ruchers");
    await page.locator('#ruchers-list button:has-text("Les Granges")').dispatchEvent("click");
    await page.locator('#ruches-list button:has-text("G04")').dispatchEvent("click");
    await page.click("#btn-ruche-queen");
    await page.fill("#queen-date", `${ANNEE}-06-15`);
    await page.selectOption("#queen-origin", "apport_reine_fecondee");
    await page.selectOption("#queen-race", "Carnica");
    await page.click('#queen-form button[type="submit"]');
    await expect(page.locator("#ruches-list")).toContainText("Carnica");
    const g04 = (await ruches(page)).find((ruche) => ruche.identifiant_personnalise === "G04");
    const reines = (await api(page, "GET", `/ruches/${g04.id}/reines`)).corps;
    expect(reines.filter((reine) => reine.statut === "active")).toHaveLength(1);
    note("S4", `G04 : ancienne reine terminee, Carnica active, colonne Reine a jour ; historique de ${reines.length} reines`);
  });

  await test.step("S5 Transhumance et demontage", async () => {
    await page.locator('#ruches-list button:has-text("G11")').dispatchEvent("click");
    await page.click("#btn-ruche-move");
    await page.selectOption("#bulk-move-target", { label: "Bois Joli" });
    await page.click('#bulk-move-form button[type="submit"]');
    await expect(page.locator("#bulk-move-dialog")).toBeHidden();
    const avant = await stock(page);
    await page.locator('#ruches-list button:has-text("G12")').dispatchEvent("click");
    await page.click("#btn-ruche-move");
    await page.selectOption("#bulk-move-target", "demonter");
    page.once("dialog", (dialogue) => dialogue.accept());
    await page.click('#bulk-move-form button[type="submit"]');
    await expect(page.locator("#bulk-move-dialog")).toBeHidden();
    const apres = await stock(page);
    expect(apres["corps|dadant"].quantite_atelier_totale).toBe(avant["corps|dadant"].quantite_atelier_totale + 1);
    expect(apres["cadre|dadant"].quantite_atelier_totale).toBe(avant["cadre|dadant"].quantite_atelier_totale + 10);
    expect((await ruches(page)).some((ruche) => ruche.identifiant_personnalise === "G12")).toBe(false);
    note("S5", "G11 transhumee vers Bois Joli ; G12 demontee : +1 corps, +10 cadres en stock, ruche sortie de la liste, historique conserve");
  });

  await test.step("S6 Modification puis suppression d'un rucher", async () => {
    await page.click("#btn-show-rucher-form");
    await page.fill("#create-rucher-name", "Rucher provisoire");
    await page.click('#rucher-create-form button[type="submit"]');
    await page.locator('#ruchers-list button:has-text("Rucher provisoire")').dispatchEvent("click");
    await page.click("#btn-edit-rucher");
    await page.fill("#edit-rucher-latitude", "45.75");
    await page.fill("#edit-rucher-longitude", "4.85");
    await page.click('#rucher-edit-form button[type="submit"]');
    await page.click("#btn-edit-rucher");
    await page.click("#btn-delete-rucher");
    await expect(page.locator("#rucher-delete-confirm-step")).toBeVisible();
    await page.click("#btn-rucher-delete-confirm");
    await expect(page.locator("#ruchers-list")).not.toContainText("Rucher provisoire");
    note("S6", "rucher vide modifie (coordonnees) puis supprime avec simple confirmation");
  });

  await test.step("S7 Statistiques : saison, rucher, ruche, saison derniere", async () => {
    await onglet(page, "stats");
    await expect(page.locator("#stats-honey")).toContainText("138.0 kg");
    await page.fill("#stats-search", "B02");
    await page.press("#stats-search", "Enter");
    await expect(page.locator("#stats-hive-sheet")).toBeVisible();
    await expect(page.locator("#stats-hive-sheet")).toContainText("Note faible");
    await capture(page, "s7-fiche-ruche-1440");
    await page.selectOption("#period-window", "last-season");
    await expect(page.locator("#stats-year-label")).toHaveText(`Saison ${ANNEE - 1}`);
    await expect(page.locator("#stats-honey")).toHaveText("0.0 kg");
    note("S7", "miel saison = 138 kg (18 + 120), saison derniere = 0 kg ; fiche B02 signale la note faible");
  });

  await test.step("S8 Ruches a surveiller", async () => {
    await page.selectOption("#period-window", "season");
    await onglet(page, "dashboard");
    const cheptel = (await api(page, "GET", "/statistiques/cheptel")).corps;
    const motifs = cheptel.ruches_a_surveiller.map((entree) => `${entree.identifiant_personnalise} (${entree.motifs.join(", ")})`);
    expect(cheptel.ruches_a_surveiller.some((entree) => entree.identifiant_personnalise === "B02")).toBe(true);
    note("S8", `${cheptel.ruches_a_surveiller.length} ruches a surveiller : ${motifs.slice(0, 6).join(" ; ")}`);
  });

  await test.step("S9 Navigation, aide, rendu mobile", async () => {
    await onglet(page, "visites");
    await page.reload();
    await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "visites");
    await page.click("#brand-home");
    await expect(page.locator("#dashboard-card")).toHaveAttribute("data-active-tab", "dashboard");
    await page.setViewportSize(MOBILE);
    await capture(page, "s9-tableau-de-bord-390");
    await onglet(page, "atelier");
    await capture(page, "s9-atelier-390");
    const debordements = await page.evaluate(() => [...document.querySelectorAll("[data-panel~='atelier'] *")]
      .filter((element) => element.offsetParent && element.getBoundingClientRect().right > document.documentElement.clientWidth + 1).length);
    note("S9", `actualisation et logo conformes ; Atelier 390 px : ${debordements} element(s) en debordement`);
  });

  note("Erreurs", erreurs.length ? erreurs.slice(0, 10).join(" | ") : "aucune erreur JavaScript ni console");
  expect(erreurs).toEqual([]);
});
