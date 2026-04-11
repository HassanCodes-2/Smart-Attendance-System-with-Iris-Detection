import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

def send_attendance_email(parent_email: str, student_name: str, timestamp: datetime = None):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("WARNING: Gmail credentials not set. Skipping email.")
        return False

    if not parent_email:
        return False

    if timestamp is None:
        timestamp = datetime.now()

    time_str = timestamp.strftime("%I:%M %p")
    date_str = timestamp.strftime("%B %d, %Y")

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;
                border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
      <div style="background: #1a1a2e; padding: 24px 32px;">
        <h2 style="color: #ffffff; margin: 0; font-size: 20px;">✅ Attendance Confirmed</h2>
      </div>
      <div style="padding: 28px 32px; background: #ffffff;">
        <p style="margin: 0 0 16px; color: #333; font-size: 15px;">Dear Parent / Guardian,</p>
        <p style="margin: 0 0 24px; color: #333; font-size: 15px;">
          Your child <strong>{student_name}</strong> has been marked
          <strong style="color: #22c55e;">present</strong> today.
        </p>
        <div style="background: #f4f7ff; border-radius: 6px; padding: 16px 20px; margin-bottom: 24px;">
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="color: #666; font-size: 13px; padding: 4px 0;">Student</td>
              <td style="color: #111; font-size: 13px; font-weight: bold; text-align: right;">{student_name}</td>
            </tr>
            <tr>
              <td style="color: #666; font-size: 13px; padding: 4px 0;">Date</td>
              <td style="color: #111; font-size: 13px; text-align: right;">{date_str}</td>
            </tr>
            <tr>
              <td style="color: #666; font-size: 13px; padding: 4px 0;">Time</td>
              <td style="color: #111; font-size: 13px; text-align: right;">{time_str}</td>
            </tr>
          </table>
        </div>
        <p style="margin: 0; color: #888; font-size: 12px;">
          This is an automated message. Please do not reply.
        </p>
      </div>
      <div style="background: #f9f9f9; padding: 14px 32px; border-top: 1px solid #e0e0e0;">
        <p style="margin: 0; color: #aaa; font-size: 11px;">Powered by IrisSecure</p>
      </div>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✅ {student_name} is present today — {date_str}"
        msg["From"] = f"IrisSecure Attendance <{GMAIL_USER}>"
        msg["To"] = parent_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, parent_email, msg.as_string())

        print(f"Email sent to {parent_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False