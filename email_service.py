import resend
import os
from datetime import datetime

resend.api_key = os.environ.get("RESEND_API_KEY", "")

# The email address you send FROM.
# During testing you can use "onboarding@resend.dev" (Resend's sandbox address).
# Once you verify your own domain on Resend, change this to your school's email.
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
SENDER_NAME  = os.environ.get("SENDER_NAME",  "IrisSecure Attendance")


def send_attendance_email(parent_email: str, student_name: str, timestamp: datetime = None):
    """
    Send a notification email to a parent when their child is marked present.
    Returns True on success, False on failure.
    """
    if not resend.api_key:
        print("WARNING: RESEND_API_KEY is not set. Skipping email.")
        return False

    if not parent_email:
        return False

    if timestamp is None:
        timestamp = datetime.now()

    time_str = timestamp.strftime("%I:%M %p")   # e.g. 08:45 AM
    date_str = timestamp.strftime("%B %d, %Y")  # e.g. April 11, 2026

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;
                border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">

      <!-- Header -->
      <div style="background: #1a1a2e; padding: 24px 32px;">
        <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
          ✅ Attendance Confirmed
        </h2>
      </div>

      <!-- Body -->
      <div style="padding: 28px 32px; background: #ffffff;">
        <p style="margin: 0 0 16px; color: #333; font-size: 15px;">Dear Parent / Guardian,</p>
        <p style="margin: 0 0 24px; color: #333; font-size: 15px;">
          This is to inform you that your child <strong>{student_name}</strong>
          has been marked <strong style="color: #22c55e;">present</strong> today.
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
          This is an automated message from the IrisSecure attendance system.
          Please do not reply to this email.
        </p>
      </div>

      <!-- Footer -->
      <div style="background: #f9f9f9; padding: 14px 32px; border-top: 1px solid #e0e0e0;">
        <p style="margin: 0; color: #aaa; font-size: 11px;">Powered by IrisSecure</p>
      </div>
    </div>
    """

    try:
        params = {
            "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
            "to": [parent_email],
            "subject": f"✅ {student_name} is present today — {date_str}",
            "html": html_body,
        }
        response = resend.Emails.send(params)
        print(f"Email sent to {parent_email} | ID: {response.get('id')}")
        return True
    except Exception as e:
        print(f"Failed to send email to {parent_email}: {e}")
        return False
