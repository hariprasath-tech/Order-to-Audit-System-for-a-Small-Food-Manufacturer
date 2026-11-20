"""
Static code analysis guard test.
Fails the build if 'float(' or 'FloatField' is used anywhere under apps/ or config/.
Enforces absolute pure-Decimal financial and inventory integrity.
"""

from pathlib import Path

from django.conf import settings


def test_no_floats_in_apps_and_config():
    """
    Scans every Python file under apps/ and config/.
    Fails build immediately if float() or FloatField is detected.
    """
    base_dir = Path(settings.BASE_DIR)
    target_dirs = [base_dir / "apps", base_dir / "config"]
    violations = []

    for target_dir in target_dirs:
        for py_file in target_dir.rglob("*.py"):
            # Skip bytecode and migrations if any auto-generated
            if "__pycache__" in py_file.parts:
                continue

            with open(py_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    # Strip comments to allow documentation mentioning float
                    code_part = line.split("#")[0]

                    if "float(" in code_part:
                        violations.append(
                            f"{py_file.relative_to(base_dir)}:{line_num}: Disallowed 'float(' usage -> {line.strip()}"
                        )
                    if "FloatField" in code_part:
                        violations.append(
                            f"{py_file.relative_to(base_dir)}:{line_num}: Disallowed 'FloatField' usage -> {line.strip()}"
                        )

    assert not violations, (
        f"Static guard failed: Found {len(violations)} illegal float usage(s)!\n"
        + "\n".join(violations)
    )
