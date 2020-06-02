# Provisioning
An [Ansible](https://docs.ansible.com/ansible/latest/index.html) script to provision my personal machines. A constant work in progress.

## Usage
For all systems, this assumes a basic installation has been performed. That is, disks have been partitioned and a user has been added with proper groups, etc. Also assumes `sudo` has been installed, and said user has been added to the `sudo` group (and `sudo` group has been given root privileges). Although in the future, especially with [Debian](https://www.debian.org/distrib/) this will probably occur in the `base` role.

For all systems, look through the roles you want, and note the roles you want to run. Also, in some roles my personal dotfiles are included. Currently, the following files should be customized accordingly:
* [roles/tmux/files/tmux.conf](roles/tmux/files/tmux.conf)
* [roles/vim/files/](roles/vim/files/)
* [roles/nvim/files/](roles/nvim/files/)
* [roles/pia/files/](roles/pia/files/)

When you've done the above, run:

### Ubuntu
```bash
sudo apt-get update && \
sudo apt-get --yes install ansible git && \
git clone --depth=1 https://github.com/mbaroody/provisioning.git ~/.provisioning && \
cd ~/.provisioning && \
ansible-playbook --ask-become --inventory localhost playbook.yml
```
Or, to run a single role, for example just the `vim` role:

```
ansible-playbook --ask-become --tags=vim --inventory=localhost playbook.yml
```

Or, pass variables, for example just the `pia` role:

```
ansible-playbook \
  --ask-become \
  --tags=pia \
  --extra-vars "pia_username=**** pia_conn_method=tcp pia_strong_encryption=yes"
  --inventory=localhost
  playbook.yml
```

The last line, `ansible-playbook --ask-become -i localhost playbook.yml`, can be run at anytime from `~/.provisioning`, for example after you've made tweeks to dotfiles in `~/.provisioning`.
