# Provisioning
Set of Ansible playbooks and roles to provision my personal dev machines.

## Usage
```bash
mkdir -p ~/github/mbaroody && \
git clone --depth=1 https://github.com/mbaroody/provisioning.git ~/github/mbaroody/provisioning && \
cd ~/github/mbaroody/provisioning && \
ansible-playbook --ask-become --inventory localhost site.yml
```