import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.models.user import User
from src.schemas.user import SUserCreate
from src.repositories.user import UserRepository


class TestReferralAPI:
    """Тесты API для реферальной системы"""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_luna_price(self):
        """Мок для цены LUNA"""
        return 0.5  # $0.5 за LUNA
    
    def test_create_user_without_referral_api(self, client, mock_luna_price):
        """Тест создания пользователя без реферала через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Данные пользователя без реферала
            user_data = {
                "telegram_id": 111111111,
                "username": "test_user",
                "firstname": "Test",
                "lastname": "User",
                "balance": 0,
                "lang_code": "ru"
            }
            
            # Отправляем запрос на создание пользователя
            response = client.post("/api/v1/user/", json=user_data)
            
            # Проверяем успешный ответ
            assert response.status_code == 201
            
            # Проверяем, что пользователь создан без реферала
            user_response = response.json()
            assert user_response["data"]["referred_by"] is None
            assert user_response["data"]["balance"] == 0
    
    def test_create_user_with_referral_api(self, client, mock_luna_price):
        """Тест создания пользователя с рефералом через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Сначала создаем приглашающего пользователя
            inviter_data = {
                "telegram_id": 123456789,
                "username": "inviter_user",
                "firstname": "Inviter",
                "lastname": "User",
                "balance": 0,
                "lang_code": "ru"
            }
            
            inviter_response = client.post("/api/v1/user/", json=inviter_data)
            assert inviter_response.status_code == 201
            inviter_id = inviter_response.json()["data"]["id"]
            
            # Теперь создаем приглашенного пользователя
            invited_data = {
                "telegram_id": 987654321,
                "username": "invited_user",
                "firstname": "Invited",
                "lastname": "User",
                "balance": 0,
                "referred_by": inviter_id,
                "lang_code": "ru"
            }
            
            invited_response = client.post("/api/v1/user/", json=invited_data)
            assert invited_response.status_code == 201
            
            # Проверяем данные приглашенного пользователя
            invited_user = invited_response.json()["data"]
            assert invited_user["referred_by"] == inviter_id
            assert invited_user["balance"] == 0  # Баланс не меняется
            assert invited_user["invitation_bonus"] == 25000000  # $50 в LUNA при цене $0.5
    
    def test_get_user_by_referral_code_api(self, client):
        """Тест получения пользователя по реферальному коду через API"""
        # Создаем пользователя
        user_data = {
            "telegram_id": 555555555,
            "username": "test_user",
            "firstname": "Test",
            "lastname": "User",
            "balance": 0,
            "lang_code": "ru"
        }
        
        response = client.post("/api/v1/user/", json=user_data)
        assert response.status_code == 201
        
        user = response.json()["data"]
        referral_code = user["referral_code"]
        
        # Получаем пользователя по реферальному коду
        referral_response = client.get(f"/api/v1/user/referral-code/{referral_code}")
        assert referral_response.status_code == 200
        
        # Проверяем, что возвращается правильный ID пользователя
        user_id = referral_response.json()["data"]
        assert user_id == user["id"]
    
    def test_get_user_full_data_api(self, client, mock_luna_price):
        """Тест получения полных данных пользователя с рефералами через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем приглашающего пользователя
            inviter_data = {
                "telegram_id": 123456789,
                "username": "inviter_user",
                "firstname": "Inviter",
                "lastname": "User",
                "balance": 0,
                "lang_code": "ru"
            }
            
            inviter_response = client.post("/api/v1/user/", json=inviter_data)
            assert inviter_response.status_code == 201
            inviter_id = inviter_response.json()["data"]["id"]
            
            # Создаем приглашенного пользователя
            invited_data = {
                "telegram_id": 987654321,
                "username": "invited_user",
                "firstname": "Invited",
                "lastname": "User",
                "balance": 0,
                "referred_by": inviter_id,
                "lang_code": "ru"
            }
            
            invited_response = client.post("/api/v1/user/", json=invited_data)
            assert invited_response.status_code == 201
            
            # Получаем полные данные приглашающего пользователя
            full_data_response = client.get(f"/api/v1/user/full_user/{123456789}")
            assert full_data_response.status_code == 200
            
            full_data = full_data_response.json()["data"]
            
            # Проверяем, что у приглашающего есть приглашенные пользователи
            assert len(full_data["referred_users"]) == 1
            assert full_data["referred_users"][0]["telegram_id"] == 987654321
    
    def test_referral_bonus_calculation_api(self, client):
        """Тест расчета реферального бонуса через API"""
        test_cases = [
            (0.1, 5000000),   # $0.1 -> 5M единиц
            (0.5, 25000000),  # $0.5 -> 25M единиц
            (1.0, 50000000),  # $1.0 -> 50M единиц
            (2.0, 100000000), # $2.0 -> 100M единиц
        ]
        
        for price, expected_bonus in test_cases:
            with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=price):
                # Создаем приглашающего пользователя
                inviter_data = {
                    "telegram_id": 123456789,
                    "username": "inviter_user",
                    "firstname": "Inviter",
                    "lastname": "User",
                    "balance": 0,
                    "lang_code": "ru"
                }
                
                inviter_response = client.post("/api/v1/user/", json=inviter_data)
                assert inviter_response.status_code == 201
                inviter_id = inviter_response.json()["data"]["id"]
                
                # Создаем приглашенного пользователя
                invited_data = {
                    "telegram_id": 987654321,
                    "username": "invited_user",
                    "firstname": "Invited",
                    "lastname": "User",
                    "balance": 0,
                    "referred_by": inviter_id,
                    "lang_code": "ru"
                }
                
                invited_response = client.post("/api/v1/user/", json=invited_data)
                assert invited_response.status_code == 201
                
                # Проверяем, что invitation_bonus рассчитан правильно
                invited_user = invited_response.json()["data"]
                assert invited_user["invitation_bonus"] == expected_bonus
    
    def test_referral_system_business_logic_api(self, client, mock_luna_price):
        """Тест бизнес-логики реферальной системы через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # 1. Создаем приглашающего пользователя
            inviter_data = {
                "telegram_id": 123456789,
                "username": "inviter_user",
                "firstname": "Inviter",
                "lastname": "User",
                "balance": 1000000,  # Начальный баланс 1 LUNA
                "lang_code": "ru"
            }
            
            inviter_response = client.post("/api/v1/user/", json=inviter_data)
            assert inviter_response.status_code == 201
            inviter_id = inviter_response.json()["data"]["id"]
            
            # 2. Создаем приглашенного пользователя
            invited_data = {
                "telegram_id": 987654321,
                "username": "invited_user",
                "firstname": "Invited",
                "lastname": "User",
                "balance": 0,
                "referred_by": inviter_id,
                "lang_code": "ru"
            }
            
            invited_response = client.post("/api/v1/user/", json=invited_data)
            assert invited_response.status_code == 201
            
            # 3. Проверяем результаты
            invited_user = invited_response.json()["data"]
            expected_bonus = int(mock_luna_price * 50 * 1000000)  # 25000000
            
            # Приглашенный НЕ получает бонус на баланс
            assert invited_user["balance"] == 0
            
            # Приглашенный получает invitation_bonus для отслеживания
            assert invited_user["invitation_bonus"] == expected_bonus
            
            # Приглашенный получает код приглашающего
            assert invited_user["referred_by"] == inviter_id
    
    def test_multiple_referrals_api(self, client, mock_luna_price):
        """Тест множественных рефералов через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем приглашающего пользователя
            inviter_data = {
                "telegram_id": 123456789,
                "username": "inviter_user",
                "firstname": "Inviter",
                "lastname": "User",
                "balance": 0,
                "lang_code": "ru"
            }
            
            inviter_response = client.post("/api/v1/user/", json=inviter_data)
            assert inviter_response.status_code == 201
            inviter_id = inviter_response.json()["data"]["id"]
            
            # Создаем несколько приглашенных пользователей
            invited_users = []
            for i in range(3):
                invited_data = {
                    "telegram_id": 987654321 + i,
                    "username": f"invited_user_{i}",
                    "firstname": f"Invited_{i}",
                    "lastname": "User",
                    "balance": 0,
                    "referred_by": inviter_id,
                    "lang_code": "ru"
                }
                
                invited_response = client.post("/api/v1/user/", json=invited_data)
                assert invited_response.status_code == 201
                invited_users.append(invited_response.json()["data"])
            
            # Проверяем, что все приглашенные пользователи имеют правильные данные
            expected_bonus = int(mock_luna_price * 50 * 1000000)
            
            for invited_user in invited_users:
                assert invited_user["balance"] == 0  # Баланс не меняется
                assert invited_user["invitation_bonus"] == expected_bonus
                assert invited_user["referred_by"] == inviter_id
    
    def test_referral_code_uniqueness_api(self, client):
        """Тест уникальности реферальных кодов через API"""
        codes = set()
        
        # Создаем несколько пользователей
        for i in range(5):
            user_data = {
                "telegram_id": 111111111 + i,
                "username": f"user_{i}",
                "firstname": f"User_{i}",
                "lastname": "Test",
                "balance": 0,
                "lang_code": "ru"
            }
            
            response = client.post("/api/v1/user/", json=user_data)
            assert response.status_code == 201
            
            user = response.json()["data"]
            codes.add(user["referral_code"])
        
        # Все коды должны быть уникальными
        assert len(codes) == 5
    
    def test_invalid_referral_code_api(self, client):
        """Тест обработки неверного реферального кода через API"""
        # Пытаемся получить пользователя по несуществующему коду
        response = client.get("/api/v1/user/referral-code/INVALID")
        assert response.status_code == 404
    
    def test_referral_with_nonexistent_inviter_api(self, client, mock_luna_price):
        """Тест реферала с несуществующим приглашающим через API"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Пытаемся создать пользователя с несуществующим приглашающим
            invited_data = {
                "telegram_id": 987654321,
                "username": "invited_user",
                "firstname": "Invited",
                "lastname": "User",
                "balance": 0,
                "referred_by": 999999,  # Несуществующий ID
                "lang_code": "ru"
            }
            
            # Ожидаем ошибку, так как приглашающий не существует
            response = client.post("/api/v1/user/", json=invited_data)
            # В зависимости от реализации, может быть 404 или 400
            assert response.status_code in [400, 404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 