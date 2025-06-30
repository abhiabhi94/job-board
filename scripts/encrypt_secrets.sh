#!/bin/bash
set -e

# Script to encrypt application secrets with Ansible Vault
# Used by pre-commit hooks and can be run manually

SECRETS_FILE="infra/.secrets.yml"
VAULT_FILE="infra/vault.yml"
VAULT_PASSWORD_FILE="infra/.vault-password"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⏭️  $1${NC}"
}

# Check if secrets file exists
if [[ ! -f "$SECRETS_FILE" ]]; then
    echo_info "No secrets file found at $SECRETS_FILE, skipping encryption"
    exit 0
fi

# Check if vault password file exists
if [[ ! -f "$VAULT_PASSWORD_FILE" ]]; then
    echo_info "No vault password file found at $VAULT_PASSWORD_FILE"
    exit 1
fi

# Check if encryption is needed
if [[ ! -f "$VAULT_FILE" ]] || [[ "$SECRETS_FILE" -nt "$VAULT_FILE" ]]; then
    echo_info "Secrets changed, encrypting..."

    ansible-vault encrypt $SECRETS_FILE \
        --output $VAULT_FILE \
        --vault-password-file $VAULT_PASSWORD_FILE

    git add "$VAULT_FILE"
    echo_success "App secrets encrypted and staged for commit"
else
    echo_warning "Secrets unchanged, skipping encryption"
fi
