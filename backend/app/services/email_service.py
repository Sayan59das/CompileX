"""
Email service for sending password reset emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Thread pool for blocking SMTP operations
_executor = ThreadPoolExecutor(max_workers=3)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
    
    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(
            self.smtp_host 
            and self.smtp_user 
            and self.smtp_password
        )
    
    def _send_email_sync(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Synchronous email sending (runs in thread pool)
        """
        try:
            logger.info(f"Attempting to send email to {to_email}")
            logger.info(f"SMTP Config: host={self.smtp_host}, port={self.smtp_port}, user={self.smtp_user}")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
            
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Send email with timeout
            logger.info("Connecting to SMTP server...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.set_debuglevel(0)
                logger.info("Starting TLS...")
                server.starttls()
                logger.info("Logging in...")
                server.login(self.smtp_user, self.smtp_password)
                logger.info("Sending message...")
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {type(e).__name__}: {str(e)}")
            return False
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email (async wrapper around sync SMTP)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text fallback (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.warning(
                "Email service not configured. Set SMTP_HOST, SMTP_USER, "
                "and SMTP_PASSWORD in your .env file."
            )
            return False
        
        # Run blocking SMTP operation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._send_email_sync,
            to_email,
            subject,
            html_content,
            text_content
        )
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        username: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email with reset link
        
        Args:
            to_email: User's email address
            username: User's username
            reset_token: Password reset token
        
        Returns:
            True if email sent successfully, False otherwise
        """
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        subject = "Reset Your CompileX Password"
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; color: #e2e8f0;">
            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);">
                            <!-- Header -->
                            <tr>
                                <td style="padding: 40px 40px 30px; text-align: center; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
                                    <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">
                                        🔐 CompileX
                                    </h1>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px;">
                                    <h2 style="margin: 0 0 20px; font-size: 24px; font-weight: 600; color: #f1f5f9;">
                                        Reset Your Password
                                    </h2>
                                    
                                    <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #cbd5e1;">
                                        Hi <strong style="color: #f1f5f9;">{username}</strong>,
                                    </p>
                                    
                                    <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #cbd5e1;">
                                        We received a request to reset your password. Click the button below to create a new password:
                                    </p>
                                    
                                    <!-- Button -->
                                    <table role="presentation" style="margin: 30px 0; width: 100%;">
                                        <tr>
                                            <td align="center">
                                                <a href="{reset_link}" style="display: inline-block; padding: 16px 32px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);">
                                    Reset Password
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="margin: 20px 0; font-size: 14px; line-height: 1.6; color: #94a3b8;">
                                        Or copy and paste this link into your browser:
                                    </p>
                                    
                                    <div style="padding: 12px; background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; word-break: break-all;">
                                        <a href="{reset_link}" style="color: #a5b4fc; text-decoration: none; font-size: 14px;">
                                            {reset_link}
                                        </a>
                                    </div>
                                    
                                    <div style="margin-top: 30px; padding: 16px; background-color: rgba(251, 191, 36, 0.1); border-left: 4px solid #fbbf24; border-radius: 8px;">
                                        <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #fcd34d;">
                                            ⚠️ <strong>Security Notice:</strong> This link will expire in 1 hour. If you didn't request this password reset, please ignore this email or contact support if you have concerns.
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 30px 40px; text-align: center; border-top: 1px solid #334155;">
                                    <p style="margin: 0 0 10px; font-size: 14px; color: #64748b;">
                                        © 2026 CompileX. All rights reserved.
                                    </p>
                                    <p style="margin: 0; font-size: 12px; color: #475569;">
                                        Competitive coding platform for developers
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Reset Your CompileX Password
        
        Hi {username},
        
        We received a request to reset your password. Click the link below to create a new password:
        
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this password reset, please ignore this email.
        
        © 2026 CompileX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_otp_email(
        self, 
        to_email: str, 
        username: str,
        otp: str
    ) -> bool:
        """
        Send OTP email for password reset
        
        Args:
            to_email: User's email address
            username: User's username
            otp: 6-digit OTP code
        
        Returns:
            True if email sent successfully, False otherwise
        """
        subject = "Your CompileX Password Reset Code"
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset OTP</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; color: #e2e8f0;">
            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);">
                            <!-- Header -->
                            <tr>
                                <td style="padding: 40px 40px 30px; text-align: center; background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);">
                                    <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">
                                        🔐 CompileX
                                    </h1>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px;">
                                    <h2 style="margin: 0 0 20px; font-size: 24px; font-weight: 600; color: #f1f5f9;">
                                        Password Reset Code
                                    </h2>
                                    
                                    <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #cbd5e1;">
                                        Hi <strong style="color: #f1f5f9;">{username}</strong>,
                                    </p>
                                    
                                    <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6; color: #cbd5e1;">
                                        We received a request to reset your password. Use the code below to reset your password:
                                    </p>
                                    
                                    <!-- OTP Code Box -->
                                    <table role="presentation" style="margin: 30px 0; width: 100%;">
                                        <tr>
                                            <td align="center">
                                                <div style="display: inline-block; padding: 24px 48px; background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%); border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(139, 92, 246, 0.3);">
                                                    <div style="font-size: 42px; font-weight: 700; color: #ffffff; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                                        {otp}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="margin: 20px 0; font-size: 14px; line-height: 1.6; color: #94a3b8; text-align: center;">
                                        Enter this code on the password reset page
                                    </p>
                                    
                                    <div style="margin-top: 30px; padding: 16px; background-color: rgba(251, 191, 36, 0.1); border-left: 4px solid #fbbf24; border-radius: 8px;">
                                        <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #fcd34d;">
                                            ⚠️ <strong>Security Notice:</strong>
                                        </p>
                                        <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 14px; line-height: 1.6; color: #fcd34d;">
                                            <li>This code will expire in <strong>10 minutes</strong></li>
                                            <li>Never share this code with anyone</li>
                                            <li>If you didn't request this, please ignore this email</li>
                                        </ul>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 30px 40px; text-align: center; border-top: 1px solid #334155;">
                                    <p style="margin: 0 0 10px; font-size: 14px; color: #64748b;">
                                        © 2026 CompileX. All rights reserved.
                                    </p>
                                    <p style="margin: 0; font-size: 12px; color: #475569;">
                                        Competitive coding platform for developers
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        CompileX Password Reset Code
        
        Hi {username},
        
        We received a request to reset your password. Use the code below to reset your password:
        
        {otp}
        
        This code will expire in 10 minutes.
        
        Never share this code with anyone. If you didn't request this password reset, please ignore this email.
        
        © 2026 CompileX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
