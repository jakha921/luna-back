import requests
from fastapi import HTTPException

from src.core.config import settings

TON_Testnet_FAUCET_API_KEY = "ec5ae2c1-96ab-444c-9e45-d2aa8712d055"

HEADERS = {
    'X-API-Key': settings.TON_API_KEY,
    'Content-Type': 'application/json'
}


def get_balance(address: str) -> float:
    url = f"{settings.TON_API_ENDPOINT}/getAddressBalance"
    params = {"address": address}

    response = requests.get(url, params=params, headers=HEADERS)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Не удалось получить баланс кошелька")

    data = response.json()
    print('data', data)

    if data.get('ok') and 'result' in data:
        balance = int(data['result']) / 1e9  # Перевод из нанотонов в TON
        return balance
    else:
        raise HTTPException(status_code=400, detail=data.get('result', 'Неизвестная ошибка'))


def send_transaction(from_address: str, to_address: str, amount: float, private_key: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "rawSendMessage",
        "params": {
            "from": from_address,
            "to": to_address,
            "value": int(amount * 1e9),  # Сумма в нанотонах
            "privateKey": private_key,
            "bounce": False
        }
    }

    response = requests.post(settings.TON_API_ENDPOINT, json=payload, headers=HEADERS)
    data = response.json()

    if 'result' in data:
        return data['result']
    else:
        error_message = data.get('error', {}).get('message', 'Неизвестная ошибка')
        raise HTTPException(status_code=400, detail=f"Ошибка при отправке транзакции: {error_message}")


def withdraw(amount: float, telegram_id: int):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше нуля")

    user_address = f"EQAEpXgrN02JcG0pDSv_DNcQb6fRQni_j34P3_YQmTW-{telegram_id}"

    # Проверяем баланс нашего кошелька
    balance = get_balance(settings.WALLET_ADDRESS)
    print('balance', balance)

    commission = 0.1  # 0.1 TON комиссия
    total_amount = amount + commission

    # Проверяем, хватает ли средств на кошельке
    print('total_amount', total_amount)
    if balance < total_amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств на кошельке для выполнения операции")

    # Отправляем сумму пользователю
    try:
        send_transaction(
            from_address=settings.WALLET_ADDRESS,
            to_address=user_address,
            amount=amount,
            private_key=settings.WALLET_PRIVATE_KEY
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Отправляем комиссию на ваш кошелёк
    try:
        send_transaction(
            from_address=settings.WALLET_ADDRESS,
            to_address=settings.COMMISSION_ADDRESS,
            amount=commission,
            private_key=settings.WALLET_PRIVATE_KEY
        )
    except Exception as e:
        # В случае ошибки при отправке комиссии, можно решить, как поступить
        raise HTTPException(status_code=400, detail=f"Ошибка при отправке комиссии: {str(e)}")

    return {"status": "success", "message": "Вывод средств выполнен успешно"}


if __name__ == '__main__':
    print(get_balance(settings.WALLET_ADDRESS))
    print(send_transaction(
        from_address=settings.WALLET_ADDRESS,
        to_address=settings.COMMISSION_ADDRESS,
        amount=1.0,
        private_key=settings.WALLET_PRIVATE_KEY
    ))
    print(withdraw(1.0, "EQAEpXgrN02JcG0pDSv_DNcQb6fRQni_j34P3_YQmTW-dnqi"))
