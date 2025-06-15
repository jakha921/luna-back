# Luna Terra Backend

## Usage
1. Install poetry: `pip install poetry`
2. Install dependencies: `poetry install`
3. To start: `gunicorn src.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --log-level=debug --timeout=60`
4. Automatic interactive documentation with Swagger UI (from the OpenAPI backend): `http://localhost:8000/docs`

## Backend local development, additional details

### Migrations
Run the alembic `migrate` command to apply schema to your newly created database (at `db:5432`)

Generate migrations if not present, skip if migrations present
```console
$ alembic revision --autogenerate -m "message"

```
```console
$ alembic upgrade head
```

### Poetry packages
To add more packages to poetry use `poetry add {package_name}`