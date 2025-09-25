# backend/pdf_generator.py
from weasyprint import HTML
import os
from datetime import datetime

def generate_pdf_report(user_id: str, title: str, content: str) -> str:
    """
    Génère un PDF à partir d'un contenu HTML et retourne le chemin du fichier.
    """
    # Dossier de sortie
    output_dir = "static/reports"
    os.makedirs(output_dir, exist_ok=True)

    # Nom du fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{user_id}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    # Contenu HTML stylisé
    html_content = f"""
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {{ font-family: Arial, sans-serif; padding: 40px; }}
          h1 {{ color: #007bff; }}
          .section {{ margin: 30px 0; }}
          .footer {{ margin-top: 50px; color: #666; font-size: 0.9em; }}
        </style>
      </head>
      <body>
        <h1>{title}</h1>
        <div class="content">{content.replace('\n', '<br>')}</div>
        <div class="footer">Généré par Assistant de Rapports - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
      </body>
    </html>
    """

    # Générer le PDF
    HTML(string=html_content).write_pdf(filepath)

    return filepath