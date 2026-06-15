import os

from twilio.rest import Client

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_PHONE = "+16814196356"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms(to_number, message):
    try:
        response = client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=to_number
        )
        print("SMS Sent successfully, SID:", response.sid)
        return True, response.sid
    except Exception as e:
        print("Failed to send SMS:", str(e))
        return False, str(e)

if __name__ == "__main__":
    # Test sending SMS
    # send_sms("+1234567890", "Test message from Quantum Health")
    pass
