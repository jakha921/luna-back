"""
Тесты для системы синхронизации балансов.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from redis.asyncio import Redis

from src.tasks.balance_sync import (
    sync_balances_task,
    cleanup_old_balances_task,
    health_check_task,
    _sync_balances_async,
    _get_redis_balances,
    _health_check_async
)
from src.utils.sync_utils import (
    BalanceSyncManager,
    get_balance_sync_summary,
    force_balance_sync,
    get_sync_schedule_info
)


class TestBalanceSyncTasks:
    """Тесты для задач синхронизации балансов."""
    
    @pytest.fixture
    def mock_redis_data(self):
        """Мок данных из Redis."""
        return {
            "123456789": "1000000",
            "987654321": "2500000",
            "555666777": "500000"
        }
    
    @pytest.fixture
    def mock_sync_result(self):
        """Мок результата синхронизации."""
        return {
            "updated_count": 3,
            "not_found_count": 0,
            "error_count": 0
        }
    
    @patch('src.tasks.balance_sync._sync_balances_async')
    def test_sync_balances_task_success(self, mock_sync_async, mock_sync_result):
        """Тест успешного выполнения задачи синхронизации."""
        # Настраиваем мок
        mock_sync_async.return_value = mock_sync_result
        
        # Выполняем задачу
        result = sync_balances_task(force_sync=False)
        
        # Проверяем результат
        assert result == mock_sync_result
        mock_sync_async.assert_called_once_with(False)
    
    @patch('src.tasks.balance_sync._sync_balances_async')
    def test_sync_balances_task_with_errors(self, mock_sync_async):
        """Тест выполнения задачи с ошибками."""
        # Настраиваем мок с ошибками
        mock_sync_async.return_value = {
            "status": "completed_with_errors",
            "error_count": 2,
            "updated_count": 1
        }
        
        # Выполняем задачу
        result = sync_balances_task(force_sync=True)
        
        # Проверяем результат
        assert result["status"] == "completed_with_errors"
        assert result["error_count"] == 2
        mock_sync_async.assert_called_once_with(True)
    
    @patch('src.tasks.balance_sync._get_redis_balances')
    @patch('src.tasks.balance_sync.get_session')
    @patch('src.tasks.balance_sync.UserRepository')
    @pytest.mark.asyncio
    async def test_sync_balances_async_success(
        self, 
        mock_user_repo, 
        mock_session, 
        mock_get_redis_balances,
        mock_redis_data,
        mock_sync_result
    ):
        """Тест успешной асинхронной синхронизации."""
        # Настраиваем моки
        mock_get_redis_balances.return_value = mock_redis_data
        
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        mock_repo_instance = MagicMock()
        mock_repo_instance.sync_balances_from_redis.return_value = mock_sync_result
        mock_user_repo.return_value = mock_repo_instance
        
        # Выполняем синхронизацию
        result = await _sync_balances_async(force_sync=False)
        
        # Проверяем результат
        assert result["status"] == "completed"
        assert result["redis_keys_found"] == 3
        assert result["updated_count"] == 3
        assert result["error_count"] == 0
    
    @patch('src.tasks.balance_sync._get_redis_balances')
    @pytest.mark.asyncio
    async def test_sync_balances_async_no_data(self, mock_get_redis_balances):
        """Тест синхронизации без данных в Redis."""
        # Настраиваем мок - нет данных
        mock_get_redis_balances.return_value = {}
        
        # Выполняем синхронизацию
        result = await _sync_balances_async(force_sync=False)
        
        # Проверяем результат
        assert result["status"] == "completed"
        assert result["redis_keys_found"] == 0
        assert result["total_processed"] == 0
    
    @patch('src.tasks.balance_sync.Redis')
    @pytest.mark.asyncio
    async def test_get_redis_balances_success(self, mock_redis_class, mock_redis_data):
        """Тест получения балансов из Redis."""
        # Настраиваем мок Redis
        mock_redis_instance = AsyncMock()
        mock_redis_instance.keys.return_value = ["123456789", "987654321", "555666777"]
        mock_redis_instance.mget.return_value = ["1000000", "2500000", "500000"]
        mock_redis_class.return_value = mock_redis_instance
        
        # Выполняем получение балансов
        result = await _get_redis_balances()
        
        # Проверяем результат
        assert result == mock_redis_data
        mock_redis_instance.close.assert_called_once()
    
    def test_health_check_task_success(self):
        """Тест успешной проверки здоровья."""
        # Настраиваем мок
        with patch('src.tasks.balance_sync._health_check_async') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "checks": {
                    "redis": "ok",
                    "database": "ok"
                }
            }
            
            # Выполняем проверку здоровья
            result = health_check_task()
            
            # Проверяем результат
            assert result["status"] == "healthy"
            assert result["checks"]["redis"] == "ok"
            assert result["checks"]["database"] == "ok"


class TestBalanceSyncUtils:
    """Тесты для утилит синхронизации."""
    
    @patch('src.utils.sync_utils.Redis')
    async def test_balance_sync_manager_connect(self, mock_redis_class):
        """Тест подключения менеджера синхронизации."""
        # Настраиваем мок Redis
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        
        # Создаем менеджер
        async with BalanceSyncManager() as manager:
            assert manager.redis_client is not None
            mock_redis_instance.ping.assert_called_once()
    
    @patch('src.utils.sync_utils.Redis')
    async def test_get_sync_status(self, mock_redis_class):
        """Тест получения статуса синхронизации."""
        # Настраиваем мок Redis
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.side_effect = [
            "2024-01-01T12:00:00",  # last_sync
            '{"updated_count": 10}'  # stats
        ]
        mock_redis_class.return_value = mock_redis_instance
        
        # Получаем статус
        async with BalanceSyncManager() as manager:
            status = await manager.get_sync_status()
            
            # Проверяем результат
            assert status["redis_connected"] is True
            assert "last_sync_time" in status
            assert "last_sync_stats" in status
    
    def test_get_sync_schedule_info(self):
        """Тест получения информации о расписании."""
        # Получаем информацию о расписании
        schedule_info = get_sync_schedule_info()
        
        # Проверяем структуру
        assert "hourly_sync" in schedule_info
        assert "daily_sync" in schedule_info
        assert "cleanup_task" in schedule_info
        assert "health_check" in schedule_info
        
        # Проверяем детали
        hourly_sync = schedule_info["hourly_sync"]
        assert hourly_sync["enabled"] is True
        assert "schedule" in hourly_sync
        assert "task" in hourly_sync
    
    @patch('src.utils.sync_utils.sync_balances_task')
    async def test_force_balance_sync(self, mock_sync_task):
        """Тест принудительной синхронизации."""
        # Настраиваем мок задачи
        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        mock_sync_task.delay.return_value = mock_result
        
        # Выполняем принудительную синхронизацию
        result = await force_balance_sync()
        
        # Проверяем результат
        assert result["status"] == "started"
        assert result["task_id"] == "test-task-id"
        mock_sync_task.delay.assert_called_once_with(force_sync=True)


class TestBalanceSyncIntegration:
    """Интеграционные тесты синхронизации."""
    
    @pytest.mark.asyncio
    async def test_full_sync_flow(self):
        """Тест полного процесса синхронизации."""
        # Мокаем все зависимости
        with patch('src.tasks.balance_sync._get_redis_balances') as mock_get_balances, \
             patch('src.tasks.balance_sync.get_session') as mock_session, \
             patch('src.tasks.balance_sync.UserRepository') as mock_user_repo:
            
            # Настраиваем моки
            mock_get_balances.return_value = {
                "123456789": "1000000",
                "987654321": "2500000"
            }
            
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_repo_instance = MagicMock()
            mock_repo_instance.sync_balances_from_redis.return_value = {
                "updated_count": 2,
                "not_found_count": 0,
                "error_count": 0
            }
            mock_user_repo.return_value = mock_repo_instance
            
            # Выполняем синхронизацию
            result = await _sync_balances_async(force_sync=False)
            
            # Проверяем результат
            assert result["status"] == "completed"
            assert result["redis_keys_found"] == 2
            assert result["updated_count"] == 2
            assert result["error_count"] == 0
            assert "sync_duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_sync_with_redis_error(self):
        """Тест синхронизации с ошибкой Redis."""
        # Мокаем ошибку Redis
        with patch('src.tasks.balance_sync._get_redis_balances') as mock_get_balances:
            mock_get_balances.side_effect = Exception("Redis connection error")
            
            # Выполняем синхронизацию
            result = await _sync_balances_async(force_sync=False)
            
            # Проверяем результат
            assert result["status"] == "error"
            assert "error_message" in result
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Интеграционный тест проверки здоровья."""
        # Мокаем Redis и базу данных
        with patch('src.tasks.balance_sync.Redis') as mock_redis_class, \
             patch('src.tasks.balance_sync.get_session') as mock_session:
            
            # Настраиваем мок Redis
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.keys.return_value = ["key1", "key2"]
            mock_redis_class.return_value = mock_redis_instance
            
            # Настраиваем мок сессии БД
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_execute_result = MagicMock()
            mock_session_instance.execute.return_value = mock_execute_result
            
            # Выполняем проверку здоровья
            result = await _health_check_async()
            
            # Проверяем результат
            assert result["status"] == "healthy"
            assert result["checks"]["redis"] == "ok"
            assert result["checks"]["database"] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 