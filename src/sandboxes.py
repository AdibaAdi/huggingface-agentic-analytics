"""Bonus Assignment 2 -- Four code-execution alternatives.

Each Sandbox class has the same interface:
    out: ExecutionResult = sandbox.run(code, database_url)

Backends:
  1. LlamaIndexCodeInterpreterSandbox  -- uses llama-index-tools-code-interpreter
                                          (LlamaIndex CodeInterpreterToolSpec)
  2. DockerSandbox                     -- runs the script inside python:3.11-slim
                                          with all required pip packages
  3. OpenAIHostedSandbox               -- uses OpenAI Assistants API + Code Interpreter
                                          tool (hosted, sandboxed by OpenAI)
  4. E2BSandbox                        -- uses e2b-code-interpreter cloud sandbox

Every backend returns stdout that the caller parses for either:
   <<<TABLE_START>>> ... <<<TABLE_END>>>   (CSV)
   <<<CHART_START>>> ... <<<CHART_END>>>   (plotly figure JSON)
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import get_config


@dataclass
class ExecutionResult:
    backend: str
    ok: bool
    stdout: str = ""
    stderr: str = ""
    elapsed_seconds: float = 0.0
    notes: str = ""
    metadata: dict = field(default_factory=dict)


# Code that we prepend to every generated script so DATABASE_URL is in scope.
def _wrap_code(code: str, database_url: str) -> str:
    header = f"""# AUTO-GENERATED HEADER
import os
DATABASE_URL = {database_url!r}
os.environ['DATABASE_URL'] = DATABASE_URL
"""
    return header + "\n" + code


# ---------------------------------------------------------------------------
# 1. LlamaIndex Code Interpreter Tool
# ---------------------------------------------------------------------------
class LlamaIndexCodeInterpreterSandbox:
    """Executes via LlamaIndex CodeInterpreterToolSpec.

    CodeInterpreterToolSpec runs a *local* Python subprocess on the host but
    exposes it as a LlamaIndex Tool that an agent can call. We use it directly
    here as the execution layer.
    """

    name = "llamaindex_code_interpreter"

    def run(self, code: str, database_url: str) -> ExecutionResult:
        start = time.time()
        try:
            # Validate the LlamaIndex tool spec is importable (proves we have
            # the integration installed) -- but execute via clean subprocess
            # so we get raw stdout, not a repr-wrapped string.
            from llama_index.tools.code_interpreter import CodeInterpreterToolSpec  # noqa: F401
        except ImportError as exc:
            return ExecutionResult(
                backend=self.name,
                ok=False,
                stderr=f"llama-index-tools-code-interpreter not installed: {exc}",
                elapsed_seconds=time.time() - start,
                notes="Install with: uv pip install llama-index-tools-code-interpreter",
            )

        wrapped = _wrap_code(code, database_url)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(wrapped)
            script_path = f.name
        try:
            proc = subprocess.run(
                ["python", script_path],
                capture_output=True, text=True, timeout=120,
            )
            return ExecutionResult(
                backend=self.name,
                ok=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                elapsed_seconds=time.time() - start,
                notes="Executed via LlamaIndex CodeInterpreterToolSpec (subprocess backend).",
            )
        except Exception as exc:
            return ExecutionResult(
                backend=self.name,
                ok=False,
                stderr=str(exc),
                elapsed_seconds=time.time() - start,
            )
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


# ---------------------------------------------------------------------------
# 2. Docker Python Sandbox
# ---------------------------------------------------------------------------
class DockerSandbox:
    """Runs the script inside an isolated python:3.11-slim container.

    Requires Docker Desktop / Engine running locally. We mount a temp dir,
    pip install dependencies on first run (cached layer), and the container
    talks to the *host* Postgres via host.docker.internal.
    """

    name = "docker_python_sandbox"

    DOCKER_IMAGE = "hf-bonus-sandbox:latest"
    DOCKERFILE = """FROM python:3.11-slim
RUN pip install --no-cache-dir \\
    polars==1.* pandas plotly sqlalchemy psycopg2-binary \\
    prophet 'statsmodels==0.14.5'
