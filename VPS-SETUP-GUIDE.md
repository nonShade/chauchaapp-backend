# VPS Configuration & Deployment Guide
`chauchaapp-backend`

This guide explains how to configure a shared Ubuntu VPS (Ubuntu 24.04 LTS) for deployment, manage users and permissions, install dependencies, set up SSH keys, and prepare the environment for GitHub Actions CI/CD deployment.

---

## Table of Contents
1. [SSH Key Setup & GitHub Secrets](#1-ssh-key-setup--github-secrets)
2. [User Management & Folder Permissions](#2-user-management--folder-permissions)
3. [Installing Docker & Docker Compose](#3-installing-docker--docker-compose)
4. [Initial Git & Project Setup](#4-initial-git--project-setup)
5. [Configuring Environment Variables](#5-configuring-environment-variables)
6. [Manual Execution & Troubleshooting](#6-manual-execution--troubleshooting)

---

## 1. SSH Key Setup & GitHub Secrets

To allow GitHub Actions to securely connect to the VPS, you must generate an SSH key pair and add the relevant keys to GitHub and the VPS.

### Step 1.1: Generate SSH Key Pair
You can generate a secure SSH key pair on your local machine (or the VPS itself). Run this command in a terminal:

```bash
ssh-keygen -t ed25519 -C "github-actions-chauchaapp"
```
*When prompted for a file, press **Enter** to use the default path (`~/.ssh/id_ed25519`).*
*When prompted for a passphrase, press **Enter** twice to keep it blank (GitHub Actions requires a key without passphrase unless you configure additional steps).*

### Step 1.2: Retrieve the Private Key (for GitHub Secrets)
Copy the **entire** content of the private key. Run:

**On Windows (PowerShell):**
```powershell
Get-Content ~\.ssh\id_ed25519
```

**On Linux / macOS:**
```bash
cat ~/.ssh/id_ed25519
```

Copy the output, which should start with `-----BEGIN OPENSSH PRIVATE KEY-----` and end with `-----END OPENSSH PRIVATE KEY-----`.

### Step 1.3: Retrieve the Public Key
Run the following to view your public key:

**On Windows (PowerShell):**
```powershell
Get-Content ~\.ssh\id_ed25519.pub
```

**On Linux / macOS:**
```bash
cat ~/.ssh/id_ed25519.pub
```

### Step 1.4: Add Public Key to the VPS
Log in to your VPS and add the public key to the authorized keys file for the deployment user (e.g., `userpds`):

```bash
# Log in to VPS
ssh userpds@200.13.5.3

# Create the .ssh directory if it does not exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Append your public key to the authorized_keys file
echo "PASTE_YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 1.5: Configure GitHub Secrets
Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret** and add the following:

| Secret Name | Value Description | Example |
| :--- | :--- | :--- |
| `IP` (or `HOST`) | The public IP address of the VPS | `200.13.5.3` |
| `USERNAME` | The UNIX username used for deployment | `userpds` |
| `SSH_PRIVATE_KEY` | The exact content of the private key (`id_ed25519`) | `-----BEGIN OPENSSH...` |
| `PASSWD` | Password of the user (in case SSH keys are not set up yet or sudo requires it) | `your_user_password` |

---

## 2. User Management & Folder Permissions

Since multiple people use this VPS, configuring correct folder permissions is critical to avoid files locked by one user or permission conflicts.

### Option A: Sharing a Single UNIX Account (`userpds`)
If all developers log into the VPS using the same `userpds` account, simply add every developer's public SSH key to `/home/userpds/.ssh/authorized_keys` as explained in Section 1.4.

### Option B: Separate UNIX Accounts with Shared Group (Recommended)
If developers log in with their own UNIX users (e.g., `alice`, `bob`) but need to collaborate on the project:

#### Step 2.1: Create a Shared Group
Create a group called `chaucha-devs` and add all developers to it:
```bash
sudo groupadd chaucha-devs

# Add users to the group
sudo usermod -aG chaucha-devs userpds
sudo usermod -aG chaucha-devs alice
sudo usermod -aG chaucha-devs bob
```
*(Users must log out and log back in for group changes to take effect).*

#### Step 2.2: Setup the Shared Directory & SetGID
Create the project folder in a shared location (like `/opt` or `/var/www` or `/home/userpds` if shared):
```bash
# Create target directory
sudo mkdir -p /opt/chauchaapp-backend

# Set owner to the primary deployer and group to chaucha-devs
sudo chown -R userpds:chaucha-devs /opt/chauchaapp-backend

# Grant read, write, and execute permissions to owner and group
sudo chmod -R 775 /opt/chauchaapp-backend

# Enable SetGID (Set Group ID) bit
# This ensures any new files created in this directory automatically inherit the 'chaucha-devs' group ownership.
sudo chmod g+s /opt/chauchaapp-backend
```

#### Step 2.3: Configure Git Shared Repository (If already cloned)
If you already cloned the repository, tell git to respect group write permissions:
```bash
cd /opt/chauchaapp-backend
git config core.sharedRepository group
```

---

## 3. Installing Docker & Docker Compose

Verify if Docker is installed. If not, follow these steps to install it on Ubuntu 24.04 LTS.

### Step 3.1: Check Current Installation
```bash
docker --version
docker compose version
```

### Step 3.2: Install Docker Engine (If needed)
If Docker is not installed, run:
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

# Install Docker packages
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Step 3.3: Configure Non-Root Docker Access
Ensure the deployer user and developers can run Docker commands without prefixing them with `sudo`:
```bash
# Create the docker group (usually already exists)
sudo groupadd docker

# Add your user to the group
sudo usermod -aG docker userpds

# Apply the new group membership (or log out and log back in)
newgrp docker
```
*Verify you can run docker without sudo:*
```bash
docker ps
```

---

## 4. Initial Git & Project Setup

Before GitHub Actions can update the code, you must initialize the repository on the VPS.

### Step 4.1: Clone the Repository
Go to your project directory and clone the repository:

**Using SSH (Recommended - Requires setting up a Deploy Key on GitHub):**
```bash
cd ~
git clone git@github.com:your-organization/chauchaapp-backend.git
```

**Using HTTPS:**
```bash
cd ~
git clone https://github.com/your-organization/chauchaapp-backend.git
```
*(Make sure the directory matches the path inside `deploy.yml`, which is `~/chauchaapp-backend`)*

### Step 4.2: Add GitHub Public Host Key to Known Hosts
Run the following to make sure Git doesn't prompt for confirmation during automated deploys:
```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

---

## 5. Configuring Environment Variables

Docker Compose uses the `.env` file to configure production secrets. You must create this file on the VPS manually because it contains sensitive keys and is not committed to git.

### Step 5.1: Create `.env` file
```bash
cd ~/chauchaapp-backend
cp .env.example .env
nano .env
```

### Step 5.2: Configure Production Values
Update variables for production:
```ini
# Security (Generate secure random values!)
SECRET_KEY=generate_a_very_long_random_string_here
JWT_SECRET=generate_another_random_string_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Database
POSTGRES_DB=chauchaapp_db_prod
POSTGRES_USER=your_secure_postgres_user
POSTGRES_PASSWORD=your_secure_postgres_password

# External APIs
NVIDIA_API_KEY=your_nvidia_api_key
TAVILY_API_KEY=your_tavily_api_key

# CORS (Allowed origins for your frontend app)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

---

## 6. Manual Execution & Troubleshooting

To ensure everything is working before pushing to `develop`:

### Step 6.1: Start Services Manually
```bash
cd ~/chauchaapp-backend
docker compose --profile production up -d --build
```

### Step 6.2: Monitor Logs
```bash
docker compose --profile production logs -f
```

### Step 6.3: Clean Up Unused Docker Resources (If VPS runs out of disk space)
Since Ubuntu VPS partitions are often small, prune old builds regularly:
```bash
docker system prune -f
docker builder prune -f
```
