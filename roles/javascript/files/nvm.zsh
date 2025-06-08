export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
if [[ -z $NODE_PATH ]]; then export NODE_PATH=`npm root -g`; else export NODE_PATH=$NODE_PATH:`npm root -g`; fi
