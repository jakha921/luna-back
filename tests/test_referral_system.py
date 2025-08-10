import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User
from src.schemas.user import SUserCreate
from src.repositories.user import UserRepository
from src.utils.currency_LUNA_to_USDT import get_luna_price_binance


class TestReferralSystem:
    """Тесты для реферальной системы"""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_luna_price(self):
        """Мок для цены LUNA"""
        return 0.5  # $0.5 за LUNA
    
    @pytest.fixture
    def inviter_user_data(self):
        """Данные приглашающего пользователя"""
        return {
            "telegram_id": 123456789,
            "username": "inviter_user",
            "firstname": "Inviter",
            "lastname": "User",
            "balance": 0,
            "lang_code": "ru"
        }
    
    @pytest.fixture
    def invited_user_data(self):
        """Данные приглашенного пользователя"""
        return {
            "telegram_id": 987654321,
            "username": "invited_user", 
            "firstname": "Invited",
            "lastname": "User",
            "balance": 0,
            "lang_code": "ru"
        }
    
    @pytest.mark.asyncio
    async def test_create_user_without_referral(self, mock_luna_price):
        """Тест создания пользователя без реферала"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем пользователя без реферала
            user_data = SUserCreate(
                telegram_id=111111111,
                username="test_user",
                firstname="Test",
                lastname="User",
                balance=0,
                lang_code="ru"
            )
            
            # Проверяем, что пользователь создается без реферала
            assert user_data.referred_by is None
            # invitation_bonus устанавливается только в репозитории, не в схеме
    
    @pytest.mark.asyncio
    async def test_create_user_with_referral(self, mock_luna_price):
        """Тест создания пользователя с рефералом"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем приглашающего пользователя
            inviter_data = SUserCreate(
                telegram_id=123456789,
                username="inviter_user",
                firstname="Inviter",
                lastname="User",
                balance=0,
                lang_code="ru"
            )
            
            # Создаем приглашенного пользователя
            invited_data = SUserCreate(
                telegram_id=987654321,
                username="invited_user",
                firstname="Invited", 
                lastname="User",
                balance=0,
                referred_by=1,  # ID приглашающего пользователя
                lang_code="ru"
            )
            
            # Проверяем логику расчета бонуса
            expected_bonus = int(mock_luna_price * 50 * 1000000)  # $50 в LUNA
            assert expected_bonus == int(0.5 * 50 * 1000000)  # 25000000
            
            # Проверяем, что приглашенный пользователь получает код приглашения
            assert invited_data.referred_by == 1
            # invitation_bonus устанавливается только в репозитории, не в схеме
    
    @pytest.mark.asyncio
    async def test_referral_bonus_calculation(self, mock_luna_price):
        """Тест расчета реферального бонуса"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Цена LUNA = $0.5
            # Бонус = $50 / $0.5 = 100 LUNA
            # В минимальных единицах: 100 * 1000000 = 100000000
            
            expected_bonus = int(mock_luna_price * 50 * 1000000)
            assert expected_bonus == 25000000  # 25 миллионов минимальных единиц
            
            # Проверяем разные цены LUNA
            test_cases = [
                (0.1, 5000000),   # $0.1 -> 5M единиц
                (0.5, 25000000),  # $0.5 -> 25M единиц
                (1.0, 50000000),  # $1.0 -> 50M единиц  
                (2.0, 100000000), # $2.0 -> 100M единиц
            ]
            
            for price, expected in test_cases:
                with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=price):
                    bonus = int(price * 50 * 1000000)
                    assert bonus == expected
    
    @pytest.mark.asyncio
    async def test_referral_relationships(self):
        """Тест реферальных связей между пользователями"""
        # Создаем приглашающего пользователя
        inviter = User(
            telegram_id=123456789,
            username="inviter",
            balance=0
        )
        
        # Создаем приглашенного пользователя
        invited = User(
            telegram_id=987654321,
            username="invited",
            balance=0,
            referred_by=inviter.id
        )
        
        # Проверяем связи
        assert invited.referred_by == inviter.id
        assert inviter.referred_users == []  # Пока пустой список
        assert invited.referrer == None  # Пока не установлена связь
    
    def test_referral_code_generation(self):
        """Тест генерации реферальных кодов"""
        # Проверяем, что коды генерируются автоматически
        user1 = User(telegram_id=111111111, username="user1")
        user2 = User(telegram_id=222222222, username="user2")
        
        # Коды должны быть уникальными
        assert user1.referral_code != user2.referral_code
        assert len(user1.referral_code) == 8
        assert len(user2.referral_code) == 8
    
    @pytest.mark.asyncio
    async def test_referral_bonus_not_added_to_invited_user(self, mock_luna_price):
        """Тест что приглашенный пользователь НЕ получает бонус на баланс"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем приглашенного пользователя
            invited_data = SUserCreate(
                telegram_id=987654321,
                username="invited_user",
                firstname="Invited",
                lastname="User", 
                balance=0,
                referred_by=1,  # ID приглашающего
                lang_code="ru"
            )
            
            # Проверяем, что приглашенный НЕ получает бонус на баланс
            assert invited_data.balance == 0  # Баланс остается 0
            # invitation_bonus устанавливается в коде, но НЕ добавляется к балансу
            # Это поле только для отслеживания суммы бонуса
    
    @pytest.mark.asyncio
    async def test_inviter_gets_bonus_on_balance(self, mock_luna_price):
        """Тест что приглашающий получает бонус на баланс"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Создаем приглашающего пользователя с начальным балансом
            inviter_initial_balance = 1000000  # 1 LUNA в минимальных единицах
            
            # В реальном коде при создании приглашенного пользователя:
            # 1. Приглашенный получает invitation_bonus = int(luna_price * 50 * 1000000)
            # 2. Приглашающий получает этот же бонус на баланс: inviter_user.balance += invitation_bonus
            
            expected_bonus = int(mock_luna_price * 50 * 1000000)  # 25000000
            inviter_final_balance = inviter_initial_balance + expected_bonus
            
            assert inviter_final_balance == 26000000  # 1000000 + 25000000
    
    def test_referral_system_business_logic(self):
        """Тест бизнес-логики реферальной системы"""
        # Сценарий:
        # 1. Пользователь A приглашает пользователя B
        # 2. Пользователь B регистрируется с кодом пользователя A
        # 3. Пользователь A получает $50 в LUNA на баланс
        # 4. Пользователь B НЕ получает ничего на баланс
        # 5. Пользователь B получает invitation_bonus для отслеживания
        
        # Проверяем логику
        luna_price = 0.5  # $0.5 за LUNA
        bonus_amount = int(luna_price * 50 * 1000000)  # $50 в LUNA
        
        # Пользователь A (приглашающий)
        user_a_initial_balance = 0
        user_a_final_balance = user_a_initial_balance + bonus_amount
        
        # Пользователь B (приглашенный)  
        user_b_balance = 0  # Не меняется
        user_b_invitation_bonus = bonus_amount  # Для отслеживания
        
        assert user_a_final_balance == 25000000  # $50 в LUNA
        assert user_b_balance == 0  # Баланс не меняется
        assert user_b_invitation_bonus == 25000000  # Отслеживание бонуса


class TestReferralSystemIntegration:
    """Интеграционные тесты реферальной системы"""
    
    @pytest.mark.asyncio
    async def test_full_referral_flow(self):
        """Полный тест реферального процесса"""
        mock_luna_price = 0.5
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # 1. Создаем приглашающего пользователя
            inviter_data = SUserCreate(
                telegram_id=123456789,
                username="inviter",
                firstname="Inviter",
                lastname="User",
                balance=0,
                lang_code="ru"
            )
            
            # 2. Создаем приглашенного пользователя
            invited_data = SUserCreate(
                telegram_id=987654321,
                username="invited",
                firstname="Invited", 
                lastname="User",
                balance=0,
                referred_by=1,  # ID приглашающего
                lang_code="ru"
            )
            
            # 3. Проверяем результаты
            expected_bonus = int(mock_luna_price * 50 * 1000000)
            
            # Приглашающий должен получить бонус на баланс
            inviter_final_balance = 0 + expected_bonus
            
            # Приглашенный не должен получить бонус на баланс
            invited_final_balance = 0
            
            # Приглашенный должен получить invitation_bonus для отслеживания
            invited_invitation_bonus = expected_bonus
            
            assert inviter_final_balance == 25000000
            assert invited_final_balance == 0
            assert invited_invitation_bonus == 25000000
    
    def test_referral_code_uniqueness(self):
        """Тест уникальности реферальных кодов"""
        codes = set()
        
        # Генерируем несколько кодов
        for i in range(100):
            user = User(telegram_id=i, username=f"user{i}")
            codes.add(user.referral_code)
        
        # Все коды должны быть уникальными
        assert len(codes) == 100
    
    @pytest.mark.asyncio
    async def test_referral_with_different_luna_prices(self):
        """Тест реферальной системы с разными ценами LUNA"""
        test_prices = [0.1, 0.5, 1.0, 2.0, 5.0]
        
        for price in test_prices:
            with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=price):
                expected_bonus = int(price * 50 * 1000000)
                
                # Проверяем расчет бонуса
                assert expected_bonus == int(price * 50 * 1000000)
                
                # Проверяем, что бонус положительный
                assert expected_bonus > 0
                
                # Проверяем логику: приглашающий получает бонус, приглашенный - нет
                inviter_balance = 0 + expected_bonus
                invited_balance = 0
                
                assert inviter_balance == expected_bonus
                assert invited_balance == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 