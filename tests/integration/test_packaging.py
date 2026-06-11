"""Regression guard: non-Python data files must ship in the built wheel.

setuptools ships only ``.py`` files unless ``package-data`` is declared. A missing
declaration silently drops the admin template (``TemplateDoesNotExist`` on install) and
the PEP 561 marker. The rest of the suite runs against an editable install, so it never
exercises a built wheel and cannot catch this — hence this dedicated build-and-inspect test.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Files that must be present in the wheel but are NOT Python modules.
REQUIRED_ARCNAMES = [
    "django_query_optimizer/py.typed",
    "django_query_optimizer/templates/django_query_optimizer/admin/change_list.html",
]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> zipfile.ZipFile:
    """Build a wheel from the project root and return it opened as a zip archive.

    Uses ``--no-build-isolation`` so the already-installed setuptools/wheel are used
    (no network), matching the offline Docker test image.
    """
    if not (PROJECT_ROOT / "pyproject.toml").exists():
        pytest.skip(f"project root not found at {PROJECT_ROOT}")

    out_dir = tmp_path_factory.mktemp("wheel")
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(PROJECT_ROOT),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"wheel build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")

    wheels = list(out_dir.glob("django_query_optimizer-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return zipfile.ZipFile(wheels[0])


@pytest.mark.parametrize("arcname", REQUIRED_ARCNAMES)
def test_data_file_is_in_wheel(built_wheel: zipfile.ZipFile, arcname: str) -> None:
    assert arcname in built_wheel.namelist(), (
        f"{arcname!r} missing from wheel; check [tool.setuptools.package-data] in pyproject.toml. "
        f"Wheel contents: {built_wheel.namelist()}"
    )
