import subprocess
import sys


def test_importing_library_does_not_import_demo_dependencies() -> None:
    code = """
import sys
import pii_redactor
blocked = {'fastapi', 'uvicorn', 'httpx', 'langfuse'}
print(','.join(sorted(blocked & set(sys.modules))))
"""

    result = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)

    assert result.stdout.strip() == ""