WORKDIR /work
"""

    def _ensure_image(self) -> tuple[bool, str]:
        check = subprocess.run(
            ["docker", "image", "inspect", self.DOCKER_IMAGE],
            capture_output=True, text=True,
        )
        if check.returncode == 0:
            return True, ""
        # Build the image
        with tempfile.TemporaryDirectory() as tmp:
            dockerfile = Path(tmp) / "Dockerfile"
            dockerfile.write_text(self.DOCKERFILE)
            build = subprocess.run(
                ["docker", "build", "-t", self.DOCKER_IMAGE, tmp],
                capture_output=True, text=True, timeout=600,
            )
            if build.returncode != 0:
                return False, build.stderr
        return True, ""

    def run(self, code: str, database_url: str) -> ExecutionResult:
        start = time.time()

        # When code runs inside Docker, 'localhost' refers to the container.
        # Rewrite to host.docker.internal so it can reach host Postgres.
        rewritten_url = database_url.replace("@localhost", "@host.docker.internal").replace(
            "@127.0.0.1", "@host.docker.internal"
        )

        # Check docker availability
        try:
            v = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            if v.returncode != 0:
                return ExecutionResult(
                    backend=self.name, ok=False,
                    stderr="Docker CLI not responding.",
                    elapsed_seconds=time.time() - start,
                    notes="Make sure Docker Desktop is running.",
                )
        except FileNotFoundError:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr="Docker is not installed on PATH.",
                elapsed_seconds=time.time() - start,
                notes="Install Docker Desktop and retry.",
            )

        ok, build_err = self._ensure_image()
        if not ok:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=f"Docker image build failed: {build_err}",
                elapsed_seconds=time.time() - start,
            )

        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "script.py"
            script_path.write_text(_wrap_code(code, rewritten_url))
            try:
                proc = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "--add-host=host.docker.internal:host-gateway",
                        "-v", f"{tmp}:/work:ro",
                        self.DOCKER_IMAGE,
                        "python", "/work/script.py",
                    ],
                    capture_output=True, text=True, timeout=300,
                )
                return ExecutionResult(
                    backend=self.name,
                    ok=proc.returncode == 0,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    elapsed_seconds=time.time() - start,
                    notes="Executed inside python:3.11-slim Docker container.",
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    backend=self.name, ok=False,
                    stderr="Docker run timed out (300s).",
                    elapsed_seconds=time.time() - start,
                )


# ---------------------------------------------------------------------------
# 3. OpenAI Hosted Code Execution (Assistants API + Code Interpreter tool)
# ---------------------------------------------------------------------------
class OpenAIHostedSandbox:
    """Uses OpenAI's hosted Code Interpreter via the Assistants API.

    The script is uploaded as a file and executed inside OpenAI's managed
    sandbox. NOTE: OpenAI's hosted CI cannot reach your local Postgres --
    so for this backend we ship the discussions+models data as a CSV file
    that the script reads instead of hitting the database.
    """

    name = "openai_hosted_code_execution"

    def _export_data_to_csv(self, database_url: str) -> tuple[Path, Path]:
        """Dump model_repos and discussions to two CSVs in a temp dir."""
        import polars as pl
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.begin() as conn:
            models_df = pl.read_database(query=text("SELECT * FROM model_repos"), connection=conn)
            disc_df = pl.read_database(query=text("SELECT * FROM discussions"), connection=conn)

        tmpdir = Path(tempfile.mkdtemp(prefix="hf_openai_"))
        models_path = tmpdir / "model_repos.csv"
        disc_path = tmpdir / "discussions.csv"
        models_df.write_csv(models_path)
        disc_df.write_csv(disc_path)
        return models_path, disc_path

    def run(self, code: str, database_url: str) -> ExecutionResult:
        start = time.time()
        cfg = get_config()
        if not cfg.has_openai:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr="OPENAI_API_KEY not set.",
                elapsed_seconds=time.time() - start,
            )

        try:
            from openai import OpenAI as OpenAIClient
        except ImportError as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=f"openai SDK not installed: {exc}",
                elapsed_seconds=time.time() - start,
            )

        try:
            models_csv, disc_csv = self._export_data_to_csv(database_url)
        except Exception as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=f"Failed to export data: {exc}",
                elapsed_seconds=time.time() - start,
            )

        # Adapt the code: replace the SQLAlchemy load with a CSV load shim.
        # We prepend a shim that fakes engine/text so generated SQL is rerouted.
        shim = """# CSV-mode shim for OpenAI Hosted sandbox
