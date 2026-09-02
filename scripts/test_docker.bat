@echo off
REM JOAT Stores - Docker Test Runner
REM Usage: scripts\test_docker.bat [test_type]

setlocal enabledelayedexpansion

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="all" goto :test_all
if "%1"=="unit" goto :test_unit
if "%1"=="integration" goto :test_integration
if "%1"=="cross-tenant" goto :test_cross_tenant
if "%1"=="store" goto :test_store
if "%1"=="product" goto :test_product
if "%1"=="order" goto :test_order
if "%1"=="payment" goto :test_payment
if "%1"=="restaurant" goto :test_restaurant
if "%1"=="bar" goto :test_bar
if "%1"=="contracting" goto :test_contracting
if "%1"=="saas" goto :test_saas
if "%1"=="analytics" goto :test_analytics
if "%1"=="loyalty" goto :test_loyalty
if "%1"=="users" goto :test_users
if "%1"=="coverage" goto :test_coverage
goto :help

:help
echo.
echo JOAT Stores - Docker Test Runner
echo =================================
echo.
echo Usage: scripts\test_docker.bat [test_type]
echo.
echo Test Types:
echo   all            - Run all tests
echo   unit           - Run unit tests only
echo   integration    - Run integration tests only
echo   cross-tenant   - Run cross-tenant isolation tests
echo   store          - Run store app tests
echo   product        - Run product app tests
echo   order          - Run order app tests
echo   payment        - Run payment app tests
echo   restaurant     - Run restaurant app tests
echo   bar            - Run bar app tests
echo   contracting     - Run contracting app tests
echo   saas           - Run SaaS app tests
echo   analytics      - Run analytics app tests
echo   loyalty        - Run loyalty app tests
echo   users          - Run users app tests
echo   coverage       - Run tests with coverage report
echo.
goto :eof

:test_all
echo.
echo Running all tests...
echo ===================
docker compose exec django python manage.py test -v 2 --parallel
goto :eof

:test_unit
echo.
echo Running unit tests...
echo ===================
docker compose exec django python manage.py test -v 2 -m "not integration"
goto :eof

:test_integration
echo.
echo Running integration tests...
echo ===========================
docker compose exec django python manage.py test -v 2 -m "integration"
goto :eof

:test_cross_tenant
echo.
echo Running cross-tenant isolation tests...
echo ======================================
docker compose exec django pytest -k "cross_tenant" -v
goto :eof

:test_store
echo.
echo Running store app tests...
echo =========================
docker compose exec django python manage.py test apps.store.tests -v 2
goto :eof

:test_product
echo.
echo Running product app tests...
echo ===========================
docker compose exec django python manage.py test apps.product.tests -v 2
goto :eof

:test_order
echo.
echo Running order app tests...
echo =========================
docker compose exec django python manage.py test apps.order.tests -v 2
goto :eof

:test_payment
echo.
echo Running payment app tests...
echo ===========================
docker compose exec django python manage.py test apps.payment.tests -v 2
goto :eof

:test_restaurant
echo.
echo Running restaurant app tests...
echo ===============================
docker compose exec django python manage.py test apps.restaurant.tests -v 2
goto :eof

:test_bar
echo.
echo Running bar app tests...
echo =======================
docker compose exec django python manage.py test apps.bar.tests -v 2
goto :eof

:test_contracting
echo.
echo Running contracting app tests...
echo =================================
docker compose exec django python manage.py test apps.contracting.tests -v 2
goto :eof

:test_saas
echo.
echo Running SaaS app tests...
echo ========================
docker compose exec django python manage.py test apps.saas.tests -v 2
goto :eof

:test_analytics
echo.
echo Running analytics app tests...
echo =============================
docker compose exec django python manage.py test apps.analytics.tests -v 2
goto :eof

:test_loyalty
echo.
echo Running loyalty app tests...
echo ===========================
docker compose exec django python manage.py test apps.loyalty.tests -v 2
goto :eof

:test_users
echo.
echo Running users app tests...
echo =========================
docker compose exec django python manage.py test apps.users.tests -v 2
goto :eof

:test_coverage
echo.
echo Running tests with coverage...
echo =============================
docker compose exec django python manage.py test --parallel --coverage=apps --cov-report=html --cov-report=term
goto :eof
