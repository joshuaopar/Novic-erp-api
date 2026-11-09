"""
SMS gateway abstraction. Currently stubbed — logs the message instead of sending it.
When ready to go live (post-deployment), replace send_sms() with a real call to
Africa's Talking, EgoSMS, or your MoMo-adjacent SMS provider of choice.
"""


def send_sms(phone_number: str, message: str) -> bool:
    print(f"[SMS STUB] To: {phone_number} | Message: {message}")
    return True
