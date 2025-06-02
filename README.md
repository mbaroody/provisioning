# Provisioning
Set of Ansible playbooks and roles to provision my personal dev machines.

## Prerequisites
- must have `ansible` and `git` installed (`sudo apt-get install git ansible`), as well as [Insync](https://www.insynchq.com)
- must login and sync with Insync Google Drive (expecting `~/Insync/michael.w.baroody@gmail.com/Google\ Drive`)
- optional: login with VPN of choice

## Usage
```bash
mkdir -p ~/github/mbaroody && \
git clone --depth=1 https://github.com/mbaroody/provisioning.git ~/github/mbaroody/provisioning && \
cd ~/github/mbaroody/provisioning && \
ansible-playbook --ask-become --inventory localhost site.yml
```