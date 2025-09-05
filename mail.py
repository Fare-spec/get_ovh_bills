import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def construct_html(bills: list[tuple[str, str]]) -> str:
    rows = []
    for bill_id, date in bills:
        rows.append(
            f"<li><b style='color:#2c3e50;'>Facture n°{bill_id}</b> — "
            f"<span style='color:#16a085;'>émise le {date}</span></li>"
        )

    template = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Nouvelle(s) facture(s) reçue(s)</title>
    </head>
    <body style="font-family:Arial, sans-serif; background:#f9f9f9; color:#333;">
        <div style="max-width:600px; margin:auto; padding:20px; background:#fff; border:1px solid #ddd; border-radius:8px;">
            <h2 style="color:#e74c3c; text-align:center;">
                Vous avez reçu <b>{len(bills)}</b> nouvelle(s) facture(s)
            </h2>
            <ul style="line-height:1.6; font-size:14px;">
                {"".join(rows)}
            </ul>
        </div>
    </body>
    </html>"""
    return template


def send_email(
    subject,
    content,
    email_from,
    email_password,
    smtp_mail_address,
    smpt_port,
    email_to,
):
    msg = MIMEMultipart()
    msg["From"] = email_from
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "html"))

    with smtplib.SMTP(smtp_mail_address, smpt_port) as server:
        server.starttls()
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())
