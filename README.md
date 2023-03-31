# Provisioning
Set of [Ansible](https://docs.ansible.com/ansible/latest/index.html) playbooks and roles to provision my personal dev machines.

## Usage
For all systems, look through the roles you want, and note the roles you want to run. Also, in some roles my personal dotfiles are included. Currently, the following files should be customized accordingly:
* [roles/tmux/files/tmux.conf](roles/tmux/files/tmux.conf)
* [roles/nvim/files/](roles/nvim/files/)

### Ubuntu
```bash
sudo apt-get update && \
  sudo apt-get --yes install ansible git && \
  git clone --depth=1 https://github.com/mbaroody/provisioning.git ~/.provisioning && \
  cd ~/.provisioning && \
  ansible-galaxy install -r requirements.yml && \
  ansible-playbook --ask-become --inventory localhost playbook.yml
```
### MacOSX
If you haven't already, install [homebrew](https://brew.sh):
```bash
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" && \
  brew update && brew upgrade
```
Then continue:
```bash
brew install ansible git && \
  git clone --depth=1 https://github.com/mbaroody/provisioning.git ~/.provisioning && \
  cd ~/.provisioning && \
  ansible-galaxy install -r requirements.yml && \
  ansible-playbook --ask-become --inventory localhost playbook.yml
```

The last line, `ansible-playbook --ask-become playbook.yml`, can be run at anytime from `~/.provisioning`, for example after you've made tweeks to dotfiles in `~/.provisioning`.
