#!/usr/bin/env bash
# Prepares a fresh Ubuntu 22.04 or 24.04 machine to be the judge machine. Run as root (sudo bash setup-host.sh). It is safe to run twice.
# It installs Docker, turns on a firewall that lets in only SSH (22), HTTP (80) and HTTPS (443), and turns on automatic security updates.
# It does not touch SSH settings, so it cannot lock you out. Use SSH keys, not a password, and keep this machine for the judge only.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "Run this as root: sudo bash setup-host.sh"; exit 1; fi

echo "== 1/4 Docker"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
systemctl enable --now docker

echo "== 2/4 Firewall (only 22, 80, 443 in)"
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "== 3/4 Automatic security updates"
apt-get install -y unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "== 4/4 Sandbox images the judge uses (pulled now so the first submission is fast)"
for image in python:3.14-alpine gcc:14 node:18-alpine eclipse-temurin:17-alpine; do docker pull "$image"; done

echo
echo "Done. Next: copy .env.example to .env here, fill in JUDGE_TOKEN and JUDGE_DOMAIN, then run:  docker compose up -d --build"
