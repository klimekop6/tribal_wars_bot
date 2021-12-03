import requests
import json

url = "https://api.melroselabs.com/sms/message"

payload = {
        "source": "MelroseLabs",
        "destination": "48604065940",
        "message": "Hello"
}
headers = {
  'x-api-key': 'PU2oEmr3Mz2nZ08uF7WTH2MlqpYCGNGj7Zf3p3QU',
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

print(response.text.encode('utf8'))