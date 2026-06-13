from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "n8n_workflows"


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.json"))


def _node_body_parameter_names(node: dict) -> set[str]:
    parameters = (
        node.get("parameters", {})
        .get("bodyParameters", {})
        .get("parameters", [])
    )
    return {parameter.get("name", "") for parameter in parameters}


def _node_body_parameter_value(node: dict, name: str) -> str:
    parameters = (
        node.get("parameters", {})
        .get("bodyParameters", {})
        .get("parameters", [])
    )
    for parameter in parameters:
        if parameter.get("name") == name:
            return str(parameter.get("value", ""))
    return ""


def test_docker_compose_requires_env_secrets_and_binds_n8n_locally():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "yemektest2024" not in compose
    assert "N8N_BASIC_AUTH_PASSWORD:-" not in compose
    assert "POSTGRES_PASSWORD: yemektest" not in compose
    assert "DB_POSTGRESDB_PASSWORD: yemektest" not in compose
    assert "${N8N_BASIC_AUTH_PASSWORD:?" in compose
    assert "${POSTGRES_PASSWORD:?" in compose
    assert "${N8N_ENCRYPTION_KEY:?" in compose

    assert '      - "5678:5678"' not in compose
    assert '      - "127.0.0.1:5678:5678"' in compose


def test_docker_compose_enables_n8n_security_controls():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    required_settings = [
        'N8N_BLOCK_ENV_ACCESS_IN_NODE: "true"',
        'N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES: "true"',
        'N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS: "true"',
        'EXECUTIONS_DATA_PRUNE: "true"',
        "EXECUTIONS_DATA_MAX_AGE: 168",
        "EXECUTIONS_DATA_PRUNE_MAX_COUNT: 1000",
        "n8n-nodes-base.executeCommand",
        "n8n-nodes-base.readWriteFile",
    ]
    for setting in required_settings:
        assert setting in compose


def test_workflows_are_parseable_and_do_not_contain_hardcoded_secrets():
    forbidden_literals = [
        "yemektest2024",
        "sk-",
        "xoxb-",
        "N8N_BASIC_AUTH_PASSWORD",
        "POSTGRES_PASSWORD",
    ]

    for path in _workflow_files():
        raw = path.read_text(encoding="utf-8")
        json.loads(raw)
        for literal in forbidden_literals:
            assert literal not in raw, f"{path.name} contains forbidden literal {literal}"


def test_orchestrate_workflow_nodes_always_send_profile_and_test_type():
    for path in _workflow_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        orchestrate_nodes = [
            node
            for node in data.get("nodes", [])
            if node.get("parameters", {}).get("url") == "http://orchestrator:8000/api/orchestrate"
        ]
        for node in orchestrate_nodes:
            body_names = _node_body_parameter_names(node)
            assert {"task", "profile", "test_type"}.issubset(body_names), path.name


def test_orchestrate_workflows_stop_on_safety_violation_before_reporting_success():
    for path in _workflow_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        has_orchestrate = any(
            node.get("parameters", {}).get("url") == "http://orchestrator:8000/api/orchestrate"
            for node in data.get("nodes", [])
        )
        if not has_orchestrate:
            continue

        node_names = {node.get("name") for node in data.get("nodes", [])}
        assert "Check Safety Violation" in node_names, path.name
        assert "Stop Safety Violation" in node_names, path.name

        safety_node = next(node for node in data["nodes"] if node.get("name") == "Check Safety Violation")
        conditions = safety_node["parameters"]["conditions"]["conditions"]
        assert any(condition["rightValue"] == "Safety policy violation" for condition in conditions)


def test_prod_smoke_workflow_is_read_only_and_separate_from_mock_regression():
    data = json.loads((WORKFLOWS / "prod_smoke_pipeline.json").read_text(encoding="utf-8"))
    orchestrate = next(
        node
        for node in data["nodes"]
        if node.get("parameters", {}).get("url") == "http://orchestrator:8000/api/orchestrate"
    )

    assert _node_body_parameter_value(orchestrate, "profile") == "web-prod-smoke"
    assert _node_body_parameter_value(orchestrate, "test_type") == "prod-smoke"

    task = _node_body_parameter_value(orchestrate, "task").lower()
    forbidden_live_terms = ["checkout", "payment", "order", "cart", "coupon", "login"]
    assert all(term not in task for term in forbidden_live_terms)


def test_env_files_are_ignored_by_git():
    result = subprocess.run(
        ["git", "check-ignore", "-v", ".env", ".env.local", "mock_ui/.env"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert ".env" in result.stdout
    assert ".env.local" in result.stdout
    assert "mock_ui/.env" in result.stdout
