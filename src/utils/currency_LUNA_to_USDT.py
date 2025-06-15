import requests


def get_luna_price_binance():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "LUNAUSDT"}
    # params = {"symbol": "LUNCUSDT"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        price = data["price"]
        print(f"LUNA/USDT price on Binance: {price}")
        # return round(float(price), 3)
        return float(price)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Binance: {e}")
        return None


# Call the function
# foo = get_luna_price_binance()
# print(foo)