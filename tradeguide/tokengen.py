import os
import requests

# 10 Oct 2026: Upstox app credentials moved out of the code into upstox.env (one per PC, see upstox.env.example)
_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upstox.env')


def _cred(name):
    if os.path.exists(_ENV):
        with open(_ENV, encoding='utf-8') as f:
            for raw in f:
                raw = raw.strip()
                if raw and not raw.startswith('#') and '=' in raw:
                    k, v = raw.split('=', 1)
                    if k.strip() == name:
                        return v.strip().strip('"').strip("'")
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f'{name} missing: create upstox.env from upstox.env.example')
    return v


def token_generate(code, redirect_uri='http://127.0.0.1'):
    url = 'https://api.upstox.com/v2/login/authorization/token'
    print(f'Auth code received is ',code)
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'code': code,
        'client_id': _cred('UPSTOX_CLIENT_ID'),
        'client_secret': _cred('UPSTOX_CLIENT_SECRET'),
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }

    response = requests.post(url, headers=headers, data=data)
    newdata=response.json()
    access_token = newdata.get('access_token', None)
    #print(response.status_code)
    #print(response.json())
    # Checking if the token exists and printing it
    if access_token:
        print("Access Token received (not printed).")
        return access_token
    else:
        # 10 Oct 2026: show Upstox's reason (never the secret), e.g. Invalid Credentials / invalid auth code
        errs = newdata.get('errors') or []
        why = '; '.join(f"{e.get('errorCode')}: {e.get('message')}" for e in errs if isinstance(e, dict)) or str(newdata)[:200]
        print(f"Access Token not found. HTTP {response.status_code} - {why}")
        try:
            import logging
            logging.getLogger('app').error(f"Upstox token exchange failed: HTTP {response.status_code} - {why}")
        except Exception:
            pass
        return 'no token found'