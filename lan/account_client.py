"""Bounded account login over the configured Arena game TCP port."""
import json
import socket


def _valid_token(value):
    return (type(value) is str and 16 <= len(value) <= 256 and
            all(33 <= ord(character) <= 126 for character in value))


def account_request(host, port, *, action, username="", password="", token=""):
    if action not in ("login", "me"):
        raise ValueError("Unsupported account action")
    request = {"op": "account", "version": 2, "action": action}
    if action == "login":
        if not isinstance(username, str) or not username.strip() or len(username) > 64:
            raise ValueError("Enter your account username")
        if not isinstance(password, str) or len(password) <= 1:
            raise ValueError("Enter your password (at least two characters)")
        request.update(username=username.strip(), password=password)
    else:
        if not _valid_token(token):
            raise ValueError("Login was not remembered. Enter your password and click Login.")
        request["token"] = token
    frame = (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
    if len(frame) > 8192:
        raise ValueError("Account request is too large")
    try:
        with socket.create_connection((host, int(port)), timeout=8) as connection:
            connection.settimeout(8)
            connection.sendall(frame)
            with connection.makefile("rb") as stream:
                raw = stream.readline(65537)
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot reach the Arena game server. Check its host and port.") from exc
    if not raw.endswith(b"\n") or len(raw) > 65536:
        raise ValueError("Account server returned an invalid reply")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError("Account server returned an invalid reply") from None
    if type(result) is not dict or result.get("event") != "account":
        raise ValueError("This game server does not support account login; update the server")
    if result.get("state") != "ok":
        raise ValueError("Login was refused or expired. Check your username and password.")
    return result


def authenticate(host, port, username, password, saved_token=""):
    username = username.strip()
    if not username or len(username) > 64:
        raise ValueError("Enter your account username")
    result = (account_request(host, port, action="login", username=username, password=password)
              if password else account_request(host, port, action="me", token=saved_token))
    token = result.get("token", saved_token)
    profile = result.get("profile")
    if (type(profile) is not dict or type(profile.get("display_name")) is not str or
            not profile["display_name"].strip() or not _valid_token(token) or
            str(profile.get("username", "")).lower() != username.lower()):
        raise ValueError("Account server returned an invalid profile or login token")
    return token, profile
