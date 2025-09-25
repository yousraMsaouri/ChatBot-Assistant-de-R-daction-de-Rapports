from backend.pdf_generator import generate_pdf_report
import urllib.parse
from fastapi.middleware.cors import CORSMiddleware
# backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from fastapi.staticfiles import StaticFiles 

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import json
from datetime import datetime

from google.generativeai.types import BlockedPromptException
from backend.pdf_generator import generate_pdf_report
# ✅ Imports corrigés : ajoute "backend." devant chaque module local
import backend.rag_engine as rag_engine
import backend.gemini_handler as gemini_handler
from backend.database import SessionLocal, UserReport, UserMessage
from backend.tasks import send_reminder_email, schedule_call_if_not_downloaded

app = FastAPI(title="Chatbot Intelligent pour Rapports")
# Autoriser le frontend Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ReportRequest(BaseModel):
    user_id: str
    report_name: str

#ÉTAPE 6 : Activer le serveur FastAPI pour servir les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Nouvelle partie : Détecte et génère un rapport ---
def should_generate_report(message: str) -> tuple[bool, str]:
    """
    Vérifie si le message contient une demande de création de rapport.
    Retourne (True, titre) ou (False, "")
    """
    message_lower = message.lower()
    if "crée un nouveau rapport" in message_lower or "génère un rapport" in message_lower:
        # Essaye d'extraire le titre après "intitulé :"
        if "intitulé :" in message:
            title = message.split("intitulé :")[1].strip()
            return True, title
        elif "intitulé:" in message:
            title = message.split("intitulé:")[1].strip()
            return True, title
        else:
            # Titre par défaut
            return True, "Rapport sans titre"
    return False, ""

# --- Route /chat mise à jour ---
@app.post("/chat")
async def chat(request: ChatRequest):
    db = next(get_db())
    
    # Sauvegarde le message utilisateur
    user_message = UserMessage(user_id=request.user_id, message=request.message, sender="user")
    db.add(user_message)
    db.commit()

    # Récupère l'historique
    user_reports = db.query(UserReport).filter(UserReport.user_id == request.user_id).all()
    last_report_name = user_reports[-1].report_name if user_reports else "Aucun"

    # === 🔥 DÉTECTION DE CRÉATION DE RAPPORT ===
    message_lower = request.message.lower()
    if ("génère un nouveau rapport" in message_lower or 
        "crée un nouveau rapport" in message_lower) and "intitulé :" in request.message:

        # Extraire le titre
        try:
            report_title = request.message.split("intitulé :")[1].strip()
        except:
            report_title = "Rapport sans titre"

        # Générer le contenu avec Gemini
        prompt = f"Rédige un rapport complet intitulé '{report_title}'..."
        try:
            gemini_response = gemini_handler.generate_response(prompt)
        except Exception as e:
            gemini_response = f"Erreur Gemini : {str(e)}"

        # === 📄 SAUVEGARDER LE RAPPORT EN BASE ===
        new_report = UserReport(
            user_id=request.user_id,
            report_name=report_title,
            plan_json='{"sections": ["intro", "analyse", "conclusion"]}',
            file_path="",
            downloaded=False
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        # === 📄 GÉNÈRE LE PDF ===
        pdf_path = generate_pdf_report(
            user_id=request.user_id,
            title=report_title,
            content=gemini_response
        )
        relative_path = pdf_path.replace("static/", "/static/")
        new_report.file_path = relative_path
        db.commit()

        # === 📬 PLANIFIE EMAIL ET APPEL ===
        download_link = f"http://localhost:8000{relative_path}"
        send_reminder_email.apply_async(
            (request.user_id, new_report.id, download_link),
            countdown=2
        )
        schedule_call_if_not_downloaded.apply_async(
            (request.user_id, new_report.id, download_link),
            countdown=5
        )

        # ✅ Réponse au frontend
        response_text = f"✅ Rapport '{report_title}' généré avec succès ! Un email vous a été envoyé."

        # Sauvegarde la réponse du bot
        bot_message = UserMessage(user_id=request.user_id, message=response_text, sender="bot")
        db.add(bot_message)
        db.commit()
        db.close()

        # ✅ RETURN à l'intérieur de la fonction
        return {"response": response_text}

    # === 🤖 Si ce n'est PAS une demande de rapport, utilise Gemini normalement ===
    context = ""
    if user_reports:
        context = f"\n\nHistorique des rapports : {len(user_reports)} générés. Dernier : {last_report_name}"

    full_prompt = f"{request.message}{context}"
    try:
        response = gemini_handler.generate_response(full_prompt)
    except Exception as e:
        response = f"Désolé, une erreur est survenue avec Gemini : {str(e)}"

    # Sauvegarde la réponse
    bot_message = UserMessage(user_id=request.user_id, message=response, sender="bot")
    db.add(bot_message)
    db.commit()
    db.close()

    # ✅ RETURN à l'intérieur de la fonction
    return {"response": response}


@app.post("/generate-report")
async def generate_report(req: ReportRequest):
    db = next(get_db())

    # Simuler génération
    new_report = UserReport(
        user_id=req.user_id,
        report_name=req.report_name,
        plan_json='{{"introduction": "...", "conclusion": "..."}}',
        file_path="",  # sera mis à jour après génération PDF
        downloaded=False
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # === 🔧 GÉNÉRER LE CONTENU AVEC GEMINI ===
    prompt = f"""
    Tu es un expert en rédaction. Rédige un rapport complet intitulé '{req.report_name}'.
    Structure : Introduction, Développement, Conclusion.
    Style : professionnel, clair, concis.
    """

    try:
        gemini_response = gemini_handler.generate_response(prompt)
    except Exception as e:
        gemini_response = "Contenu du rapport indisponible."

    # === 📄 GÉNÉRER LE PDF ===
    pdf_path = generate_pdf_report(
        user_id=req.user_id,
        title=req.report_name,
        content=gemini_response
    )

    # Sauvegarder le chemin relatif dans la DB
    relative_path = pdf_path.replace("static/", "/static/")
    new_report.file_path = relative_path
    db.commit()

    # === 📬 ENVOYER UN EMAIL AVEC LIEN DE TÉLÉCHARGEMENT ===
    download_link = f"http://localhost:8000{relative_path}"
    send_reminder_email.apply_async(
        (req.user_id, new_report.id, download_link),
        countdown=2  # Pour test rapide → 2 secondes
    )

    # Planifier appel après 5s (test)
    schedule_call_if_not_downloaded.apply_async(
        (req.user_id, new_report.id, download_link),
        countdown=5
    )

    return {
        "status": "rapport généré",
        "id": new_report.id,
        "download_link": download_link
    }