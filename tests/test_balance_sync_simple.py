"""
Упрощенные тесты для системы синхронизации балансов.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from src.tasks.celery_app import celery_app
from src.utils.sync_utils import get_sync_schedule_info


class TestCeleryApp:
    """Тесты конфигурации Celery приложения."""
    
    def test_celery_app_configured(self):
        """Тест что Celery приложение правильно настроено."""
        assert celery_app is not None
        assert celery_app.conf.get('task_serializer') == 'json'
        assert celery_app.conf.get('accept_content') == ['json']
        assert celery_app.conf.get('result_serializer') == 'json'
    
    def test_celery_app_has_tasks(self):
        """Тест что в Celery приложении есть задачи."""
        registered_tasks = celery_app.tasks.keys()
        assert 'src.tasks.balance_sync.sync_balances_task' in registered_tasks
        assert 'src.tasks.balance_sync.health_check_task' in registered_tasks
    
    def test_celery_app_has_beat_schedule(self):
        """Тест что настроено расписание задач."""
        beat_schedule = celery_app.conf.get('beat_schedule', {})
        assert 'sync-balances-hourly' in beat_schedule
        assert 'sync-balances-daily' in beat_schedule


class TestSyncUtils:
    """Тесты утилит синхронизации."""
    
    def test_get_sync_schedule_info(self):
        """Тест получения информации о расписании."""
        schedule_info = get_sync_schedule_info()
        
        # Проверяем структуру
        assert isinstance(schedule_info, dict)
        assert 'hourly_sync' in schedule_info
        assert 'daily_sync' in schedule_info
        assert 'cleanup_task' in schedule_info
        assert 'health_check' in schedule_info
        
        # Проверяем детали
        hourly_sync = schedule_info['hourly_sync']
        assert hourly_sync['enabled'] is True
        assert 'schedule' in hourly_sync
        assert 'task' in hourly_sync
        
        daily_sync = schedule_info['daily_sync']
        assert daily_sync['enabled'] is True
        assert 'schedule' in daily_sync
        assert 'task' in daily_sync


class TestBalanceSyncTasks:
    """Тесты задач синхронизации."""
    
    @patch('src.tasks.balance_sync._sync_balances_async')
    def test_sync_balances_task_success(self, mock_sync_async):
        """Тест успешного выполнения задачи синхронизации."""
        # Настраиваем мок
        mock_sync_async.return_value = {
            "status": "completed",
            "updated_count": 3,
            "error_count": 0
        }
        
        # Выполняем задачу
        result = sync_balances_task(force_sync=False)
        
        # Проверяем результат
        assert result["status"] == "completed"
        assert result["updated_count"] == 3
        assert result["error_count"] == 0
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


class TestBalanceSyncIntegration:
    """Интеграционные тесты синхронизации."""
    
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


# Импорты для тестов
from src.tasks.balance_sync import (
    sync_balances_task,
    health_check_task,
    _sync_balances_async,
    _health_check_async
)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 