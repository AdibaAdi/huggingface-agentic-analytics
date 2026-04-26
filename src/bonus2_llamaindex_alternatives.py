"""Bonus Assignment 2: LlamaIndex code execution alternatives."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionOutcome:
    ok: bool
    stdout: str
    stderr: str = ""
    notes: str = ""


class LlamaIndexCodeInterpreterAlternative:
    """Local-friendly placeholder for LlamaIndex Code Interpreter Tool integration."""

    def run(self, code: str) -> ExecutionOutcome:
        notes = (
            "Use llama-index-tools-code-interpreter package in a fully provisioned env. "
            "This local placeholder executes code via safe subprocess for demo purposes."
        )
        return run_python_subprocess(code, notes=notes)


class DockerPythonSandboxAlternative:
    """Run code in Docker python image if Docker is available."""

    def run(self, code: str) -> ExecutionOutcome:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name
        try:
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{script_path}:/tmp/script.py:ro",
                "python:3.11-slim",
                "python",
                "/tmp/script.py",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return ExecutionOutcome(proc.returncode == 0, proc.stdout, proc.stderr)
        except FileNotFoundError:
            return ExecutionOutcome(False, "", "Docker not installed.", "Install Docker Desktop/Engine first.")
        except Exception as exc:
            return ExecutionOutcome(False, "", str(exc), "Docker sandbox execution failed.")
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


class OpenAIHostedCodeExecutionAlternative:
    """Placeholder: OpenAI hosted code execution is evolving; keep abstraction ready."""

    def run(self, code: str) -> ExecutionOutcome:
        return ExecutionOutcome(
            ok=False,
            stdout="",
            stderr="Hosted code execution not enabled in this project template.",
            notes="Implement via future OpenAI tools/runtime APIs once available to your account.",
        )


class E2BCloudSandboxAlternative:
    """Optional E2B integration when E2B_API_KEY exists."""

    def run(self, code: str) -> ExecutionOutcome:
        key = os.getenv("E2B_API_KEY", "")
        if not key:
            return ExecutionOutcome(False, "", "E2B_API_KEY missing.", "Set E2B_API_KEY in .env to enable this path.")
        try:
            from e2b_code_interpreter import Sandbox

            with Sandbox(api_key=key) as sandbox:
                result = sandbox.run_code(code)
                stdout = "\n".join([x.text for x in result.logs.stdout]) if result.logs.stdout else ""
                stderr = "\n".join([x.text for x in result.logs.stderr]) if result.logs.stderr else ""
                return ExecutionOutcome(True, stdout, stderr, "Ran inside E2B cloud sandbox.")
        except Exception as exc:
            return ExecutionOutcome(False, "", str(exc), "E2B execution failed or SDK unavailable.")


def run_python_subprocess(code: str, notes: str = "") -> ExecutionOutcome:
    """Simple local fallback runner used by alternatives."""

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        proc = subprocess.run(["python", path], capture_output=True, text=True, timeout=20)
        return ExecutionOutcome(proc.returncode == 0, proc.stdout, proc.stderr, notes)
    except Exception as exc:
        return ExecutionOutcome(False, "", str(exc), notes)
    finally:
        if os.path.exists(path):
            os.remove(path)


def demo_all_alternatives(code: str = "print('hello from sandbox')") -> dict[str, ExecutionOutcome]:
    return {
        "llamaindex_code_interpreter": LlamaIndexCodeInterpreterAlternative().run(code),
        "docker_python_sandbox": DockerPythonSandboxAlternative().run(code),
        "openai_hosted_code_execution": OpenAIHostedCodeExecutionAlternative().run(code),
        "e2b_cloud_sandbox": E2BCloudSandboxAlternative().run(code),
    }
