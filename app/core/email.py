from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from app.config import get_settings

settings = get_settings()

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)


async def send_otp_email(email: str, otp: str, first_name: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #1a73e8;">Ondo Logistics — Driver Verification</h2>
        <p>Hello {first_name},</p>
        <p>Your one-time verification code is:</p>
        <div style="background: #f0f4f8; padding: 20px; text-align: center; 
                    border-radius: 8px; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                         color: #1a73e8;">{otp}</span>
        </div>
        <p>This code expires in <strong>10 minutes</strong>.</p>
        <p>If you didn't request this, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #888; font-size: 12px;">Ondo State Intelligent Logistics Platform</p>
    </div>
    """

    message = MessageSchema(
        subject="Your Verification Code — Ondo Logistics",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    await fast_mail.send_message(message)


async def send_order_notification_email(
    email: str,
    first_name: str,
    waybill_number: str,
    status: str,
    origin: str,
    destination: str,
):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #1a73e8;">Order Update</h2>
        <p>Hello {first_name},</p>
        <p>Your order <strong>{waybill_number}</strong> has been updated:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr><td style="padding: 8px; color: #666;">Route</td>
                <td style="padding: 8px; font-weight: bold;">{origin} → {destination}</td></tr>
            <tr><td style="padding: 8px; color: #666;">Status</td>
                <td style="padding: 8px; font-weight: bold; color: #1a73e8;">{status.replace('_', ' ').title()}</td></tr>
        </table>
        <p style="color: #888; font-size: 12px;">Ondo State Intelligent Logistics Platform</p>
    </div>
    """

    message = MessageSchema(
        subject=f"Order {waybill_number} — {status.replace('_', ' ').title()}",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    await fast_mail.send_message(message)


async def send_driver_welcome_email(email: str, first_name: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #1a73e8;">Welcome, {first_name}!</h2>
        <p>Your driver account has been verified successfully.</p>
        <p>You can now:</p>
        <ul>
            <li>View and accept delivery orders</li>
            <li>Enable GPS tracking for real-time delivery updates</li>
            <li>Manage your delivery history</li>
        </ul>
        <p>Open the driver dashboard in your browser to get started — no app installation needed.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #888; font-size: 12px;">Ondo State Intelligent Logistics Platform</p>
    </div>
    """

    message = MessageSchema(
        subject="Welcome to Ondo Logistics — Driver Verified",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    await fast_mail.send_message(message)