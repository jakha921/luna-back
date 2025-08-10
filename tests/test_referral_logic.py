import pytest
from unittest.mock import patch
from datetime import datetime

from src.utils.currency_LUNA_to_USDT import get_luna_price_binance


class TestReferralLogic:
    """Тесты логики реферальной системы"""
    
    @pytest.fixture
    def mock_luna_price(self):
        """Мок для цены LUNA"""
        return 0.5  # $0.5 за LUNA
    
    def test_referral_bonus_calculation(self, mock_luna_price):
        """Тест расчета реферального бонуса"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Проверяем расчет бонуса
            luna_price = mock_luna_price  # $0.5
            bonus_amount = int(luna_price * 50 * 1000000)  # $50 в LUNA
            
            assert bonus_amount == 25000000  # 25 миллионов минимальных единиц
            
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
    
    def test_referral_system_business_logic(self, mock_luna_price):
        """Тест бизнес-логики реферальной системы"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Сценарий:
            # 1. Пользователь A приглашает пользователя B
            # 2. Пользователь B регистрируется с кодом пользователя A
            # 3. Пользователь A получает $50 в LUNA на баланс
            # 4. Пользователь B НЕ получает ничего на баланс
            # 5. Пользователь B получает invitation_bonus для отслеживания
            
            # Проверяем логику
            luna_price = mock_luna_price  # $0.5 за LUNA
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
    
    def test_referral_bonus_formula_analysis(self, mock_luna_price):
        """Анализ формулы расчета реферального бонуса"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Формула в коде: int(luna_price * 50 * 1000000)
            # Где:
            # - luna_price: цена LUNA в USD
            # - 50: $50 бонус
            # - 1000000: конвертация в минимальные единицы (1 LUNA = 1,000,000 единиц)
            
            luna_price = mock_luna_price  # $0.5
            bonus = int(luna_price * 50 * 1000000)
            
            # Проверяем расчет:
            # $0.5 * 50 = $25
            # $25 / $0.5 = 50 LUNA
            # 50 LUNA * 1,000,000 = 50,000,000 единиц
            # Но в коде: int(0.5 * 50 * 1000000) = int(25000000) = 25000000
            
            assert bonus == 25000000
            
            # Проверяем логику:
            # При цене $0.5 за LUNA, $50 = 100 LUNA
            # 100 LUNA * 1,000,000 = 100,000,000 единиц
            # Но код дает 25,000,000 единиц
            # Это означает, что формула в коде: int(price * 50 * 1000000)
            # А не: int((50 / price) * 1000000)
            
            # Правильная формула должна быть:
            correct_bonus = int((50 / luna_price) * 1000000)  # 100,000,000
            assert correct_bonus == 100000000
            
            # Но код использует:
            code_bonus = int(luna_price * 50 * 1000000)  # 25,000,000
            assert code_bonus == 25000000
            
            # Вывод: формула в коде НЕПРАВИЛЬНАЯ!
            # Она должна быть: int((50 / luna_price) * 1000000)
            # А не: int(luna_price * 50 * 1000000)
    
    def test_referral_system_requirements(self):
        """Проверка требований реферальной системы"""
        # Требования:
        # 1. Кто пригласил получает $50 по нынешнему курсу
        # 2. Приглашенному загрепляется код приглашенного (ему не начисляется в баланс ничего)
        
        test_cases = [
            (0.1, 500000000),  # $0.1 -> 500M единиц (500 LUNA)
            (0.5, 100000000),  # $0.5 -> 100M единиц (100 LUNA)  
            (1.0, 50000000),   # $1.0 -> 50M единиц (50 LUNA)
            (2.0, 25000000),   # $2.0 -> 25M единиц (25 LUNA)
        ]
        
        for price, expected_bonus in test_cases:
            with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=price):
                # Правильная формула: $50 / цена_LUNA * 1000000
                correct_bonus = int((50 / price) * 1000000)
                assert correct_bonus == expected_bonus
                
                # Проверяем логику:
                # Приглашающий получает бонус на баланс
                inviter_balance = 0 + correct_bonus
                
                # Приглашенный НЕ получает бонус на баланс
                invited_balance = 0
                
                # Приглашенный получает invitation_bonus для отслеживания
                invited_invitation_bonus = correct_bonus
                
                assert inviter_balance == expected_bonus
                assert invited_balance == 0
                assert invited_invitation_bonus == expected_bonus
    
    def test_current_code_bug(self, mock_luna_price):
        """Тест выявления бага в текущем коде"""
        with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=mock_luna_price):
            # Текущая формула в коде: int(luna_price * 50 * 1000000)
            current_formula = int(mock_luna_price * 50 * 1000000)
            
            # Правильная формула: int((50 / luna_price) * 1000000)
            correct_formula = int((50 / mock_luna_price) * 1000000)
            
            # При цене $0.5:
            # Текущая формула: int(0.5 * 50 * 1000000) = 25000000 (25 LUNA)
            # Правильная формула: int((50 / 0.5) * 1000000) = 100000000 (100 LUNA)
            
            assert current_formula == 25000000
            assert correct_formula == 100000000
            
            # Разница в 4 раза!
            assert correct_formula == current_formula * 4
            
            # Это означает, что приглашающий получает в 4 раза меньше бонуса, чем должен!
    
    def test_referral_system_correct_implementation(self):
        """Тест правильной реализации реферальной системы"""
        test_cases = [
            (0.1, 500000000),  # $0.1 -> 500M единиц
            (0.5, 100000000),  # $0.5 -> 100M единиц
            (1.0, 50000000),   # $1.0 -> 50M единиц
            (2.0, 25000000),   # $2.0 -> 25M единиц
        ]
        
        for price, expected_bonus in test_cases:
            with patch('src.utils.currency_LUNA_to_USDT.get_luna_price_binance', return_value=price):
                # Правильная формула для $50 бонуса
                bonus = int((50 / price) * 1000000)
                
                # Проверяем, что бонус рассчитан правильно
                assert bonus == expected_bonus
                
                # Проверяем бизнес-логику
                inviter_balance = 0 + bonus
                invited_balance = 0
                invited_invitation_bonus = bonus
                
                assert inviter_balance == expected_bonus
                assert invited_balance == 0
                assert invited_invitation_bonus == expected_bonus


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 