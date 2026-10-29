# Beevarium Ansible

This minimal local Ansible role orchestrates the existing Linux scripts. It does not replace their business logic.

## Install

```bash
python3 -m venv ansible/.venv
ansible/.venv/bin/pip install -r ansible/requirements.txt
```

## Run

```bash
ansible/.venv/bin/ansible-playbook -i ansible/inventory/localhost.ini ansible/playbook.yml
```

Default lifecycle:

1. Starts Docker Compose with `.env`.
2. Waits for the API.
3. Generates and publishes demo access.
4. Runs the full Linux gate.

Useful overrides:

```bash
ansible/.venv/bin/ansible-playbook -i ansible/inventory/localhost.ini ansible/playbook.yml \
  -e beevarium_bootstrap_demo=false \
  -e beevarium_run_gate=false
```

Migrations remain explicit because local and target environments use different procedures. For a target deployment, run `scripts/linux/deploy_apply_migrations.sh .env.target` before the target deploy lifecycle.