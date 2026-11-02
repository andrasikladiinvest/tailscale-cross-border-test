# Temporary cross-border Tailscale connectivity check

Manual-only, bounded synthetic-data qualification. No Fund source, documents, SSH private keys, or VPN profiles are uploaded. A temporary GitHub-hosted runner joins an existing tailnet, exchanges fixed 1 MiB synthetic payloads in both directions, and logs anonymized timings. The target is configured through a repository secret. No exit node or routing change is requested.

Requires temporary `TAILSCALE_AUTHKEY`, `TARGET_TS_IP`, and `PROBE_TOKEN` repository secrets. Standard public-repository hosted runners are used. The node logs out and the probe listener stops after the job. Results describe one route/time, not universal future availability. Remove the temporary secrets after qualification.
