import asyncio
from core.sandbox import run_sandboxed
from core.plugins import PluginManager
from pathlib import Path

async def run_tests():
    print("=== TEST 1: AST Guard on Dangerous Code ===")
    bad_code = "import os\nos.system('dir')"
    res1 = await run_sandboxed(bad_code)
    print(f"Success: {res1['success']}")
    print(f"Violation Detected: {res1['violation']}")
    assert res1['success'] is False
    assert "Forbidden module import" in res1['stderr']
    print("[PASS] Malicious import blocked successfully!\n")

    print("=== TEST 2: Safe Python Execution in Sandbox ===")
    safe_code = """
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)

print(f"Factorial 6 is {factorial(6)}")
"""
    res2 = await run_sandboxed(safe_code)
    print(f"Success: {res2['success']}")
    print(f"Output: {res2['stdout'].strip()}")
    assert res2['success'] is True
    assert "Factorial 6 is 720" in res2['stdout']
    print("[PASS] Safe computation executed cleanly!\n")

    print("=== TEST 3: Plugin Manager Discovery ===")
    mgr = PluginManager(Path(__file__).parent / "plugins")
    loaded = mgr.reload()
    print(f"Discovered Plugins: {loaded}")
    assert "get_system_info" in loaded
    assert "list_workspace_files" in loaded
    assert "web_search" in loaded

    sys_info = await mgr.execute("get_system_info", {})
    print(f"System Info Output: {sys_info}")
    assert "python_version" in sys_info
    print("[PASS] Plugin execution working flawlessly!\n")

    print("All core unit tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
