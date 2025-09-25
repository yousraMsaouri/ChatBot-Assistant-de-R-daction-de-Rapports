# backend/tasks.py
from celery import Celery
import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from backend.database import SessionLocal, UserReport
from urllib.parse import quote

load_dotenv()

app = Celery('tasks', broker='redis://localhost:6379', backend='redis://localhost:6379')

@app.task
def send_reminder_email(user_id: str, report_id: int, download_link: str):
    print(f"📧 Tentative d'envoi d'email à l'utilisateur {user_id} pour le rapport {report_id}")

    message = Mail(
        from_email=os.getenv("FROM_EMAIL"),
        to_emails="yousramsaouri13@gmail.com",  # ← Remplace par ton vrai email pour test
        subject="📚 Votre rapport est prêt !",
        html_content=f"""
        <h3>Bonjour,</h3>
        <p>Votre rapport a été généré avec succès.</p>
        <p><strong>Nom :</strong> Rapport Dynamique</p>
        <a href="{download_link}" style="color: #fff; background: #007bff; padding: 10px 15px; text-decoration: none; border-radius: 4px;">
            Télécharger le rapport (PDF)
        </a>
        <p>Le lien expire dans 7 jours.</p>
        <p>Cordialement,<br>L'équipe de génération de rapports</p>
        """
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email envoyé ! Statut : {response.status_code}")
        return f"Email envoyé à {user_id}"
    except Exception as e:
        print(f"❌ Erreur d'envoi : {str(e)}")
        return f"Échec de l'envoi à {user_id}"

@app.task
def schedule_call_if_not_downloaded(user_id: str, report_id: int, download_link: str):
    print(f"📞 Vérification : le rapport {report_id} a-t-il été téléchargé ?")

    db = SessionLocal()
    report = db.query(UserReport).filter(UserReport.id == report_id).first()

    if not report or not report.downloaded:
        print(f"⚠️ Rapport non téléchargé. Envoi d’un appel à {user_id}…")

        try:
            from twilio.rest import Client
            client = Client(
                os.getenv("TWILIO_ACCOUNT_SID"),
                os.getenv("TWILIO_AUTH_TOKEN")
            )

            # Texte du message vocal
            text = f"Bonjour, votre rapport {report.report_name} est disponible depuis plusieurs jours. Veuillez le télécharger. Merci."
            encoded_text = quote(text)  # Pour éviter les erreurs d'URL

            call = client.calls.create(
                url=f"http://demo.twimlet.com/echo?Text={encoded_text}",
                to="+12566676023",  # ← numéro vérifié sur Twilio
                from_=os.getenv("TWILIO_PHONE_NUMBER")
            )
            print(f"📞 Appel lancé ! SID: {call.sid}")
        except Exception as e:
            print(f"❌ Échec de l'appel : {str(e)}")
    else:
        print(f"✅ Rapport {report_id} déjà téléchargé. Aucun appel nécessaire.")

    db.close()