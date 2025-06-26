# Infrastructure

Automated deployment setup for the Job Board application using Ansible and GitHub Actions.

## Overview

This directory contains the complete infrastructure-as-code setup to deploy the job board application to a production server. The deployment includes:

- **Automated CI/CD** via GitHub Actions
- **Secure secret management** with Ansible Vault
- **Production-ready setup** with Nginx, SSL, and systemd service

## Structure

```
infra/
├── playbook.yml          # Main Ansible deployment playbook
├── hosts.yml             # Server inventory configuration
├── vault.yml             # Encrypted secrets (Ansible Vault)
├── .secrets.yml          # Plain secrets file (local only, never commit!)
└── templates/
    ├── env.j2             # Application environment variables
    ├── jobboard.service.j2 # Systemd service configuration
    └── nginx.conf.j2      # Nginx reverse proxy config
```

## Quick Start

### Initial Setup

1. **Create secrets file** (never commit this):
   ```bash
   cp .secrets.yml.example .secrets.yml
   # Edit with your actual values
   ```

2. **Set up GitHub secrets** in your repository:
   - `SSH_PRIVATE_KEY` - Private key for server access
   - `SERVER_HOST` - Your server's IP/hostname
   - `ANSIBLE_VAULT_PASSWORD` - Password for encrypting secrets

3. **Configure your server** in `hosts.yml`:
   ```yaml
   production:
     ansible_host: "your-server.com"
     ansible_user: "deploy"
   ```

### Deployment

**Automatic**: Push to `main` branch triggers deployment

**Manual**: Use GitHub Actions "Run workflow" button

**Local deployment**:
```bash
cd infra
ansible-playbook -i hosts.yml playbook.yml --ask-vault-pass
```

## What Gets Deployed

The playbook sets up a complete production environment:

1. **System packages** - Python, Nginx, Certbot, Git
2. **Application user** - Dedicated system user for security
3. **Python environment** - Virtual environment with dependencies
4. **Application service** - Systemd service for the Flask app
5. **Reverse proxy** - Nginx with security headers and compression
6. **SSL certificate** - Automatic Let's Encrypt certificate
7. **Environment config** - Secure environment variables from vault

## Secret Management

Secrets are managed using Ansible Vault:

- **Local development**: Edit `.secrets.yml` (never commit!)
- **Automatic encryption**: Pre-commit hook encrypts secrets → `vault.yml`
- **Production**: Secrets loaded from encrypted `vault.yml`

## Key Features

- **Security**: Encrypted secrets, proper file permissions, security headers
- **Reliability**: Systemd service with auto-restart, health checks
- **Performance**: Nginx compression, proper caching headers
- **Maintenance**: Automated SSL renewal, system updates

## Troubleshooting

**Deployment fails**: Check GitHub Actions logs for detailed error messages

**App won't start**: SSH to server and check:
```bash
sudo systemctl status jobboard
sudo journalctl -u jobboard -f
```

**Nginx issues**: Check nginx logs:
```bash
sudo nginx -t  # Test config
sudo tail -f /var/log/nginx/error.log
```

**Secrets issues**: Re-encrypt vault if needed:
```bash
ansible-vault encrypt .secrets.yml --output vault.yml
```

## Server Requirements

- **OS**: Ubuntu 20.04+ (or Debian-based)
- **Access**: SSH key-based authentication
- **Privileges**: Sudo access for the deployment user
- **Ports**: 80, 443 open for web traffic

## Production Checklist

Before first deployment(should be automated in future as well):
- [ ] Server provisioned with SSH access
- [ ] GitHub secrets configured
- [ ] Domain DNS pointing to server
- [ ] Secrets file created and encrypted
- [ ] Firewall configured (ports 80, 443, 22)
