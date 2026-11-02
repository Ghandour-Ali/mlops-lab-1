"""Apply the lab's two-standard-error quality gate to an MLflow candidate."""
import argparse
import json
import math
from pathlib import Path


def decide(candidate: float, champion: float, n: int) -> dict:
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (candidate, champion)):
        raise ValueError("Accuracies must be finite values between 0 and 1")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("n must be a positive integer")
    se = math.sqrt(champion * (1 - champion) / n)
    threshold = champion + 2 * se
    return {"candidate_accuracy": candidate, "champion_accuracy": champion, "n": n,
            "standard_error": se, "margin": 2 * se, "threshold": threshold,
            "decision": "champion" if candidate >= threshold else "challenger"}


def promote(client, name: str, version: str, n=None, metric="test_accuracy", dry_run=False):
    incumbent = client.get_model_version_by_alias(name, "champion")
    candidate = client.get_model_version(name, str(version))
    if str(candidate.version) == str(incumbent.version):
        raise ValueError("Candidate already is champion")
    old_run = client.get_run(incumbent.run_id)
    new_run = client.get_run(candidate.run_id)
    if any(run.info.status != "FINISHED" for run in (old_run, new_run)):
        raise ValueError("Both evaluation runs must be FINISHED")
    old_data = old_run.data
    new_data = new_run.data
    if metric not in old_data.metrics or metric not in new_data.metrics:
        raise ValueError(f"Missing {metric}: evaluate both models before promotion")
    fingerprint = old_data.params.get("dataset_sha256")
    if not fingerprint or fingerprint != new_data.params.get("dataset_sha256"):
        raise ValueError("Candidate and champion must use the same verified dataset")
    old_n = int(old_data.params.get("test_images", "0"))
    new_n = int(new_data.params.get("test_images", "0"))
    if old_n <= 0 or old_n != new_n or (n is not None and n != old_n):
        raise ValueError("Evaluation sample counts do not match")
    result = decide(new_data.metrics[metric], old_data.metrics[metric], old_n)
    result.update({"name": name, "candidate_version": str(version),
                   "previous_champion_version": str(incumbent.version),
                   "metric": metric, "dataset_sha256": fingerprint, "dry_run": dry_run})
    if not dry_run:
        current = client.get_model_version_by_alias(name, "champion")
        if str(current.version) != str(incumbent.version):
            raise RuntimeError("Champion changed during comparison; retry the gate")
        for key, value in result.items():
            client.set_model_version_tag(name, str(version), "gate." + key, str(value))
        client.set_registered_model_alias(name, result["decision"], str(version))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--name", default="food11")
    parser.add_argument("--tracking-uri", default=None)
    parser.add_argument("--n", type=int)
    parser.add_argument("--metric", default="test_accuracy")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from mlflow import MlflowClient
    client = MlflowClient(tracking_uri=args.tracking_uri)
    result = promote(client, args.name, args.version, args.n, args.metric, args.dry_run)
    content = json.dumps(result, indent=2)
    print(content)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
