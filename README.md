# Provisioning
An Ansible playbook and full instructions to provision my personal dev machines.

## Prerequisites
- must have installed Ubuntu Desktop with secret `autoinstall.yml` Gist
- **optional:** login with VPN of choice
- log in and sync with Insync Google Drive (expecting `~/Insync/michael.w.baroody@gmail.com/Google\ Drive`) for Anki `addons21` and `zsh_history`
- log in with GitHub and fine-grained personal access token with read/write access for SSH keys

## Usage
```bash
wget -q https://gist.github.com/mbaroody/4491225f14eeab204289114e1b557f39/raw/67c92710d843348ee6fbba94499fba834cadd086/post-install.sh -O /tmp/post-install.sh && bash /tmp/post-install.sh
```
