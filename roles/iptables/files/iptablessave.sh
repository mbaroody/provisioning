#!/bin/sh
iptables-save -c > /etc/iptables.rules
if [ -f /etc/iptables/iptables.downrules ]; then
  iptables-restore < /etc/iptables.downrules
fi
exit 0
