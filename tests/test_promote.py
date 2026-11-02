from types import SimpleNamespace

import pytest

from src.food11.promote import decide, promote


class FakeClient:
    def __init__(self, candidate_accuracy):
        self.aliases = {"champion": "1"}
        self.tags = {}
        self.runs = {
            "1": SimpleNamespace(info=SimpleNamespace(status="FINISHED"), data=SimpleNamespace(
                metrics={"test_accuracy": 0.8}, params={"test_images": "1000", "dataset_sha256": "same"})),
            "2": SimpleNamespace(info=SimpleNamespace(status="FINISHED"), data=SimpleNamespace(
                metrics={"test_accuracy": candidate_accuracy}, params={"test_images": "1000", "dataset_sha256": "same"})),
        }

    def get_model_version(self, name, version):
        return SimpleNamespace(version=str(version), run_id=str(version))

    def get_model_version_by_alias(self, name, alias):
        return self.get_model_version(name, self.aliases[alias])

    def get_run(self, run_id):
        return self.runs[run_id]

    def set_model_version_tag(self, name, version, key, value):
        self.tags[key] = value

    def set_registered_model_alias(self, name, alias, version):
        self.aliases[alias] = version


@pytest.mark.parametrize(("accuracy", "decision"), [(0.81, "challenger"), (0.9, "champion")])
def test_gate_mutations(accuracy, decision):
    client = FakeClient(accuracy)
    result = promote(client, "food11", "2")
    assert result["decision"] == decision
    assert client.aliases[decision] == "2"
    assert client.aliases["champion"] == ("2" if decision == "champion" else "1")
    assert client.tags["gate.decision"] == decision
    assert float(client.tags["gate.candidate_accuracy"]) == accuracy


def test_boundary_and_dry_run():
    threshold = decide(0.8, 0.8, 1000)["threshold"]
    assert decide(threshold, 0.8, 1000)["decision"] == "champion"
    client = FakeClient(0.9)
    assert promote(client, "food11", "2", dry_run=True)["decision"] == "champion"
    assert client.aliases == {"champion": "1"} and client.tags == {}


@pytest.mark.parametrize(("candidate", "champion", "n"), [(float("nan"), 0.8, 100), (0.9, 1.1, 100), (0.9, 0.8, 0)])
def test_invalid_numbers(candidate, champion, n):
    with pytest.raises(ValueError):
        decide(candidate, champion, n)


@pytest.mark.parametrize("problem", ["metric", "dataset", "size", "status"])
def test_gate_fails_closed(problem):
    client = FakeClient(0.9)
    if problem == "metric":
        client.runs["2"].data.metrics.clear()
    elif problem == "dataset":
        client.runs["2"].data.params["dataset_sha256"] = "different"
    elif problem == "size":
        client.runs["2"].data.params["test_images"] = "10"
    else:
        client.runs["2"].info.status = "FAILED"
    with pytest.raises(ValueError):
        promote(client, "food11", "2")
    assert client.aliases == {"champion": "1"} and client.tags == {}
