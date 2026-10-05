import re
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.ownership import get_owned_ruche
from app.routers.visites import _build_visite_response, _replace_visit_children, _validate_owned_visite_rucher, _validate_visite_has_content
from app.security import get_current_user


router = APIRouter(prefix="/ia-vocale", tags=["ia-vocale"])


@router.post("/transcrire-audio", response_model=schemas.IaVocaleTranscriptionResponse)
async def transcribe_audio_ia_vocale(
    audio_file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fonction reservee aux comptes premium")

    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le fichier doit etre un audio")

    max_size_bytes = min(10 * 1024 * 1024, settings.max_request_body_bytes)
    total_size = 0
    while chunk := await audio_file.read(64 * 1024):
        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Fichier audio trop volumineux")

    if total_size == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le fichier audio est vide")

    file_ext = "wav"
    if audio_file.filename and "." in audio_file.filename:
        file_ext = audio_file.filename.rsplit(".", 1)[1].lower() or "wav"
    audio_reference = f"audio/{uuid.uuid4()}.{file_ext}"

    transcription = (
        "reine vue, ponte presente, etat couvain normal, couvain 4 cadres, "
        "reserves correct, agressivite 2, note 4"
    )

    # Estimation simple en attendant l integration d un moteur de transcription reel.
    duration_seconds_estimate = round(max(1.0, total_size / 16000.0), 2)

    return schemas.IaVocaleTranscriptionResponse(
        audio_reference=audio_reference,
        transcription=transcription,
        detected_language="fr",
        duration_seconds_estimate=duration_seconds_estimate,
    )


@router.get("/brouillons", response_model=list[schemas.VisiteRucheResponse])
def list_ia_vocale_drafts(
    ruche_id: UUID | None = None,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fonction reservee aux comptes premium")

    if limit <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La limite doit etre positive")

    query = (
        db.query(models.VisiteRuche)
        .options(selectinload(models.VisiteRuche.actions))
        .join(models.Ruche, models.VisiteRuche.ruche_id == models.Ruche.id)
        .filter(
            models.Ruche.user_id == current_user.id,
            models.VisiteRuche.source_saisie == "ia_vocale",
            models.VisiteRuche.statut_validation == "brouillon",
        )
    )

    if ruche_id is not None:
        get_owned_ruche(db, ruche_id, current_user.id)
        query = query.filter(models.VisiteRuche.ruche_id == ruche_id)

    visites = query.order_by(models.VisiteRuche.date_visite.desc()).limit(min(limit, 200)).all()
    return [_build_visite_response(db, visite) for visite in visites]


@router.delete("/brouillons/{visite_id}", status_code=status.HTTP_204_NO_CONTENT)
def reject_ia_vocale_draft(
    visite_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fonction reservee aux comptes premium")
    visite = db.get(models.VisiteRuche, visite_id)
    if visite is None or visite.source_saisie != "ia_vocale" or visite.statut_validation != "brouillon":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brouillon IA introuvable")
    get_owned_ruche(db, visite.ruche_id, current_user.id)
    db.delete(visite)
    db.commit()
    return None


def _extract_visite_from_transcription(transcription: str) -> tuple[dict[str, object], list[str], float]:
    normalized = transcription.strip().lower()
    extracted: dict[str, object] = {}
    missing_fields: list[str] = []
    confidence = 0.45

    if "reine absente" in normalized or "pas de reine" in normalized:
        extracted["reine_vue"] = False
        confidence += 0.15
    elif "reine vue" in normalized or "reine presente" in normalized or "reine présente" in normalized:
        extracted["reine_vue"] = True
        confidence += 0.15
    else:
        missing_fields.append("reine_vue")

    if "pas de ponte" in normalized or "absence de ponte" in normalized:
        extracted["presence_ponte"] = False
        confidence += 0.15
    elif "ponte" in normalized:
        extracted["presence_ponte"] = True
        confidence += 0.15
    else:
        missing_fields.append("presence_ponte")

    for label in ("faible", "normal", "excellent"):
        if label in normalized:
            extracted["etat_couvain"] = label
            confidence += 0.1
            break
    else:
        missing_fields.append("etat_couvain")

    if "reserves critique" in normalized or "reserves critiques" in normalized:
        extracted["reserves_nourriture"] = "critique"
        confidence += 0.1
    elif "reserves correct" in normalized or "reserves correctes" in normalized:
        extracted["reserves_nourriture"] = "correct"
        confidence += 0.1
    elif "reserves abondant" in normalized or "reserves abondantes" in normalized:
        extracted["reserves_nourriture"] = "abondant"
        confidence += 0.1
    else:
        missing_fields.append("reserves_nourriture")

    match_agressivite = re.search(r"agressivit[eé]\s*(\d)", normalized)
    if match_agressivite:
        extracted["agressivite"] = int(match_agressivite.group(1))
        confidence += 0.1
    else:
        missing_fields.append("agressivite")

    match_note = re.search(r"note\s*(\d)", normalized)
    if match_note:
        extracted["note_ruche"] = int(match_note.group(1))
        confidence += 0.1
    else:
        missing_fields.append("note_ruche")

    match_cadres = re.search(r"(\d+)\s*cadres?", normalized)
    if match_cadres:
        extracted["nombre_cadres_total"] = int(match_cadres.group(1))
        confidence += 0.08
    else:
        missing_fields.append("nombre_cadres_total")

    match_couvain = re.search(r"couvain\s*(\d+)\s*cadres?", normalized)
    if match_couvain:
        extracted["nombre_cadres_couvain"] = int(match_couvain.group(1))
        confidence += 0.08
    else:
        missing_fields.append("nombre_cadres_couvain")

    hausses_mouvements = []
    match_hausses = re.search(r"(\d+)\s*hausses?", normalized)
    if match_hausses:
        hausses_mouvements.append({"quantite_delta": int(match_hausses.group(1)), "note": "Extraction IA vocale"})
        confidence += 0.05

    extracted["source_saisie"] = "ia_vocale"
    extracted["statut_validation"] = "valide" if confidence >= 0.8 and not missing_fields else "brouillon"
    extracted["action_ids"] = []
    extracted["interventions"] = []
    extracted["mouvements_cadres"] = []
    extracted["mouvements_hausses"] = hausses_mouvements

    if len(missing_fields) < 7:
        confidence = min(confidence, 0.95)

    return extracted, sorted(set(missing_fields)), round(min(confidence, 0.99), 2)


def _is_complete_enough_for_validation(extracted_visit: dict[str, object]) -> bool:
    required_keys = (
        "reine_vue",
        "presence_ponte",
        "etat_couvain",
        "reserves_nourriture",
        "agressivite",
        "note_ruche",
    )
    has_core_observations = all(key in extracted_visit for key in required_keys)
    has_measurement = "nombre_cadres_total" in extracted_visit or "nombre_cadres_couvain" in extracted_visit
    return has_core_observations and has_measurement


@router.post("/analyser-visite", response_model=schemas.IaVocaleAnalyseResponse)
def analyse_visite_ia_vocale(
    payload: schemas.IaVocaleAnalyseRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fonction reservee aux comptes premium")

    get_owned_ruche(db, payload.ruche_id, current_user.id)
    _validate_owned_visite_rucher(db, payload.visite_rucher_id, current_user.id)

    extracted_visit, missing_fields, confidence = _extract_visite_from_transcription(payload.transcription)
    statut_validation = "valide" if _is_complete_enough_for_validation(extracted_visit) else "brouillon"
    extracted_visit["statut_validation"] = statut_validation

    saved_visite = None
    if payload.save_as_draft:
        visite_payload = schemas.VisiteRucheCreate(
            ruche_id=payload.ruche_id,
            visite_rucher_id=payload.visite_rucher_id,
            reine_vue=extracted_visit.get("reine_vue"),
            presence_ponte=extracted_visit.get("presence_ponte"),
            etat_couvain=extracted_visit.get("etat_couvain"),
            nombre_cadres_couvain=extracted_visit.get("nombre_cadres_couvain"),
            reserves_nourriture=extracted_visit.get("reserves_nourriture"),
            agressivite=extracted_visit.get("agressivite"),
            note_ruche=extracted_visit.get("note_ruche"),
            nombre_cadres_total=extracted_visit.get("nombre_cadres_total"),
            source_saisie="ia_vocale",
            statut_validation=statut_validation,
            action_ids=[],
            interventions=[],
            mouvements_cadres=[],
            mouvements_hausses=[schemas.MouvementHausseCreate(**item) for item in extracted_visit.get("mouvements_hausses", [])],
        )
        _validate_visite_has_content(visite_payload)

        visite = models.VisiteRuche(
            ruche_id=payload.ruche_id,
            visite_rucher_id=payload.visite_rucher_id,
            reine_vue=visite_payload.reine_vue,
            presence_ponte=visite_payload.presence_ponte,
            etat_couvain=visite_payload.etat_couvain,
            nombre_cadres_couvain=visite_payload.nombre_cadres_couvain,
            reserves_nourriture=visite_payload.reserves_nourriture,
            agressivite=visite_payload.agressivite,
            note_ruche=visite_payload.note_ruche,
            nombre_cadres_total=visite_payload.nombre_cadres_total,
            source_saisie=visite_payload.source_saisie,
            statut_validation=visite_payload.statut_validation,
        )
        db.add(visite)
        db.flush()
        _replace_visit_children(db, visite, visite_payload)
        db.commit()
        db.refresh(visite)
        saved_visite = db.query(models.VisiteRuche).filter(models.VisiteRuche.id == visite.id).one()
        saved_visite = schemas.VisiteRucheResponse.model_validate(saved_visite)

    return schemas.IaVocaleAnalyseResponse(
        audio_reference=payload.audio_reference,
        transcription=payload.transcription,
        statut_validation=statut_validation,
        confidence=confidence,
        missing_fields=missing_fields,
        extracted_visit=extracted_visit,
        saved_visite=saved_visite,
    )
