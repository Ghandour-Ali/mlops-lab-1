"""Verify the Lab 4 stack and disposable persistence experiments."""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from mlflow import MlflowClient

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "lab4"


def docker(*args):
    result = subprocess.run(["docker", *args], cwd=ROOT, text=True,
                            encoding="utf-8", errors="replace", capture_output=True, timeout=240)
    if result.returncode:
        raise RuntimeError(f"docker {args}: {result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def compose(*args):
    return docker("compose", *args)


def wait_http(url):
    for _ in range(90):
        try:
            if requests.get(url, timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"Not ready: {url}")


def model_info():
    return json.loads(compose("exec", "-T", "frontend", "python", "-c",
        "import requests,json; print(json.dumps(requests.get('http://inference:8000/model',timeout=10).json()))"))


def integration(evidence):
    assert requests.get("http://127.0.0.1:8501/", timeout=10).status_code == 200
    assert requests.get("http://127.0.0.1:8501/_stcore/health", timeout=10).text == "ok"
    evidence["frontend_http"] = 200
    evidence["compose_ps"] = [{k: row.get(k) for k in ("Service", "State", "Health", "Ports")} for row in map(json.loads, compose("ps", "--format", "json").splitlines())]
    frontend = compose("ps", "-q", "frontend")
    docker("cp", str(ROOT / "data_preview"), f"{frontend}:/tmp/data_preview")
    docker("cp", str(ROOT / "scripts/test_serving.py"), f"{frontend}:/tmp/test_serving.py")
    evidence["api_tests"] = compose("exec", "-T", "frontend", "python", "/tmp/test_serving.py",
        "--url", "http://inference:8000", "--images", "/tmp/data_preview", "--output", "/tmp/api-tests.json")
    docker("cp", f"{frontend}:/tmp/api-tests.json", str(OUT / "api-tests.json"))
    ui_test = """
import io,json
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
class Upload(io.BytesIO):
    name = 'class_0.jpg'
    type = 'image/jpeg'
uploaded = Upload(Path('/tmp/data_preview/class_0.jpg').read_bytes())
with patch('streamlit.file_uploader', return_value=uploaded):
    app = AppTest.from_file('/app/app.py').run(timeout=30)
    assert not app.exception, str(app.exception)
    app.button[0].click().run(timeout=60)
    assert not app.exception, str(app.exception)
    assert len(app.success) == 1 and len(app.metric) == 1
    print(json.dumps({'category_display': app.success[0].value, 'confidence_display': app.metric[0].value}))
"""
    evidence["streamlit_upload_click"] = json.loads(compose("exec", "-T", "frontend", "python", "-c", ui_test))
    client = MlflowClient(tracking_uri="http://127.0.0.1:5500")
    old = client.get_model_version_by_alias("food11", "champion")
    before = model_info()
    assert before["loaded_version"] == old.version
    new = client.create_model_version("food11", old.source, run_id=old.run_id)
    client.set_registered_model_alias("food11", "champion", new.version)
    without_restart = model_info()
    assert without_restart["loaded_version"] == old.version
    compose("restart", "inference")
    compose("up", "-d", "--wait", "--wait-timeout", "180")
    after = model_info()
    assert after["loaded_version"] == new.version
    evidence["promotion"] = {"before": before, "after_alias_change": without_restart,
                             "after_restart": after, "same_weights": True}
    compose("down")
    compose("up", "-d", "--wait", "--wait-timeout", "180")
    assert client.get_model_version_by_alias("food11", "champion").version == new.version
    assert model_info()["loaded_version"] == new.version
    evidence["operational_down_up"] = {"alias_preserved": True,
        "model_loads_from_preserved_artifacts": True, "version": new.version}


def persistence(evidence):
    name = "food11-lab4-no-volume-check"
    assert not docker("ps", "-aq", "--filter", f"name=^/{name}$"), "Test container already exists"
    def start_empty():
        docker("run", "-d", "--name", name, "-p", "127.0.0.1:5501:5000", "food11-lab4-mlflow:local")
        wait_http("http://127.0.0.1:5501/health")
    try:
        start_empty()
        client = MlflowClient(tracking_uri="http://127.0.0.1:5501")
        client.create_registered_model("persistence-sentinel")
        docker("stop", name)
        docker("start", name)
        wait_http("http://127.0.0.1:5501/health")
        assert len(client.search_registered_models()) == 1
        docker("rm", "-f", name)
        start_empty()
        assert len(client.search_registered_models()) == 0
        evidence["without_volume"] = {"stop_start_preserves": True, "remove_recreate_loses_registry": True}
    finally:
        docker("rm", "-f", name)
    scratch = ROOT / "local_results/lab4-persistence"
    scratch.mkdir(parents=True, exist_ok=True)
    config = scratch / "compose.yml"
    config.write_text("""name: food11-lab4-persistence-check
services:
  mlflow:
    image: food11-lab4-mlflow:local
    ports: ["127.0.0.1:5501:5000"]
    volumes: ["test-data:/mlflow-data"]
volumes:
  test-data:
""")
    assert not docker("volume", "ls", "-q", "--filter", "name=^food11-lab4-persistence-check_test-data$")
    def temporary(*args):
        return docker("compose", "-f", str(config), *args)
    try:
        temporary("up", "-d")
        wait_http("http://127.0.0.1:5501/health")
        client = MlflowClient(tracking_uri="http://127.0.0.1:5501")
        client.create_registered_model("persistence-sentinel")
        temporary("down")
        temporary("up", "-d")
        wait_http("http://127.0.0.1:5501/health")
        assert len(client.search_registered_models()) == 1
        temporary("down", "-v")
        temporary("up", "-d")
        wait_http("http://127.0.0.1:5501/health")
        assert len(client.search_registered_models()) == 0
        evidence["disposable_volume"] = {"down_up_preserves": True, "down_v_up_loses_registry": True}
    finally:
        temporary("down", "-v")


def failure(evidence):
    name = "food11-lab4-startup-failure-check"
    assert not docker("ps", "-aq", "--filter", f"name=^/{name}$")
    try:
        docker("run", "-d", "--name", name, "--network", "none",
               "-e", "MLFLOW_TRACKING_URI=http://127.0.0.1:9",
               "-e", "MLFLOW_HTTP_REQUEST_MAX_RETRIES=0", "food11-lab4-inference:local")
        exit_code = docker("wait", name)
        assert exit_code != "0"
        result = subprocess.run(["docker", "logs", name], text=True, encoding="utf-8",
                                errors="replace", capture_output=True, timeout=20)
        logs = result.stdout + result.stderr
        (OUT / "startup-failure.log").write_text(logs, encoding="utf-8")
        assert "Application startup failed" in logs
        evidence["unready_mlflow"] = {"inference_exit_code": exit_code, "startup_failed": True}
    finally:
        docker("rm", "-f", name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["all", "integration", "persistence", "failure"], default="all")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "integration.json"
    evidence = json.loads(path.read_text()) if path.exists() and args.phase != "all" else {}
    for name, check in [("integration", integration), ("persistence", persistence), ("failure", failure)]:
        if args.phase in ("all", name):
            check(evidence)
            evidence["tested_at_utc"] = datetime.now(timezone.utc).isoformat()
            evidence["final_model"] = model_info()
            path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            print(f"PASS: {name}", flush=True)


if __name__ == "__main__":
    main()
