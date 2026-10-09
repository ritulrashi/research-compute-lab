"""Cross-platform local lab CLI; requires Docker Compose."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
def compose(*args):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["up", "down", "status", "submit", "logs", "configure"])
    p.add_argument("--samples", type=int, default=1000000)
    p.add_argument("--shards", type=int, default=8)
    a = p.parse_args()
    if a.command == "up":
        compose("up", "-d", "--build", "--wait", "--wait-timeout", "180")
    elif a.command == "down":
        compose("down")
    elif a.command == "status":
        compose("ps")
        compose("exec", "-T", "controller", "sinfo", "-N", "-l")
    elif a.command == "submit":
        result = subprocess.check_output(["docker", "compose", "exec", "-T", "--user",
            "researcher", "controller", "python3", "/opt/lab/distributed.py", "submit",
            "--samples", str(a.samples), "--shards", str(a.shards)], cwd=ROOT, text=True, timeout=240)
        manifest = json.loads(result)
        output = ROOT / "runs" / (manifest["execution"]["run_id"] + ".json")
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps({"output": str(output), "checksum": manifest["result_sha256"],
                          "hosts": manifest["execution"]["hosts"],
                          "verified": manifest["execution"]["serial_reference_matches"]}))
    elif a.command == "logs":
        compose("logs", "--tail", "100")
    else:
        for node in ("controller", "worker1", "worker2"):
            compose("exec", "-T", node, "ansible-playbook", "-i", "localhost,", "-c", "local",
                    "/opt/infra/configure.yml")
if __name__ == "__main__": main()
