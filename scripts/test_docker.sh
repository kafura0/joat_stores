#!/bin/bash
# JOAT Stores - Docker Test Runner (Bash)
# Usage: bash scripts/test_docker.sh [test_type]

set -e

COMMAND=${1:-help}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

case $COMMAND in
    help)
        print_header "JOAT Stores - Docker Test Runner"
        echo ""
        echo "Usage: bash scripts/test_docker.sh [test_type]"
        echo ""
        echo "Test Types:"
        echo "  all            - Run all tests"
        echo "  unit           - Run unit tests only"
        echo "  integration    - Run integration tests only"
        echo "  cross-tenant   - Run cross-tenant isolation tests"
        echo "  store          - Run store app tests"
        echo "  product        - Run product app tests"
        echo "  order          - Run order app tests"
        echo "  payment        - Run payment app tests"
        echo "  restaurant     - Run restaurant app tests"
        echo "  bar            - Run bar app tests"
        echo "  contracting     - Run contracting app tests"
        echo "  saas           - Run SaaS app tests"
        echo "  analytics      - Run analytics app tests"
        echo "  loyalty        - Run loyalty app tests"
        echo "  users          - Run users app tests"
        echo "  coverage       - Run tests with coverage report"
        ;;

    all)
        print_header "Running All Tests"
        docker compose exec django python manage.py test -v 2 --parallel
        ;;

    unit)
        print_header "Running Unit Tests"
        docker compose exec django python manage.py test -v 2 -m "not integration"
        ;;

    integration)
        print_header "Running Integration Tests"
        docker compose exec django python manage.py test -v 2 -m "integration"
        ;;

    cross-tenant)
        print_header "Running Cross-Tenant Isolation Tests"
        docker compose exec django pytest -k "cross_tenant" -v
        ;;

    store)
        print_header "Running Store App Tests"
        docker compose exec django python manage.py test apps.store.tests -v 2
        ;;

    product)
        print_header "Running Product App Tests"
        docker compose exec django python manage.py test apps.product.tests -v 2
        ;;

    order)
        print_header "Running Order App Tests"
        docker compose exec django python manage.py test apps.order.tests -v 2
        ;;

    payment)
        print_header "Running Payment App Tests"
        docker compose exec django python manage.py test apps.payment.tests -v 2
        ;;

    restaurant)
        print_header "Running Restaurant App Tests"
        docker compose exec django python manage.py test apps.restaurant.tests -v 2
        ;;

    bar)
        print_header "Running Bar App Tests"
        docker compose exec django python manage.py test apps.bar.tests -v 2
        ;;

    contracting)
        print_header "Running Contracting App Tests"
        docker compose exec django python manage.py test apps.contracting.tests -v 2
        ;;

    saas)
        print_header "Running SaaS App Tests"
        docker compose exec django python manage.py test apps.saas.tests -v 2
        ;;

    analytics)
        print_header "Running Analytics App Tests"
        docker compose exec django python manage.py test apps.analytics.tests -v 2
        ;;

    loyalty)
        print_header "Running Loyalty App Tests"
        docker compose exec django python manage.py test apps.loyalty.tests -v 2
        ;;

    users)
        print_header "Running Users App Tests"
        docker compose exec django python manage.py test apps.users.tests -v 2
        ;;

    coverage)
        print_header "Running Tests with Coverage"
        docker compose exec django python manage.py test --parallel --coverage=apps --cov-report=html --cov-report=term
        ;;

    *)
        print_fail "Unknown command: $COMMAND"
        echo "Run 'bash scripts/test_docker.sh help' for usage"
        ;;
esac

echo ""
