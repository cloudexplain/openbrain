"""Email service for sending verification and notification emails"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data structure"""
    to: List[str]
    subject: str
    html_content: str
    text_content: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Optional[Dict] = None


class EmailProvider(ABC):
    """Abstract base class for email providers"""
    
    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email message"""
        pass
    
    @abstractmethod
    async def send_bulk(self, messages: List[EmailMessage]) -> Dict[str, bool]:
        """Send multiple emails"""
        pass


class MockEmailProvider(EmailProvider):
    """Mock email provider for development/testing"""
    
    def __init__(self):
        self.sent_emails = []
    
    async def send_email(self, message: EmailMessage) -> bool:
        """Mock sending - just log the email"""
        logger.info(f"[MOCK EMAIL] To: {message.to}")
        logger.info(f"[MOCK EMAIL] Subject: {message.subject}")
        logger.info(f"[MOCK EMAIL] Content (first 200 chars): {message.html_content[:200]}...")
        
        self.sent_emails.append({
            'to': message.to,
            'subject': message.subject,
            'sent_at': datetime.utcnow(),
            'content': message.html_content
        })
        
        return True
    
    async def send_bulk(self, messages: List[EmailMessage]) -> Dict[str, bool]:
        """Mock bulk sending"""
        results = {}
        for message in messages:
            to_email = message.to[0] if message.to else "unknown"
            results[to_email] = await self.send_email(message)
        return results


class AzureEmailProvider(EmailProvider):
    """Azure Communication Services Email Provider"""
    
    def __init__(self, connection_string: str, sender_address: str):
        self.connection_string = connection_string
        self.sender_address = sender_address
        
        try:
            from azure.communication.email import EmailClient
            self.client = EmailClient.from_connection_string(connection_string)
            logger.info("Azure Email Provider initialized successfully")
        except ImportError:
            logger.error("azure-communication-email package not installed")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Azure Email Provider: {str(e)}")
            self.client = None
    
    async def send_email(self, message: EmailMessage) -> bool:
        """Send email via Azure Communication Services"""
        if not self.client:
            logger.error("Azure Email client not initialized")
            return False
            
        try:
            # Create Azure email message using dictionary format
            azure_message = {
                "senderAddress": message.from_email or self.sender_address,
                "content": {
                    "subject": message.subject,
                    "plainText": message.text_content,
                    "html": message.html_content,
                },
                "recipients": {
                    "to": [{"address": email} for email in message.to]
                }
            }
            
            # Send the email
            poller = self.client.begin_send(azure_message)
            result = poller.result()
            
            # Handle result as dictionary or object
            if hasattr(result, 'message_id'):
                logger.info(f"Azure email sent successfully. Message ID: {result.message_id}")
            elif isinstance(result, dict):
                message_id = result.get('messageId', 'N/A')
                logger.info(f"Azure email sent successfully. Message ID: {message_id}")
            else:
                logger.info(f"Azure email sent successfully. Result: {result}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Azure email: {str(e)}")
            return False
    
    async def send_bulk(self, messages: List[EmailMessage]) -> Dict[str, bool]:
        """Send bulk emails via Azure"""
        results = {}
        for message in messages:
            to_email = message.to[0] if message.to else "unknown"
            results[to_email] = await self.send_email(message)
        return results


class EmailService:
    """Main email service that uses configured provider"""
    
    def __init__(self, provider: Optional[EmailProvider] = None):
        self.provider = provider or MockEmailProvider()
    
    async def send_verification_email(self, to_email: str, username: str, verification_url: str) -> bool:
        """Send account verification email"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a5568; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f7fafc; padding: 30px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4299e1; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #718096; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to SecondBrain!</h1>
                </div>
                <div class="content">
                    <h2>Hi {username},</h2>
                    <p>Thanks for signing up! Please verify your email address to complete your registration.</p>
                    <p>Click the button below to verify your account:</p>
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </div>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #4299e1;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 SecondBrain. All rights reserved.</p>
                    <p>Having trouble? Check your spam folder or request a new verification email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to SecondBrain!
        
        Hi {username},
        
        Thanks for signing up! Please verify your email address to complete your registration.
        
        Click this link to verify your account:
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, you can safely ignore this email.
        
        © 2025 SecondBrain. All rights reserved.
        """
        
        message = EmailMessage(
            to=[to_email],
            subject="Verify your SecondBrain account",
            html_content=html_content,
            text_content=text_content,
            metadata={'type': 'verification', 'username': username}
        )
        
        return await self.provider.send_email(message)
    
    async def send_verification_reminder(self, to_email: str, username: str, verification_url: str) -> bool:
        """Send verification reminder email"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #ed8936; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f7fafc; padding: 30px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #ed8936; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #718096; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Please Verify Your Email</h1>
                </div>
                <div class="content">
                    <h2>Hi {username},</h2>
                    <p>Your SecondBrain account needs email verification to continue using all features.</p>
                    <p>Your grace period has expired, and you'll need to verify your email to continue using the app.</p>
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Now</a>
                    </div>
                    <p>Or copy and paste this link:</p>
                    <p style="word-break: break-all; color: #ed8936;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                </div>
                <div class="footer">
                    <p>© 2025 SecondBrain. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = EmailMessage(
            to=[to_email],
            subject="Action Required: Verify your SecondBrain account",
            html_content=html_content,
            metadata={'type': 'verification_reminder', 'username': username}
        )
        
        return await self.provider.send_email(message)


# Global email service instance
def get_email_service() -> EmailService:
    """Get configured email service instance"""
    from app.config import get_settings
    
    settings = get_settings()
    
    # Check if Azure Email is configured
    connection_string = settings.azure_email_connection_string
    sender_address = settings.azure_email_sender_address
    
    logger.info(f"🔧 DEBUG: AZURE_EMAIL_CONNECTION_STRING present: {'Yes' if connection_string else 'No'}")
    logger.info(f"🔧 DEBUG: AZURE_EMAIL_SENDER_ADDRESS present: {'Yes' if sender_address else 'No'}")
    
    if connection_string and sender_address:
        logger.info("✅ Using Azure Email Provider")
        provider = AzureEmailProvider(connection_string, sender_address)
        # Test if the provider was initialized correctly
        if provider.client:
            logger.info("✅ Azure Email Provider client initialized successfully")
        else:
            logger.error("❌ Azure Email Provider client failed to initialize, falling back to Mock")
            provider = MockEmailProvider()
    else:
        logger.info("📧 Using Mock Email Provider (Azure Email not configured)")
        if not connection_string:
            logger.info("   - Missing AZURE_EMAIL_CONNECTION_STRING")
        if not sender_address:
            logger.info("   - Missing AZURE_EMAIL_SENDER_ADDRESS")
        provider = MockEmailProvider()
    
    return EmailService(provider)