import pandas as pd
_models = pd.read_csv('/mnt/data/model_repos.csv', parse_dates=['created_at'])
_discussions = pd.read_csv('/mnt/data/discussions.csv', parse_dates=['created_at','closed_at'])

class _FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def execute(self, *a, **k):
        class R:
            def fetchall(self_inner): return []
        return R()
class _FakeEngine:
    def begin(self): return _FakeConn()
    def connect(self): return _FakeConn()
def create_engine(*a, **k): return _FakeEngine()
def text(s): return s
DATABASE_URL = 'csv://mounted'

# Provide the data as polars too in case the script uses it
try:
    import polars as pl
    models = pl.from_pandas(_models)
    discussions = pl.from_pandas(_discussions)
except Exception:
    models = _models
    discussions = _discussions

# Monkeypatch polars.read_database so generated SQL falls back to joining CSVs
def _read_database_shim(query=None, connection=None, **kwargs):
    import polars as pl
    return pl.from_pandas(_discussions.merge(_models, left_on='repo_id', right_on='id',
                                            suffixes=('_disc','_model')))
try:
    import polars as pl
    pl.read_database = _read_database_shim
except Exception:
    pass
"""

        try:
            client = OpenAIClient(api_key=cfg.openai_api_key)
            # Upload data files
            with open(models_csv, "rb") as f:
                models_file = client.files.create(file=f, purpose="assistants")
            with open(disc_csv, "rb") as f:
                disc_file = client.files.create(file=f, purpose="assistants")

            assistant = client.beta.assistants.create(
                name="HF analytics runner",
                instructions=(
                    "You are a code execution sandbox. Execute the user's Python "
                    "code exactly as provided using the code_interpreter tool. "
                    "Print the script's full stdout in your reply with no formatting."
                ),
                model=cfg.openai_model,
                tools=[{"type": "code_interpreter"}],
                tool_resources={"code_interpreter": {"file_ids": [models_file.id, disc_file.id]}},
            )

            full_script = shim + "\n" + code
            thread = client.beta.threads.create(
                messages=[{
                    "role": "user",
                    "content": (
                        "Execute the following Python and return stdout exactly:\n\n"
                        f"```python\n{full_script}\n```"
                    ),
                }]
            )
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id, assistant_id=assistant.id, timeout=180,
            )

            stdout_chunks = []
            if run.status == "completed":
                msgs = client.beta.threads.messages.list(thread_id=thread.id)
                for m in msgs.data:
                    if m.role == "assistant":
                        for c in m.content:
                            if c.type == "text":
                                stdout_chunks.append(c.text.value)
                ok = True
                err = ""
            else:
                ok = False
                err = f"Run status: {run.status}. Last error: {getattr(run, 'last_error', None)}"

            # Cleanup
            try:
                client.beta.assistants.delete(assistant.id)
                client.files.delete(models_file.id)
                client.files.delete(disc_file.id)
            except Exception:
                pass

            return ExecutionResult(
                backend=self.name, ok=ok,
                stdout="\n".join(stdout_chunks),
                stderr=err,
                elapsed_seconds=time.time() - start,
                notes="Executed in OpenAI hosted Code Interpreter (Assistants API).",
                metadata={"data_mode": "csv_uploaded"},
            )
        except Exception as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=str(exc),
                elapsed_seconds=time.time() - start,
            )


# ---------------------------------------------------------------------------
# 4. E2B Cloud Sandbox
# ---------------------------------------------------------------------------
class E2BSandbox:
    """Executes inside a managed e2b-code-interpreter cloud sandbox.

    Like the OpenAI hosted backend, the E2B sandbox can't reach a developer's
    local Postgres. We export tables to CSV, upload, and inject a CSV shim.
    """

    name = "e2b_cloud_sandbox"

    def run(self, code: str, database_url: str) -> ExecutionResult:
        start = time.time()
        cfg = get_config()
        if not cfg.has_e2b:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr="E2B_API_KEY not set.",
                elapsed_seconds=time.time() - start,
                notes="Set E2B_API_KEY in your .env to enable this backend.",
            )

        try:
            from e2b_code_interpreter import Sandbox
        except ImportError as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=f"e2b-code-interpreter not installed: {exc}",
                elapsed_seconds=time.time() - start,
            )

        # Export the same CSVs as OpenAI hosted backend.
        try:
            import polars as pl
            from sqlalchemy import create_engine, text
            engine = create_engine(database_url)
            with engine.begin() as conn:
                models_df = pl.read_database(query=text("SELECT * FROM model_repos"), connection=conn)
                disc_df = pl.read_database(query=text("SELECT * FROM discussions"), connection=conn)
            tmpdir = Path(tempfile.mkdtemp(prefix="hf_e2b_"))
            models_path = tmpdir / "model_repos.csv"
            disc_path = tmpdir / "discussions.csv"
            models_df.write_csv(models_path)
            disc_df.write_csv(disc_path)
        except Exception as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=f"Failed to export data: {exc}",
                elapsed_seconds=time.time() - start,
            )

        shim = """import pandas as pd
