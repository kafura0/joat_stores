@echo off
REM JOAT Stores - Local Development Scripts
REM Usage: scripts\debug.bat [command]

setlocal enabledelayedexpansion

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="check" goto :check
if "%1"=="lint" goto :lint
if "%1"=="format" goto :format
if "%1"=="test" goto :test
if "%1"=="test-docker" goto :test-docker
if "%1"=="migrate" goto :migrate
if "%1"=="seed" goto :seed
if "%1"=="shell" goto :shell
if "%1"=="health" goto :health
if "%1"=="urls" goto :urls
if "%1"=="models" goto :models
if "%1"=="celery" goto :celery
if "%1"=="redis" goto :redis
if "%1"=="db" goto :db
goto :help

:help
echo.
echo JOAT Stores - Debug Scripts
echo ===========================
echo.
echo Usage: scripts\debug.bat [command]
echo.
echo Commands:
echo   check       - Run all checks (lint + typecheck + syntax)
echo   lint        - Run Python linting (flake8 + black + isort)
echo   format      - Auto-format Python code
echo   test        - Run tests locally (requires PostgreSQL)
echo   test-docker - Run tests in Docker
echo   migrate     - Run database migrations
echo   seed        - Seed demo data
echo   shell       - Open Django shell
echo   health      - Check application health
echo   urls        - List all API URLs
echo   models      - List all Django models
echo   celery      - Check Celery worker status
echo   redis       - Check Redis connection
echo   db          - Check database connection
echo.
goto :eof

:check
echo.
echo Running all checks...
echo =====================
echo.

echo [1/3] Python linting...
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
if %errorlevel% neq 0 (
    echo ERROR: Linting failed
    exit /b 1
)

echo [2/3] Python formatting check...
black --check .
if %errorlevel% neq 0 (
    echo WARNING: Code needs formatting. Run 'black .' to fix
)

echo [3/3] Import sorting check...
isort --check-only .
if %errorlevel% neq 0 (
    echo WARNING: Imports need sorting. Run 'isort .' to fix
)

echo.
echo All checks passed!
goto :eof

:lint
echo.
echo Running flake8...
echo ================
flake8 . --count --statistics
goto :eof

:format
echo.
echo Formatting Python code...
echo ========================
echo Running black...
black .
echo Running isort...
isort .
echo Done!
goto :eof

:test
echo.
echo Running tests locally...
echo ======================
echo WARNING: Requires PostgreSQL running on localhost:5432
echo.
python -m pytest -v --tb=short %2 %3 %4 %5
goto :eof

:test-docker
echo.
echo Running tests in Docker...
echo =========================
docker compose exec django python manage.py test %2 %3 %4 %5
goto :eof

:migrate
echo.
echo Running migrations...
echo ===================
python manage.py migrate
goto :eof

:seed
echo.
echo Seeding demo data...
echo ===================
python manage.py seed_demo --reset
goto :eof

:shell
echo.
echo Opening Django shell...
echo =====================
python manage.py shell_plus
goto :eof

:health
echo.
echo Checking application health...
echo =============================
echo.

echo [1/4] Database connection...
python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); print('  OK: PostgreSQL connected')" 2>nul
if %errorlevel% neq 0 (
    echo  FAIL: Cannot connect to PostgreSQL
)

echo [2/4] Redis connection...
python -c "from django.core.cache import cache; cache.set('test', 'ok', 10); print('  OK: Redis connected')" 2>nul
if %errorlevel% neq 0 (
    echo  FAIL: Cannot connect to Redis
)

echo [3/4] Celery worker...
python -c "import socket; s = socket.socket(); s.connect(('localhost', 6379)); s.close(); print('  OK: Redis port open')" 2>nul
if %errorlevel% neq 0 (
    echo  FAIL: Redis not accessible
)

echo [4/4] Django settings...
python -c "import django; django.setup(); print('  OK: Django configured')" 2>nul
if %errorlevel% neq 0 (
    echo  FAIL: Django setup failed
)

echo.
goto :eof

:urls
echo.
echo Listing all API URLs...
echo =====================
python manage.py show_urls | sort
goto :eof

:models
echo.
echo Listing all Django models...
echo ==========================
python manage.py show_models
goto :eof

:celery
echo.
echo Checking Celery workers...
echo =========================
docker compose exec django celery -A config.celery_app inspect active
goto :eof

:redis
echo.
echo Checking Redis...
echo ================
docker compose exec redis redis-cli ping
goto :eof

:db
echo.
echo Checking database...
echo ===================
python -c "from django.db import connection; print(f'Database: {connection.settings_dict[\"NAME\"]}'); print(f'Host: {connection.settings_dict[\"HOST\"]}:{connection.settings_dict[\"PORT\"]}')"
goto :eof
