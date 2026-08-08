#!/bin/bash
# ============================================================================
# BIJOU AI SAAS - AUTOMATED DEPLOYMENT SCRIPT
# ============================================================================
# Description: Zero-downtime deployment with feature flags
# Author: Lead Engineer
# Date: 2026-01-30
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="bijou-ai-enterprise-w3j"
BRIDGE_APP="whatsapp-bridge-staging-w3j"
SUPABASE_URL="https://lrwzlujomukzjykafmic.supabase.co"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

preflight_checks() {
    log_step "PRE-FLIGHT CHECKS"

    log_info "Checking required tools..."
    check_command fly
    check_command psql
    check_command git

    log_info "Checking Fly.io authentication..."
    if ! fly auth whoami &> /dev/null; then
        log_error "Not authenticated with Fly.io. Run: fly auth login"
        exit 1
    fi

    log_info "Checking app exists..."
    if ! fly apps list | grep -q "$APP_NAME"; then
        log_error "App $APP_NAME not found"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

# ============================================================================
# DATABASE MIGRATION
# ============================================================================

run_database_migration() {
    log_step "DATABASE MIGRATION"

    log_info "Extracting Supabase credentials..."
    SUPABASE_SERVICE_KEY=$(fly secrets list -a $APP_NAME | grep SUPABASE_SERVICE_KEY | awk '{print $2}')

    if [ -z "$SUPABASE_SERVICE_KEY" ]; then
        log_warning "Could not extract Supabase service key automatically"
        log_info "Please run the migration manually:"
        echo ""
        echo "1. Open: $SUPABASE_URL"
        echo "2. Go to SQL Editor"
        echo "3. Paste contents of: migrations/001_saas_tables.sql"
        echo "4. Execute"
        echo ""
        read -p "Press Enter after you've run the migration..."
    else
        log_info "Running migration via psql..."
        # Note: This requires psql and proper connection string
        log_warning "Automatic migration not implemented yet"
        log_info "Please run migration manually in Supabase SQL Editor"
        log_info "File: migrations/001_saas_tables.sql"
        read -p "Press Enter after you've run the migration..."
    fi

    log_success "Database migration completed"
}

# ============================================================================
# SET FEATURE FLAGS (ALL OFF)
# ============================================================================

set_feature_flags_off() {
    log_step "SETTING FEATURE FLAGS (ALL OFF)"

    log_info "Setting all feature flags to FALSE for safe deployment..."

    fly secrets set \
        ENABLE_BIJOU_COMMANDS=false \
        ENABLE_MULTI_TENANT=false \
        ENABLE_USAGE_LIMITS=false \
        ENABLE_AUTO_REPORTS=false \
        ENABLE_DAILY_REPORTS=false \
        ENABLE_WEEKLY_REPORTS=false \
        ENABLE_MONTHLY_REPORTS=false \
        ENABLE_FUNCTION_CALLING=false \
        ENABLE_HANDOVER_QUEUE=false \
        DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001 \
        OWNER_NUMBER=+60174106981 \
        -a $APP_NAME

    log_success "Feature flags set to OFF"
}

# ============================================================================
# DEPLOY APPLICATION
# ============================================================================

deploy_app() {
    log_step "DEPLOYING APPLICATION"

    log_info "Current app status:"
    fly status -a $APP_NAME

    log_info "Deploying new version with SaaS code..."
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR/../w3j-bijou-enterprise"
    fly deploy --ha=false -a $APP_NAME

    log_success "Application deployed"
}

# ============================================================================
# VERIFY DEPLOYMENT
# ============================================================================

verify_deployment() {
    log_step "VERIFYING DEPLOYMENT"

    log_info "Waiting for app to start..."
    sleep 10

    log_info "Checking app health..."
    fly status -a $APP_NAME

    log_info "Recent logs:"
    fly logs -a $APP_NAME | tail -30

    log_info "Testing health endpoint..."
    HEALTH_URL="https://$APP_NAME.fly.dev/health"
    if curl -s $HEALTH_URL | grep -q "healthy\|ok"; then
        log_success "Health check passed"
    else
        log_warning "Health check returned unexpected response"
    fi

    log_success "Deployment verification completed"
}

# ============================================================================
# PROGRESSIVE FEATURE ENABLEMENT
# ============================================================================

enable_bijou_commands() {
    log_step "ENABLING @BIJOU COMMANDS"

    log_info "Enabling command system..."
    fly secrets set ENABLE_BIJOU_COMMANDS=true -a $APP_NAME

    log_info "Restarting app..."
    fly apps restart $APP_NAME

    sleep 5
    log_info "Test: Send '@bijou help' via WhatsApp"
    read -p "Press Enter after testing..."

    log_success "@bijou commands enabled"
}

enable_multi_tenant() {
    log_step "ENABLING MULTI-TENANT"

    log_info "Enabling tenant isolation..."
    fly secrets set ENABLE_MULTI_TENANT=true -a $APP_NAME

    log_info "Restarting app..."
    fly apps restart $APP_NAME

    sleep 5
    log_info "Check usage_tracking table in Supabase for entries"
    read -p "Press Enter after verifying..."

    log_success "Multi-tenant enabled"
}

enable_limits_and_reports() {
    log_step "ENABLING LIMITS & REPORTS"

    log_info "Enabling usage limits and reporting..."
    fly secrets set \
        ENABLE_USAGE_LIMITS=true \
        ENABLE_AUTO_REPORTS=true \
        ENABLE_DAILY_REPORTS=true \
        ENABLE_WEEKLY_REPORTS=true \
        -a $APP_NAME

    log_info "Restarting app..."
    fly apps restart $APP_NAME

    sleep 5
    log_info "Test: Send '/admin report daily' via WhatsApp"
    read -p "Press Enter after testing..."

    log_success "Limits & reports enabled"
}

enable_advanced_features() {
    log_step "ENABLING ADVANCED FEATURES"

    log_info "Enabling handover system..."
    fly secrets set \
        ENABLE_HANDOVER_QUEUE=true \
        -a $APP_NAME

    log_info "Restarting app..."
    fly apps restart $APP_NAME

    sleep 5
    log_info "Test: Send message with 'speak to human'"
    read -p "Press Enter after testing..."

    log_success "Advanced features enabled"
}

# ============================================================================
# ROLLBACK FUNCTION
# ============================================================================

rollback() {
    log_step "ROLLING BACK"

    log_warning "Disabling all features..."
    fly secrets set \
        ENABLE_BIJOU_COMMANDS=false \
        ENABLE_MULTI_TENANT=false \
        ENABLE_USAGE_LIMITS=false \
        ENABLE_AUTO_REPORTS=false \
        ENABLE_HANDOVER_QUEUE=false \
        ENABLE_FUNCTION_CALLING=false \
        -a $APP_NAME

    fly apps restart $APP_NAME

    log_success "Rolled back to safe state"
}

# ============================================================================
# MAIN DEPLOYMENT FLOW
# ============================================================================

main() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║        🚀 BIJOU AI SAAS DEPLOYMENT AUTOMATION 🚀        ║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Deployment Target: $APP_NAME"
    log_info "Bridge App: $BRIDGE_APP"
    log_info "Supabase: $SUPABASE_URL"
    echo ""

    # Show menu
    echo "Select deployment phase:"
    echo "  1) Full deployment (all steps)"
    echo "  2) Pre-flight checks only"
    echo "  3) Database migration only"
    echo "  4) Deploy code only"
    echo "  5) Enable features (progressive)"
    echo "  6) Rollback (disable all features)"
    echo "  0) Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice

    case $choice in
        1)
            preflight_checks
            run_database_migration
            set_feature_flags_off
            deploy_app
            verify_deployment

            log_step "DEPLOYMENT COMPLETE"
            log_success "Code deployed with features OFF"
            echo ""
            log_info "Next steps:"
            echo "  - Run option 5 to enable features progressively"
            echo "  - Or manually enable via: fly secrets set ENABLE_*=true"
            ;;
        2)
            preflight_checks
            ;;
        3)
            run_database_migration
            ;;
        4)
            deploy_app
            verify_deployment
            ;;
        5)
            enable_bijou_commands
            enable_multi_tenant
            enable_limits_and_reports
            enable_advanced_features

            log_step "ALL FEATURES ENABLED"
            log_success "Bijou AI SaaS is now fully operational! 🎉"
            ;;
        6)
            rollback
            ;;
        0)
            log_info "Exiting..."
            exit 0
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac

    echo ""
    log_success "Script completed successfully! 🎉"
    echo ""
}

# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

# Trap errors and provide rollback option
trap 'log_error "Deployment failed! Run with option 6 to rollback."; exit 1' ERR

# Run main function
main "$@"