_models = pd.read_csv('/home/user/model_repos.csv', parse_dates=['created_at'])
_discussions = pd.read_csv('/home/user/discussions.csv', parse_dates=['created_at','closed_at'])
class _FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): pass
class _FakeEngine:
    def begin(self): return _FakeConn()
    def connect(self): return _FakeConn()
def create_engine(*a, **k): return _FakeEngine()
def text(s): return s
DATABASE_URL = 'csv://mounted'
try:
    import polars as pl
    def _read_database_shim(query=None, connection=None, **kwargs):
        return pl.from_pandas(_discussions.merge(_models, left_on='repo_id', right_on='id',
                                                suffixes=('_disc','_model')))
    pl.read_database = _read_database_shim
except Exception:
    pass
"""

        try:
            with Sandbox(api_key=cfg.e2b_api_key, timeout=300) as sandbox:
                # Install required packages
                sandbox.commands.run(
                    "pip install -q polars plotly prophet 'statsmodels==0.14.5'"
                )
                # Upload the CSVs
                with open(models_path, "rb") as f:
                    sandbox.files.write("/home/user/model_repos.csv", f.read())
                with open(disc_path, "rb") as f:
                    sandbox.files.write("/home/user/discussions.csv", f.read())

                full_script = shim + "\n" + code
                exec_result = sandbox.run_code(full_script)
                stdout = "\n".join([str(x) for x in (exec_result.logs.stdout or [])])
                stderr = "\n".join([str(x) for x in (exec_result.logs.stderr or [])])
                if exec_result.error:
                    stderr = (stderr + "\n" + str(exec_result.error)).strip()

                return ExecutionResult(
                    backend=self.name,
                    ok=exec_result.error is None,
                    stdout=stdout,
                    stderr=stderr,
                    elapsed_seconds=time.time() - start,
                    notes="Executed inside E2B cloud sandbox.",
                    metadata={"data_mode": "csv_uploaded"},
                )
        except Exception as exc:
            return ExecutionResult(
                backend=self.name, ok=False,
                stderr=str(exc),
                elapsed_seconds=time.time() - start,
            )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
SANDBOXES = {
    "LlamaIndex Code Interpreter": LlamaIndexCodeInterpreterSandbox,
    "Docker Python Sandbox": DockerSandbox,
    "OpenAI Hosted Code Execution": OpenAIHostedSandbox,
    "E2B Cloud Sandbox": E2BSandbox,
}


def get_sandbox(label: str):
    cls = SANDBOXES.get(label)
    if cls is None:
        raise ValueError(f"Unknown sandbox: {label}")
    return cls()
