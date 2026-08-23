# Troubleshooting

Common errors and how to fix them.

---

## 401 — `NotAuthenticated: Failed to verify the HTTP(S) Signature`

**Cause:** The OCI API private key path, fingerprint, or tenancy OCID in `oci_config` is wrong.

**Fix checklist:**
1. Open `oci_config` and confirm the `key_file` path is the **absolute** path to your `.pem` file.
2. Run `ls -la <key_file_path>` — the file must exist and be readable by the current user.
3. Confirm the `fingerprint` matches what OCI shows under your profile > API Keys.
4. Confirm `tenancy` and `user` OCIDs are correct — they look like `ocid1.tenancy.oc1..xxxxx`.
5. Check your system clock: OCI signatures expire if your clock is more than 5 minutes off. Run `date` and compare with world time.

---

## 400 — `LimitExceeded`

**Cause:** Your tenancy has hit a resource quota — either the ARM instance already exists, or boot volume storage is exhausted.

**Fix checklist:**
1. Log into the [OCI Console](https://cloud.oracle.com) → Compute → Instances. Check if an ARM instance already exists.
2. If it does, the script should detect it and stop. If it already stopped, check `INSTANCE_CREATED`.
3. If no instance exists, go to **Governance → Limits, Quotas and Usage** and look at `Block Volume` and `Compute` limits.
4. Delete unused boot volumes to free up storage if needed.

---

## `No logs after 60 seconds` / `Couldn't find any logs`

**Cause:** Python crashed before it could write `launch_instance.log`.

**Fix:**
1. Check `python_error.log` in the project directory — it captures Python startup errors since the fix in [#83](https://github.com/mohankumarpaluru/oracle-freetier-instance-creation/pull/83).
2. Common causes: wrong Python version, missing dependencies, or bad `oci.env` values.
3. Run `python3 main.py` directly to see the error in your terminal.
4. Re-run setup: `./setup_init.sh` (not `rerun`) to reinstall dependencies.

---

## `Connection aborted` / `MaxRetryError` / `503`

**Cause:** Transient network issue or OCI API outage.

**This is handled automatically.** Since [#83](https://github.com/mohankumarpaluru/oracle-freetier-instance-creation/pull/83), connection errors and 503s are treated as retryable. The script will wait `REQUEST_WAIT_TIME_SECS` and try again. If the error is persistent (hours), check the [OCI Status page](https://ocistatus.oraclecloud.com/).

---

## 404 — `NotAuthorizedOrNotFound`

**Cause:** The API key doesn't have permission to access the resource, or a resource OCID is wrong.

**Fix checklist:**
1. Confirm the IAM policy for your user allows `manage` on `instances` and `vnics` in your compartment.
2. If you set `OCI_SUBNET_ID` manually, verify it is the correct OCID for your tenancy.
3. Confirm `OCI_CONFIG` points to a config file where `tenancy` matches your actual tenancy OCID.

---

## SSH — `Permission denied (publickey)` after instance creation

**Cause:** Using the wrong key file when connecting.

The script generates a **key pair**: a private key (e.g. `id_rsa_private`) and a public key (`id_rsa.pub`). To SSH in you must use the **private** key:

```bash
# Wrong:
ssh -i id_rsa.pub ubuntu@<ip>

# Correct:
ssh -i id_rsa_private ubuntu@<ip>
```

Also confirm you have assigned a public IP to the instance in the OCI console (Compute → Instances → your instance → Attached VNICs → Edit → Add Public IP).

---

## Account suspension / service limits zeroed out

Oracle may review accounts that make a very high volume of API calls. If you are concerned:

- Set `REQUEST_WAIT_TIME_SECS` to **60 or higher** (default is 60).
- Avoid restarting the script excessively — each restart triggers an immediate API call.
- The script is designed for legitimate provisioning automation as supported by the OCI API. That said, account reviews are at Oracle's sole discretion.

---

## `oci.env: line N: <word>: command not found`

**Cause:** A value in `oci.env` contains spaces and isn't quoted (e.g. `OPERATING_SYSTEM=Canonical Ubuntu`). Bash tries to execute the second word as a command.

**Fix:** Open `oci.env` and put double quotes around any value with spaces:
```bash
OPERATING_SYSTEM="Canonical Ubuntu"
DISPLAY_NAME="my arm instance"
```

If you used `setup_env.sh` to generate the file, re-run it — this quoting issue was fixed in the script.
