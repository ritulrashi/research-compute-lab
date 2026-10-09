#!/usr/bin/env bash
set -euo pipefail
ansible-playbook -i localhost, -c local /opt/infra/configure.yml
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/lab.conf
