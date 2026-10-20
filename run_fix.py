from pathlib import Path
import json, sys
# Patch original constant before import
orig_path = Path("backtest_cached_20261019.py")
text = orig_path.read_text()
text = text.replace("ATR_MULTIPLIER = 1.5", "ATR_MULTIPLIER = 2.5")
# Also handle other values like 1.0 etc
import re
text = re.sub(r"^ATR_MULTIPLIER\s*=\s*[\d\.]+", "ATR_MULTIPLIER = 2.5", text, flags=re.M)
Path("backtest_cached_20261019_patched.py").write_text(text)

import importlib.util
spec = importlib.util.spec_from_file_location("patched", "backtest_cached_20261019_patched.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(f"ATR_MULTIPLIER now = {mod.ATR_MULTIPLIER}")

# Now run staged logic using patched module
import importlib.util as iu
spec2 = iu.spec_from_file_location("orig", "backtest_cached_20261019.py")
# we will reuse backtest_staged logic directly
import subprocess
subprocess.run(["python", "backtest_staged_20261019.py"])
