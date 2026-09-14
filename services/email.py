# services/email.py
import os
import requests

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@userdoc.io")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Userdoc Support")

def send_reset_password_email(to_email: str, reset_link: str) -> bool:
    """Mengirimkan email reset password ke inbox pengguna via Brevo API"""
    if not BREVO_API_KEY:
        print("⚠️ BREVO_API_KEY belum diisi di .env. Menggunakan fallback log console.")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reset Password - Userdoc</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 30px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="color: #1e293b; margin-top: 0; text-align: center;">Permintaan Reset Password</h2>
            <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                Halo, kami menerima permintaan untuk mengatur ulang kata sandi akun Userdoc Anda.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; display: inline-block;">
                    Reset Password Saya
                </a>
            </div>
            <p style="color: #64748b; font-size: 12px; line-height: 1.5;">
                Tautan ini hanya berlaku selama <strong>15 menit</strong>. Jika Anda tidak merasa meminta reset password, silakan abaikan email ini.
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="color: #94a3b8; font-size: 11px; text-align: center; margin-bottom: 0;">
                &copy; 2026 Userdoc Application. All rights reserved.
            </p>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Reset Password Akun Userdoc Anda",
        "htmlContent": html_content,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            print(f"✅ Email reset password berhasil dikirim ke {to_email} via Brevo!")
            return True
        else:
            print(f"⚠️ Gagal kirim email via Brevo ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"⚠️ Error koneksi Brevo: {str(e)}")
        return False