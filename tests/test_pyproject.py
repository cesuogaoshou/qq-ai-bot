import tomllib
from pathlib import Path


def test_runtime_dependencies_include_python_dotenv() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "python-dotenv>=1.0" in data["project"]["dependencies"]
