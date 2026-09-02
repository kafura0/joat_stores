#!/bin/bash
# JOAT Stores - Debug Scripts (Bash)
# Usage: bash scripts/debug.sh [command]

set -e

COMMAND=${1:-help}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

print_ok() {
    echo -e "${GREEN}  OK: $1${NC}"
}

print_fail() {
    echo -e "${RED}  FAIL: $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  WARNING: $1${NC}"
}

case $COMMAND in
    help)
        print_header "JOAT Stores - Debug Scripts"
        echo ""
        echo "Usage: bash scripts/debug.sh [command]"
        echo ""
        echo "Commands:"
        echo "  check       - Run all checks (lint + syntax + imports)"
        echo "  lint        - Run Python linting"
        echo "  format      - Auto-format Python code"
        echo "  test        - Run tests locally"
        echo "  test-docker - Run tests in Docker"
        echo "  migrate     - Run database migrations"
        echo "  seed        - Seed demo data"
        echo "  shell       - Open Django shell"
        echo "  health      - Check application health"
        echo "  models      - List all Django models"
        echo "  urls        - List all API URLs"
        echo "  syntax      - Check Python syntax"
        echo "  imports     - Check imports"
        echo "  full        - Run full health check"
        ;;

    check)
        print_header "Running All Checks"
        
        print_header "[1/4] Python Syntax"
        python -m py_compile apps/store/models.py && print_ok "store/models.py" || print_fail "store/models.py"
        python -m py_compile apps/product/models.py && print_ok "product/models.py" || print_fail "product/models.py"
        python -m py_compile apps/order/models.py && print_ok "order/models.py" || print_fail "order/models.py"
        python -m py_compile apps/payment/models.py && print_ok "payment/models.py" || print_fail "payment/models.py"
        python -m py_compile apps/restaurant/models.py && print_ok "restaurant/models.py" || print_fail "restaurant/models.py"
        python -m py_compile apps/bar/models.py && print_ok "bar/models.py" || print_fail "bar/models.py"
        
        print_header "[2/4] Linting"
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && print_ok "flake8 passed" || print_fail "flake8 failed"
        
        print_header "[3/4] Formatting"
        black --check . && print_ok "black passed" || print_warn "black: code needs formatting"
        isort --check-only . && print_ok "isort passed" || print_warn "isort: imports need sorting"
        
        print_header "[4/4] Import Check"
        cd backend
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from apps.store.models import Store
from apps.product.models import Product
from apps.order.models import Order
print('All key imports successful')
" && print_ok "Imports OK" || print_fail "Import failed"
        cd ..
        
        print_header "Checks Complete"
        ;;

    lint)
        print_header "Running Linting"
        flake8 . --count --statistics
        ;;

    format)
        print_header "Formatting Code"
        black .
        isort .
        print_ok "Code formatted"
        ;;

    test)
        print_header "Running Tests"
        print_warn "Requires PostgreSQL on localhost:5432"
        cd backend
        python -m pytest -v --tb=short ${@:2}
        ;;

    test-docker)
        print_header "Running Tests in Docker"
        docker compose exec django python manage.py test ${@:2}
        ;;

    migrate)
        print_header "Running Migrations"
        cd backend
        python manage.py migrate
        ;;

    seed)
        print_header "Seeding Demo Data"
        cd backend
        python manage.py seed_demo --reset
        ;;

    shell)
        print_header "Opening Django Shell"
        cd backend
        python manage.py shell_plus
        ;;

    health)
        print_header "Health Check"
        
        echo "[1/4] Database"
        cd backend
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('PostgreSQL connected')
" && print_ok "Database OK" || print_fail "Database connection failed"
        
        echo "[2/4] Redis"
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from django.core.cache import cache
cache.set('test', 'ok', 10)
assert cache.get('test') == 'ok'
print('Redis connected')
" && print_ok "Redis OK" || print_fail "Redis connection failed"
        
        echo "[3/4] Django Setup"
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
print('Django configured')
" && print_ok "Django OK" || print_fail "Django setup failed"
        
        echo "[4/4] Models"
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from django.apps import apps
models = apps.get_models()
print(f'{len(models)} models loaded')
" && print_ok "Models OK" || print_fail "Models failed"
        
        cd ..
        ;;

    models)
        print_header "Django Models"
        cd backend
        python manage.py show_models
        cd ..
        ;;

    urls)
        print_header "URL Patterns"
        cd backend
        python manage.py show_urls
        cd ..
        ;;

    syntax)
        print_header "Python Syntax Check"
        find apps -name "*.py" -not -path "*/migrations/*" -exec python -m py_compile {} \; && print_ok "All files OK" || print_fail "Syntax errors found"
        ;;

    imports)
        print_header "Import Check"
        cd backend
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

# Check all apps
apps_to_check = [
    'store', 'product', 'order', 'payment',
    'restaurant', 'bar', 'contracting',
    'saas', 'analytics', 'ai', 'loyalty',
    'notifications', 'users'
]

for app in apps_to_check:
    try:
        __import__(f'apps.{app}.models')
        print(f'  {app}: OK')
    except Exception as e:
        print(f'  {app}: FAIL - {e}')
"
        cd ..
        ;;

    full)
        print_header "FULL HEALTH CHECK"
        
        # Track results
        PASSED=0
        FAILED=0
        
        echo ""
        echo "Running syntax check..."
        python -m py_compile backend/apps/store/models.py 2>/dev/null && { print_ok "Syntax"; PASSED=$((PASSED+1)); } || { print_fail "Syntax"; FAILED=$((FAILED+1)); }
        
        echo ""
        echo "Running linting..."
        flake8 . --count --select=E9,F63,F7,F82 2>/dev/null && { print_ok "Linting"; PASSED=$((PASSED+1)); } || { print_fail "Linting"; FAILED=$((FAILED+1)); }
        
        echo ""
        echo "Checking database..."
        cd backend
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
" 2>/dev/null && { print_ok "Database"; PASSED=$((PASSED+1)); } || { print_fail "Database"; FAILED=$((FAILED+1)); }
        
        echo ""
        echo "Checking Redis..."
        python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()
from django.core.cache import cache
cache.set('test', 'ok', 10)
" 2>/dev/null && { print_ok "Redis"; PASSED=$((PASSED+1)); } || { print_fail "Redis"; FAILED=$((FAILED+1)); }
        
        cd ..
        
        echo ""
        print_header "SUMMARY"
        echo "  Passed: $PASSED"
        echo "  Failed: $FAILED"
        
        if [ $FAILED -eq 0 ]; then
            echo -e "\n${GREEN}ALL CHECKS PASSED${NC}"
        else
            echo -e "\n${RED}SOME CHECKS FAILED${NC}"
        fi
        ;;

    *)
        print_fail "Unknown command: $COMMAND"
        echo "Run 'bash scripts/debug.sh help' for usage"
        ;;
esac

echo ""
