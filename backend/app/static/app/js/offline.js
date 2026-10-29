import { api } from "./api.js";
import { dom } from "./dom.js";
import { state } from "./state.js";
import { setHint, setStatus } from "./utils.js";

export const SYNC_DB_NAME = "beevarium-offline";
export const SYNC_STORE_NAME = "sync_operations";

export function openSyncDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SYNC_DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(SYNC_STORE_NAME, { keyPath: "operation_id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function queueOfflineVisit(payload) {
  const db = await openSyncDb();
  const operation = { operation_id: crypto.randomUUID(), entity_type: "visite_ruche", operation: "create", payload, created_at: new Date().toISOString(), status: "pending" };
  await new Promise((resolve, reject) => {
    const request = db.transaction(SYNC_STORE_NAME, "readwrite").objectStore(SYNC_STORE_NAME).add(operation);
    request.onsuccess = resolve;
    request.onerror = () => reject(request.error);
  });
  db.close();
  return operation;
}

export async function listOfflineOperations() {
  const db = await openSyncDb();
  const operations = await new Promise((resolve, reject) => {
    const request = db.transaction(SYNC_STORE_NAME, "readonly").objectStore(SYNC_STORE_NAME).getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return operations;
}

export async function removeOfflineOperation(operationId) {
  const db = await openSyncDb();
  await new Promise((resolve, reject) => {
    const request = db.transaction(SYNC_STORE_NAME, "readwrite").objectStore(SYNC_STORE_NAME).delete(operationId);
    request.onsuccess = resolve;
    request.onerror = () => reject(request.error);
  });
  db.close();
}

export async function clearOfflineData() {
  const db = await openSyncDb();
  db.close();
  await new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(SYNC_DB_NAME);
    request.onsuccess = resolve;
    request.onblocked = () => reject(new Error("Fermez les autres onglets Beevarium pour effacer les donnees locales."));
    request.onerror = () => reject(request.error);
  });
}

export async function updateOfflineOperation(operation) {
  const db = await openSyncDb();
  await new Promise((resolve, reject) => {
    const request = db.transaction(SYNC_STORE_NAME, "readwrite").objectStore(SYNC_STORE_NAME).put(operation);
    request.onsuccess = resolve;
    request.onerror = () => reject(request.error);
  });
  db.close();
}

export function renderSyncConflict(operation) {
  if (!operation) {
    dom.syncConflictCard.hidden = true;
    return;
  }
  const local = operation.payload || {};
  const server = operation.server_visit || {};
  dom.syncConflictCard.hidden = false;
  dom.syncConflictSummary.textContent = "La visite a ete modifiee sur le serveur depuis votre saisie locale. Choisissez explicitement la version a conserver.";
  dom.syncConflictDetails.innerHTML = [
    ["Saisie locale", `note ${local.note_ruche ?? "-"}, ${local.nombre_cadres_couvain ?? "-"}/${local.nombre_cadres_total ?? "-"} cadres`],
    ["Serveur", `note ${server.note_ruche ?? "-"}, ${server.nombre_cadres_couvain ?? "-"}/${server.nombre_cadres_total ?? "-"} cadres`],
  ].map(([label, value]) => `<div><strong>${label}</strong>${value}</div>`).join("");
  dom.syncConflictCard.dataset.operationId = operation.operation_id;
}

export async function showFirstSyncConflict() {
  const operations = await listOfflineOperations().catch(() => []);
  renderSyncConflict(operations.find((operation) => operation.status === "conflict"));
}

export async function getOfflineOperation(operationId) {
  const operations = await listOfflineOperations();
  return operations.find((operation) => operation.operation_id === operationId);
}

export async function keepServerConflict() {
  const operationId = dom.syncConflictCard.dataset.operationId;
  if (!operationId) return;
  await removeOfflineOperation(operationId);
  state.mergeOperationId = null;
  await showFirstSyncConflict();
  await updateSyncStatus("online");
  setStatus("Version serveur conservee.");
}

export async function keepLocalConflict() {
  const operationId = dom.syncConflictCard.dataset.operationId;
  const operation = operationId ? await getOfflineOperation(operationId) : null;
  if (!operation || !operation.server_visit?.updated_at) return;
  operation.status = "pending";
  operation.client_base_updated_at = operation.server_visit.updated_at;
  await updateOfflineOperation(operation);
  await syncOfflineVisits();
}

export async function mergeConflictManually() {
  const operationId = dom.syncConflictCard.dataset.operationId;
  const operation = operationId ? await getOfflineOperation(operationId) : null;
  if (!operation) return;
  const payload = operation.payload;
  state.mergeOperationId = operationId;
  dom.visiteReineVue.value = payload.reine_vue == null ? "" : String(payload.reine_vue);
  dom.visitePonte.value = payload.presence_ponte == null ? "" : String(payload.presence_ponte);
  dom.visiteCouvain.value = payload.etat_couvain || "";
  dom.visiteReserves.value = payload.reserves_nourriture || "";
  dom.visiteNote.value = payload.note_ruche ?? "";
  dom.visiteCadresCouvain.value = payload.nombre_cadres_couvain ?? "";
  dom.visiteCadresTotal.value = payload.nombre_cadres_total ?? "";
  dom.syncConflictCard.hidden = true;
  setHint(dom.visiteFormHint, "Fusion manuelle: ajuste les champs puis enregistre la visite.", "ok");
}

export async function updateSyncStatus(mode = "online") {
  const operations = await listOfflineOperations().catch(() => []);
  dom.syncStatus.className = `sync-status ${mode === "offline" ? "offline" : mode === "syncing" ? "syncing" : ""}`;
  dom.syncStatus.textContent = mode === "offline"
    ? `Hors ligne - saisie locale. A synchroniser: ${operations.length}.`
    : mode === "syncing"
      ? `Synchronisation en cours. En attente: ${operations.length}.`
      : operations.length
        ? `En ligne - a synchroniser: ${operations.length}.`
        : "Connexion en ligne.";
}

// Une seule synchronisation a la fois : l'evenement `online` peut arriver
// pendant une synchronisation deja lancee et renverrait les memes visites.
export let offlineSyncInFlight = null;

export function syncOfflineVisits() {
  if (!offlineSyncInFlight) {
    offlineSyncInFlight = runOfflineSync().finally(() => { offlineSyncInFlight = null; });
  }
  return offlineSyncInFlight;
}

export async function runOfflineSync() {
  if (!navigator.onLine || !state.authenticated) {
    await updateSyncStatus(navigator.onLine ? "online" : "offline");
    return;
  }
  const operations = await listOfflineOperations().catch(() => []);
  if (!operations.length) {
    await updateSyncStatus("online");
    return;
  }
  await updateSyncStatus("syncing");
  for (const operation of operations.sort((left, right) => left.created_at.localeCompare(right.created_at))) {
    try {
      const path = operation.operation === "update" ? `/visites/${operation.entity_id}` : "/visites";
      const method = operation.operation === "update" ? "PATCH" : "POST";
      const headers = { "Idempotency-Key": operation.operation_id, "X-Sync-Protocol": "1" };
      if (operation.client_base_updated_at) headers["X-Client-Base-Updated-At"] = operation.client_base_updated_at;
      const synced = await api(path, { method, body: operation.payload, headers });
      await removeOfflineOperation(operation.operation_id);
      if (synced?.avertissements?.length) setStatus(`Visite synchronisee. ${synced.avertissements.join(" ")}`);
    } catch (error) {
      if (error.status === 409) {
        operation.status = "conflict";
        try {
          operation.server_visit = await api(`/visites/${operation.entity_id}`);
        } catch {
          operation.server_visit = null;
        }
        await updateOfflineOperation(operation);
        await showFirstSyncConflict();
      }
      setStatus(`Synchronisation en attente: ${error.message}`);
      break;
    }
  }
  await updateSyncStatus("online");
}
