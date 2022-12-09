from base64 import b64decode
from urllib.parse import unquote


class BasicAuthDecodeError(Exception):
    pass


def basic_decode(encoded_str: str) -> tuple[str, str]:
    """Decode an encrypted HTTP basic authentication string. Returns a tuple of
    the form (username, password), and raises a BasicAuthDecodeError exception if
    nothing could be decoded.
    """
    split = encoded_str.strip().split(" ")

    # If split is only one element, try to decode the username and password
    # directly.
    if len(split) == 1:
        try:
            username, password = b64decode(split[0]).decode().split(":", 1)
        except Exception:
            raise BasicAuthDecodeError()

    # If there are only two elements, check the first and ensure it says
    # 'basic' so that we know we're about to decode the right thing. If not,
    # bail out.
    elif len(split) == 2:
        if split[0].strip().lower() == "basic":
            try:
                username, password = b64decode(split[1]).decode().split(":", 1)
            except Exception:
                raise BasicAuthDecodeError()
        else:
            raise BasicAuthDecodeError()

    # If there are more than 2 elements, something crazy must be happening.
    # Bail.
    else:
        raise BasicAuthDecodeError()

    return unquote(username), unquote(password)
