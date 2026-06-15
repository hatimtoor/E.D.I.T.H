# Security posture & responsible use

E.D.I.T.H. includes a genuine offensive-security toolkit. It is built to be **powerful
for authorized work and useless for opportunistic abuse**.

## The authorization gate

Every offensive action (`security/recon.py`, and any future exploit helper) calls
`assert_in_scope(target, scope)` **before** touching a target. That function refuses
unless:

1. A scope file exists (`config/authorization.yaml`), and
2. it names an accountable human (`authorized_by`), and
3. it has not expired (`expires`), and
4. the specific target is covered by an authorized IP/CIDR/hostname-glob entry.

With no scope file, **all** offensive tooling is disabled. This is verified by the test
suite (`tests/test_authorization.py`).

## What E.D.I.T.H. will do

- Recon, scanning, TLS inspection, and exploitation tooling **against scoped targets**
  for CTFs, authorized penetration tests, and infrastructure you own.
- Stealth web automation to defeat bot-blocking **for your own browsing/automation**.

## What E.D.I.T.H. will not do

- Act on any host outside the signed scope.
- Mass-targeting, worming, or self-propagation.
- Build malware for distribution or detection-evasion for the purpose of harming others.

These boundaries are structural (the gate, the sandbox, the destructive-command guard),
not just policy text.

## Defense-in-depth layers

| Layer | Control |
|---|---|
| Targeting | `assert_in_scope()` choke point + expiry |
| Execution | Docker sandbox (cap-drop, no-new-privileges, read-only, `--network none`, pids/mem limits) |
| Shell | destructive-pattern regex guard (`sandbox/backends.py`) |
| Memory | prompt-injection scanner on every write |
| Skills | secret-literal refusal + agent-immutable protection |
| Permissions | explicit 5-level matrix (`core/config.py`) |

## Reporting

If you find a way to bypass the authorization gate or the sandbox boundary, treat it as
a security bug and fix/report it before using the toolkit further.
