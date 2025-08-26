
#!/usr/bin/env python3
import os, subprocess, sys
print("Running NLU evaluation (ensure backend is running)...")
res = subprocess.run([sys.executable, "tests/eval_nlu.py"], capture_output=False)
