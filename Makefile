# Makefile для Luna Terra Backend

.PHONY: help install test run docker-up docker-down seed-data clear-data reset-data

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Показать справку
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Установить зависимости
	@echo "$(GREEN)Установка зависимостей...$(NC)"
	poetry install

test: ## Запустить тесты
	@echo "$(GREEN)Запуск тестов...$(NC)"
	poetry run pytest tests/ -v

run: ## Запустить приложение локально
	@echo "$(GREEN)Запуск приложения...$(NC)"
	poetry run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

docker-up: ## Запустить Docker Compose
	@echo "$(GREEN)Запуск Docker Compose...$(NC)"
	docker-compose up -d

docker-down: ## Остановить Docker Compose
	@echo "$(GREEN)Остановка Docker Compose...$(NC)"
	docker-compose down

docker-logs: ## Показать логи Docker
	@echo "$(GREEN)Логи Docker Compose:$(NC)"
	docker-compose logs -f

docker-restart: ## Перезапустить Docker Compose
	@echo "$(GREEN)Перезапуск Docker Compose...$(NC)"
	docker-compose down
	docker-compose up -d

seed-data: ## Заполнить базу данных тестовыми данными
	@echo "$(GREEN)Заполнение базы данных тестовыми данными...$(NC)"
	docker-compose exec app python scripts/seed_simple.py

seed-data-large: ## Заполнить базу данных большим количеством данных
	@echo "$(GREEN)Заполнение базы данных большим количеством данных...$(NC)"
	docker-compose exec app python scripts/seed_simple.py

seed-data-small: ## Заполнить базу данных небольшим количеством данных
	@echo "$(GREEN)Заполнение базы данных небольшим количеством данных...$(NC)"
	docker-compose exec app python scripts/seed_simple.py

clear-data: ## Очистить базу данных
	@echo "$(RED)Очистка базы данных...$(NC)"
	poetry run python scripts/clear_data.py --confirm

reset-data: ## Очистить и заполнить базу данных заново
	@echo "$(YELLOW)Сброс и заполнение базы данных...$(NC)"
	poetry run python scripts/clear_data.py --confirm
	poetry run python scripts/seed_data.py --users 100

check-api: ## Проверить работоспособность API
	@echo "$(GREEN)Проверка API...$(NC)"
	@curl -s http://localhost:8000/ | grep -q "LunaTerra API" && echo "$(GREEN)✅ API работает$(NC)" || echo "$(RED)❌ API не отвечает$(NC)"
	@curl -s http://localhost:8000/api/user | jq '.data | length' 2>/dev/null && echo "$(GREEN)✅ API endpoints работают$(NC)" || echo "$(RED)❌ API endpoints не работают$(NC)"

check-docker: ## Проверить статус Docker контейнеров
	@echo "$(GREEN)Статус Docker контейнеров:$(NC)"
	docker-compose ps

check-db: ## Проверить подключение к базе данных
	@echo "$(GREEN)Проверка подключения к базе данных...$(NC)"
	docker-compose exec db pg_isready -U postgres -d luna_terra

check-redis: ## Проверить подключение к Redis
	@echo "$(GREEN)Проверка подключения к Redis...$(NC)"
	docker-compose exec cache redis-cli -a hfiuwhe287498jIWUfhwoif ping

setup: ## Полная настройка проекта
	@echo "$(GREEN)Полная настройка проекта...$(NC)"
	$(MAKE) install
	$(MAKE) docker-up
	@echo "$(YELLOW)Ожидание запуска сервисов...$(NC)"
	@sleep 30
	$(MAKE) seed-data
	$(MAKE) check-api

dev: ## Запуск в режиме разработки
	@echo "$(GREEN)Запуск в режиме разработки...$(NC)"
	$(MAKE) docker-up
	$(MAKE) run

clean: ## Очистка проекта
	@echo "$(GREEN)Очистка проекта...$(NC)"
	docker-compose down -v
	docker system prune -f
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
