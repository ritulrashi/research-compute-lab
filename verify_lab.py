"""End-to-end lab acceptance checks. Failure injection touches this Compose project only."""
import json
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
evidence = []
def command(*args):
    p = subprocess.run(["docker","compose",*args], cwd=ROOT, text=True, capture_output=True, timeout=240)
    evidence.append({"command": list(args), "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
    if p.returncode: raise RuntimeError(p.stderr)
    return p.stdout
def controller(*args):
    return command("exec","-T","controller",*args)
def http(url):
    with urlopen(url, timeout=5) as response: return json.load(response)
def until(function, timeout=90):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            value=function()
            if value: return value
        except (OSError, ValueError, RuntimeError): pass
        time.sleep(2)
    raise TimeoutError("acceptance condition did not become true")
def query(expression):
    return http("http://127.0.0.1:19090/api/v1/query?"+urlencode({"query":expression}))["data"]["result"]
def all_ready():
    values=query('lab_slurm_node_available')
    return len(values)==2 and all(v["value"][1]=="1" for v in values)
def main():
    summary={"timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"checks":{}}
    try:
        until(lambda: "idle" in controller("sinfo","-h","-N","-o","%N %T"))
        hosts=controller("srun","--nodes=2","--ntasks=2","--mem=64M","hostname").split()
        assert set(hosts)=={"worker1","worker2"}, hosts
        summary["checks"]["two_worker_execution"]=hosts
        for node in ("controller","worker1","worker2"):
            output=command("exec","-T",node,"ansible-playbook","-i","localhost,","-c","local","/opt/infra/configure.yml")
            assert "changed=0" in output
        summary["checks"]["ansible_idempotence"]="changed=0 on all three nodes"
        output=command("exec","-T","--user","researcher","controller","python3","distributed.py",
                       "submit","--samples","1000000","--shards","8")
        result=json.loads(output)
        assert result["execution"]["serial_reference_matches"]
        summary["checks"]["distributed_result"]=result
        until(lambda: len(query('up{job="lab"} == 1'))==3)
        until(all_ready)
        assert http("http://127.0.0.1:13000/api/health")["database"]=="ok"
        dashboard=http("http://127.0.0.1:13000/api/dashboards/uid/research-lab")
        assert len(dashboard["dashboard"]["panels"])>=5
        summary["checks"]["monitoring"]="three exporters, two available workers, provisioned dashboard"
        try:
            controller("scontrol","update","NodeName=worker1","State=DRAIN","Reason=lab-acceptance")
            job=command("exec","-T","--user","researcher","controller","sbatch","--parsable",
                        "--nodelist=worker1","--mem=64M","--output=/shared/runs/drain-%j.log","--wrap","hostname").strip()
            pending=until(lambda: "PENDING" in controller("squeue","-h","-j",job,"-o","%T %R"))
            summary["checks"]["drained_worker_blocks_job"]=bool(pending)
            until(lambda: any(v["metric"]["node"]=="worker1" and v["value"][1]=="0"
                              for v in query("lab_slurm_node_available")))
        finally:
            controller("scontrol","update","NodeName=worker1","State=RESUME")
        until(lambda: "JobState=COMPLETED" in controller("scontrol","show","job",job))
        summary["checks"]["resume_runs_pending_job"]=True
        try:
            command("stop","worker2")
            alerts=until(lambda: [a for a in http("http://127.0.0.1:19090/api/v1/alerts")["data"]["alerts"]
                        if a["labels"]["alertname"]=="LabExporterDown" and a["labels"].get("instance")=="worker2:9108"
                        and a["state"]=="firing"], timeout=60)
            summary["checks"]["worker_outage_alert"]=alerts
        finally:
            command("start","worker2")
        until(lambda: len(query('up{job="lab"} == 1'))==3)
        until(all_ready)
        summary["checks"]["worker_recovered"]=True
        summary["status"]="passed"
    except Exception as error:
        summary["status"]="failed"
        summary["error"]=repr(error)
        raise
    finally:
        destination=ROOT/"runs"/"acceptance.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps({"summary":summary,"commands":evidence},indent=2)+"\n")
        print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
