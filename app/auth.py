import base64, hashlib, hmac, json, os, secrets, time
_ITERATIONS=310_000
_secret=os.getenv("TASK_API_TOKEN_SECRET")
_environment=os.getenv("APP_ENV","development").lower()
if not _secret and _environment in {"production","prod"}:
    raise RuntimeError("TASK_API_TOKEN_SECRET must be configured in production")
_TOKEN_SECRET=(_secret.encode() if _secret else secrets.token_bytes(32))
TOKEN_TTL=3600

def hash_password(password):
    salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,_ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"
def verify_password(password,encoded):
    try:
        alg,rounds,salt,digest=encoded.split("$"); expected=base64.urlsafe_b64decode(digest)
        return alg=="pbkdf2_sha256" and hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",password.encode(),base64.urlsafe_b64decode(salt),int(rounds)),expected)
    except (ValueError,TypeError): return False
def create_token(user_id,now=None,ttl=TOKEN_TTL):
    payload=base64.urlsafe_b64encode(json.dumps({"sub":int(user_id),"exp":int(now if now is not None else time.time())+ttl},separators=(",",":")).encode()).decode().rstrip("=")
    signature=base64.urlsafe_b64encode(hmac.new(_TOKEN_SECRET,payload.encode(),hashlib.sha256).digest()).decode().rstrip("=")
    return f"{payload}.{signature}"
def verify_token(token,now=None):
    try:
        payload,signature=token.split(".",1); expected=base64.urlsafe_b64encode(hmac.new(_TOKEN_SECRET,payload.encode(),hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature,expected): return None
        data=json.loads(base64.urlsafe_b64decode(payload+"="*(-len(payload)%4)))
        if int(data["exp"])<=int(now if now is not None else time.time()): return None
        return int(data["sub"])
    except (ValueError,TypeError,KeyError,json.JSONDecodeError): return None
