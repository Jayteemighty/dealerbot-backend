import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

smtp_host: str = "smtp.hostinger.com"
smtp_port: int = 465
smtp_username: str = "noreply@tournamentiq.io"
smtp_password: str = "NoReply@Hostinger101"
recipient_email: str = "bolajiogaji@gmail.com"

def submit_inquiry(
    name: str,
    phone: str,
    email: str,
    inquiry_type: str,
    details: str,
) -> tuple[bool, Optional[str]]:
    """
    Submit an inquiry form and send it via email using ladus.io mail service.
    
    Returns:
        tuple: (success: bool, error_message: Optional[str])
    """
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = recipient_email
        msg['Subject'] = f'New Inquiry from {name} - {inquiry_type}'

        # Create email body
        body = f"""
        New inquiry received:
        
        Name: {name}
        Phone: {phone}
        Email: {email}
        Inquiry Type: {inquiry_type}
        
        Details:
        {details}
        """
        
        msg.attach(MIMEText(body, 'plain'))

        # Setup SMTP server connection
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)  # Changed to SMTP_SSL
        server.login(smtp_username, smtp_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return True, None

    except Exception as e:
        return False, str(e)


# if __name__ == "__main__":
#     print("Testing submit_inquiry function...")
    
#     # Test case
#     test_data = {
#         "name": "Test User",
#         "phone": "(555) 123-4567",
#         "email": "test@example.com",
#         "inquiry_type": "Test Inquiry",
#         "details": "This is a test submission from the submit_form.py test function."
#     }
    
#     # Test with default SMTP settings
#     success, error = submit_inquiry(**test_data)
    
#     if success:
#         print("✅ Test passed: Email sent successfully")
#     else:
#         print(f"❌ Test failed: {error}")
#         print("\nSMTP Configuration used:")
#         print(f"Host: {smtp_host}")
#         print(f"Port: {smtp_port}")
#         print(f"Username: {smtp_username}")
#         print(f"Recipient: {recipient_email}")