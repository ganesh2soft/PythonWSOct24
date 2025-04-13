import requests

def token_generate(code):
    url = 'https://api.upstox.com/v2/login/authorization/token'
    print(f'Auth code received is ',code)
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'code': code,
        'client_id': 'dd054851-b341-4bf6-89e4-924f9339c9cf',
        'client_secret': '63nulahu1j',
        'redirect_uri': 'http://127.0.0.1',
        'grant_type': 'authorization_code',
    }

    response = requests.post(url, headers=headers, data=data)
    newdata=response.json()
    access_token = newdata.get('access_token', None)
    #print(response.status_code)
    #print(response.json())
    # Checking if the token exists and printing it
    if access_token:
        print("Access Token:", access_token)
        return access_token
    else:
        print("Access Token not found.")
        return 'no token found'