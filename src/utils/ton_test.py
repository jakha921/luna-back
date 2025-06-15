import requests

def tonx():
    headers = {
        'Content-Type': 'application/json',
    }

    json_data = {
        'jsonrpc': '2.0',
        'method': 'getAddressInformation',
        'params': {
            'address': 'EQAEpXgrN02JcG0pDSv_DNcQb6fRQni_j34P3_YQmTW-dnqi',
        },
        'id': 1,
    }

    response = requests.post(
        'https://mainnet-rpc.tonxapi.com/v2/json-rpc/ec5ae2c1-96ab-444c-9e45-d2aa8712d055',
        headers=headers,
        json=json_data,
    )

    print(response.json())