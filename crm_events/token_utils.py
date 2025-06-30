import datetime
import urllib.parse
from cryptography.fernet import Fernet, InvalidToken
from config.settings import TIMEZONE

SECRET_KEY = b'wzR2DOfUvBh0XkhJ5Inwx8O-w8wCg51sfFVc6dzPA8Q='
cipher_suite = Fernet(SECRET_KEY)


def generate_event_token(email, user_id, event_expiry_datetime):
    """
    Generates an encrypted token string containing user email, user ID,
    and the event's expiry timestamp. This token is designed to be part of a URL.

    Args:
        email (str): The user's email address.
        user_id (int): The user's unique ID.
        event_expiry_datetime (datetime.datetime): The exact datetime when the event link should expire.
                                                 This datetime object MUST be timezone-aware.

    Returns:
        str: The URL-safe encrypted token string.
    """
    if event_expiry_datetime.tzinfo is None:
        event_expiry_datetime = TIMEZONE.localize(event_expiry_datetime)
    else:
        event_expiry_datetime = event_expiry_datetime.astimezone(TIMEZONE)

    expiry_timestamp = int(event_expiry_datetime.timestamp())
    data_to_encrypt = f"{email}|{user_id}|{expiry_timestamp}".encode('utf-8')
    encrypted_data = cipher_suite.encrypt(data_to_encrypt)
    encoded_token_param = urllib.parse.quote_plus(encrypted_data.decode('utf-8'))

    return encoded_token_param


def decrypt_event_token(encoded_token):
    """
    Decrypts a token string received from a URL and extracts the user's email, user ID,
    and the event's expiry datetime. It also validates if the token has expired
    based on the event's specific expiry time.

    Args:
        encoded_token (str): The encrypted token string received from the URL parameter.

    Returns:
        tuple[str, int, datetime.datetime]: (email, user_id, event_expiry_datetime) if valid and not expired.
        tuple[None, None, None]: If the token is invalid, tampered with, or expired.
    """
    try:
        decoded_param = urllib.parse.unquote_plus(encoded_token)
        encrypted_data = decoded_param.encode('utf-8')

        decrypted_data = cipher_suite.decrypt(encrypted_data).decode('utf-8')

        email, user_id_str, expiry_timestamp_str = decrypted_data.split('|')
        user_id = int(user_id_str)
        expiry_timestamp = int(expiry_timestamp_str)

        event_expiry_datetime = datetime.datetime.fromtimestamp(expiry_timestamp, tz=TIMEZONE)

        now = datetime.datetime.now(TIMEZONE)
        if now > event_expiry_datetime:
            print(
                f"DEBUG: Token has expired. Current time: {now}, Expiry time: {event_expiry_datetime}")
            return None, None, None

        return email, user_id, event_expiry_datetime

    except InvalidToken:
        print("ERROR: Invalid token (tampered or wrong key).")
        return None, None, None
    except Exception as e:
        print(f"ERROR: Failed to decrypt token: {e}")
        return None, None, None
