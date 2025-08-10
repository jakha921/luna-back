"""
Тесты для management команд синхронизации балансов.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from click.testing import CliRunner

from src.management.commands.sync_balances import (
    sync_balances,
    cleanup_old_balances,
    health_check,
    _sync_balances_async,
    _cleanup_old_balances_async,
    _health_check_async
)


class TestManagementCommands:
    """Тесты management команд."""
    
    def test_sync_balances_command_success(self):
        """Тест успешного выполнения команды синхронизации."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._sync_balances_async') as mock_sync:
            mock_sync.return_value = {
                "status": "completed",
                "updated_count": 5,
                "error_count": 0
            }
            
            result = runner.invoke(sync_balances, ['--force'])
            
            assert result.exit_code == 0
            assert "✅ Balance synchronization completed successfully!" in result.output
            mock_sync.assert_called_once_with(True, False)
    
    def test_sync_balances_command_with_errors(self):
        """Тест выполнения команды с ошибками."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._sync_balances_async') as mock_sync:
            mock_sync.return_value = {
                "status": "completed_with_errors",
                "updated_count": 2,
                "error_count": 3
            }
            
            result = runner.invoke(sync_balances, ['--force'])
            
            assert result.exit_code == 0
            assert "⚠️ Balance synchronization completed with errors!" in result.output
            mock_sync.assert_called_once_with(True, False)
    
    def test_sync_balances_command_dry_run(self):
        """Тест команды в режиме dry-run."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._sync_balances_async') as mock_sync:
            mock_sync.return_value = {
                "status": "completed",
                "dry_run": True
            }
            
            result = runner.invoke(sync_balances, ['--dry-run'])
            
            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            mock_sync.assert_called_once_with(False, True)
    
    def test_sync_balances_command_verbose(self):
        """Тест команды с подробным выводом."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._sync_balances_async') as mock_sync:
            mock_sync.return_value = {
                "status": "completed",
                "updated_count": 1
            }
            
            result = runner.invoke(sync_balances, ['--verbose'])
            
            assert result.exit_code == 0
            assert "Starting manual balance synchronization" in result.output
            mock_sync.assert_called_once_with(False, False)
    
    def test_cleanup_old_balances_command(self):
        """Тест команды очистки старых балансов."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._cleanup_old_balances_async') as mock_cleanup:
            mock_cleanup.return_value = {
                "status": "completed",
                "cleaned_keys": 10
            }
            
            result = runner.invoke(cleanup_old_balances, ['--days', '7'])
            
            assert result.exit_code == 0
            assert "✅ Cleanup completed successfully!" in result.output
            mock_cleanup.assert_called_once_with(7, False)
    
    def test_health_check_command_success(self):
        """Тест успешной команды проверки здоровья."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._health_check_async') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "checks": {
                    "redis": "ok",
                    "database": "ok"
                }
            }
            
            result = runner.invoke(health_check)
            
            assert result.exit_code == 0
            assert "✅ System is healthy!" in result.output
    
    def test_health_check_command_unhealthy(self):
        """Тест команды проверки здоровья с проблемами."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._health_check_async') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "error": "Redis connection failed"
            }
            
            result = runner.invoke(health_check)
            
            assert result.exit_code == 0
            assert "❌ System is unhealthy!" in result.output


class TestAsyncFunctions:
    """Тесты асинхронных функций."""
    
    @pytest.mark.asyncio
    async def test_sync_balances_async_success(self):
        """Тест успешной асинхронной синхронизации."""
        with patch('src.management.commands.sync_balances.get_session') as mock_session, \
             patch('src.management.commands.sync_balances.UserRepository') as mock_repo, \
             patch('src.management.commands.sync_balances.get_all_telegram_balances') as mock_get_balances:
            
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
            mock_repo.return_value = mock_repo_instance
            
            # Выполняем синхронизацию
            result = await _sync_balances_async(force_sync=False, dry_run=False)
            
            # Проверяем результат
            assert result["status"] == "completed"
            assert result["updated_count"] == 2
            assert result["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_sync_balances_async_no_data(self):
        """Тест синхронизации без данных."""
        with patch('src.management.commands.sync_balances.get_all_telegram_balances') as mock_get_balances:
            mock_get_balances.return_value = {}
            
            result = await _sync_balances_async(force_sync=False, dry_run=False)
            
            assert result["status"] == "completed"
            assert result["redis_keys_found"] == 0
    
    @pytest.mark.asyncio
    async def test_sync_balances_async_dry_run(self):
        """Тест синхронизации в режиме dry-run."""
        with patch('src.management.commands.sync_balances.get_all_telegram_balances') as mock_get_balances:
            mock_get_balances.return_value = {
                "123456789": "1000000",
                "987654321": "2500000"
            }
            
            result = await _sync_balances_async(force_sync=False, dry_run=True)
            
            assert result["status"] == "completed"
            assert result["dry_run"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_old_balances_async(self):
        """Тест асинхронной очистки старых балансов."""
        result = await _cleanup_old_balances_async(days=7, dry_run=False)
        
        assert result["status"] == "not_implemented"
        assert result["days_old"] == 7
        assert result["dry_run"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_async_success(self):
        """Тест успешной асинхронной проверки здоровья."""
        with patch('src.management.commands.sync_balances.Redis') as mock_redis_class, \
             patch('src.management.commands.sync_balances.get_session') as mock_session:
            
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
    
    @pytest.mark.asyncio
    async def test_health_check_async_unhealthy(self):
        """Тест асинхронной проверки здоровья с проблемами."""
        with patch('src.management.commands.sync_balances.Redis') as mock_redis_class:
            # Настраиваем мок Redis с ошибкой
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_redis_instance
            
            # Выполняем проверку здоровья
            result = await _health_check_async()
            
            # Проверяем результат
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestErrorHandling:
    """Тесты обработки ошибок."""
    
    def test_sync_balances_command_exception(self):
        """Тест обработки исключения в команде синхронизации."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._sync_balances_async') as mock_sync:
            mock_sync.side_effect = Exception("Database connection failed")
            
            result = runner.invoke(sync_balances, ['--force'])
            
            assert result.exit_code == 1
            assert "❌ Error during balance synchronization" in result.output
    
    def test_cleanup_command_exception(self):
        """Тест обработки исключения в команде очистки."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._cleanup_old_balances_async') as mock_cleanup:
            mock_cleanup.side_effect = Exception("Cleanup failed")
            
            result = runner.invoke(cleanup_old_balances, ['--days', '7'])
            
            assert result.exit_code == 1
            assert "❌ Error during cleanup" in result.output
    
    def test_health_check_command_exception(self):
        """Тест обработки исключения в команде проверки здоровья."""
        runner = CliRunner()
        
        with patch('src.management.commands.sync_balances._health_check_async') as mock_health:
            mock_health.side_effect = Exception("Health check failed")
            
            result = runner.invoke(health_check)
            
            assert result.exit_code == 1
            assert "❌ Error during health check" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 