# Deploying Taura AI on ZCHPC's HPC Cloud

This is the deployment target referenced in the written proposal (Section
3.3, "CCE" = ZCHPC's Cloud Compute Environment). This document records what
that environment actually is and the concrete steps to deploy this
repository on it — grounded in ZCHPC's own published HPC Access Guide and
User Manual, not assumed.

## What ZCHPC's HPC Cloud actually is

ZCHPC's HPC Cloud is a **Xen Orchestra**-managed virtual machine platform
(not Kubernetes, not a PaaS with buildpacks). Per ZCHPC's own HPC Access
Guide and User Manual (https://zchpc.ac.zw/usermanual):

- You apply for an account at `https://zchpc.ac.zw/accountapplication`.
- You get a VM by logging into Xen Orchestra at
  `https://cloud.zchpc.ac.zw` (open internet) or via a campus VPN, clicking
  **Create VM**, selecting a template, and assigning vCPU/RAM/storage.
- VM lifecycle (start/stop/restart), console access, and **snapshots** are
  all managed through that same Xen Orchestra web UI.
- Support: `support@zchpc.ac.zw`, WhatsApp/call `+263 785 005 163`. For
  resource/GPU allocation questions specifically: `business@zchpc.ac.zw`,
  `+263 719 479 129`.

**Practical consequence:** the deployment target is a standard Ubuntu Linux
VM you administer yourself over SSH — so this repository's existing
Docker/Docker Compose setup (`Dockerfile`, `docker-compose.yml`) is already
the right artifact. This directory adds what a bare Docker Compose file
doesn't cover on a self-managed VM: a bootstrap script, a systemd unit so the
app survives reboots, a reverse proxy for real TLS, and a VM-level backup
plan — see the file list below.

## Files in this directory

| File | Purpose |
|---|---|
| `cloud-init.yaml` | Bootstraps a fresh VM: installs Docker Engine + Compose plugin, creates a non-root `taura` service account, configures the firewall (ufw: allow SSH/80/443 only), creates `/opt/taura-ai`. Paste into Xen Orchestra's cloud-init/user-data field at VM creation if the template supports it, or run the equivalent commands manually over SSH. |
| `taura-backend.service` | systemd unit that runs `docker compose up -d` on boot and restarts on failure. |
| `docker-compose.zchpc.yml` | Compose override: resource limits, log rotation, a Caddy reverse proxy for automatic HTTPS, a named volume for `/app/logs`. Applied on top of the base `docker-compose.yml`. |
| `Caddyfile` | Reverse proxy config for Caddy — replace the placeholder domain before deploying. |
| `VM_SIZING.md` | Recommended vCPU/RAM/disk per deployment stage, and the honest open item on GPU passthrough availability. |
| `backup.sh` | Application-level backup (audit log today; a database dump once the session store is a real database) — complements, not replaces, a Xen Orchestra VM snapshot. |

## Step-by-step: first deployment

### 1. Apply for an account and create the VM

1. Apply at `https://zchpc.ac.zw/accountapplication`.
2. Once approved, log into `https://cloud.zchpc.ac.zw`.
3. **Create VM** → choose an Ubuntu 24.04 LTS template → assign resources per
   `VM_SIZING.md` (start with Stage 1 sizing for the demo) → if the template
   exposes a cloud-init/user-data field, paste in `cloud-init.yaml`.
4. Start the VM and note its IP address (VM details in Xen Orchestra).

If the template doesn't support cloud-init, start the VM, connect via the
Xen Orchestra **Console** or SSH, and run the `packages`/`runcmd` steps from
`cloud-init.yaml` manually — they're plain `apt`/`useradd`/`ufw` commands.

### 2. Point a domain at the VM (recommended)

Add an A record for a domain/subdomain you control pointing at the VM's IP.
Caddy needs this for automatic HTTPS (see `Caddyfile`). You can skip this for
an early internal demo and access the app over plain HTTP on port 8000
directly (see the note in `docker-compose.zchpc.yml`), but not for anything
pilot users will actually use.

### 3. Deploy the application

```bash
ssh taura@<vm-ip>                      # the account cloud-init.yaml created
cd /opt/taura-ai
git clone <your-repo-url> app
cd app
cp .env.example .env                   # edit as needed -- see .env.example comments
# Edit deploy/zchpc/Caddyfile: replace taura.example.org with your real domain
```

### 4. Install and start the systemd service

```bash
sudo cp deploy/zchpc/taura-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now taura-backend
sudo systemctl status taura-backend
```

### 5. Verify

```bash
curl -s https://<your-domain>/api/health
# {"status":"ok"}
```

Open `https://<your-domain>` in a browser — you should see the same chat demo
described in `docs/DEMO_SCRIPT.md`.

### 6. Set up backups

```bash
crontab -e
# add:
0 2 * * * /opt/taura-ai/app/deploy/zchpc/backup.sh >> /var/log/taura-backup.log 2>&1
```

And separately, in Xen Orchestra: VM → **Snapshots** → **Create**, on
whatever cadence matches your risk tolerance (at minimum, before any
significant change — matching the "Regular Snapshots" best practice in
ZCHPC's own User Manual).

## Updating a running deployment

```bash
cd /opt/taura-ai/app
git pull
sudo systemctl restart taura-backend    # re-runs `docker compose up -d --remove-orphans`,
                                         # which rebuilds/recreates only what changed
```

## What this runbook does NOT cover yet

- **GPU-enabled inference** (`TAURA_ASR_BACKEND=mms`) — GPU passthrough
  availability on ZCHPC's HPC Cloud VM tier is an open item to confirm with
  ZCHPC directly (see `VM_SIZING.md`), not something this runbook can assume.
- **A managed database** — the session store is currently the in-process
  `ConsentStore` and a JSONL audit log (see `docs/ARCHITECTURE.md`). Adding a
  Postgres service to `docker-compose.zchpc.yml` is straightforward when that
  migration happens, but isn't needed for the current prototype.
- **Multi-VM / high availability** — out of scope for a pilot-stage (~200
  user) deployment; a single right-sized VM per `VM_SIZING.md` is sufficient.
