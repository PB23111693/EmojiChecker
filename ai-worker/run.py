"""AI 推理进程启动脚本。

用法：
    python run.py --config config.yaml
    python run.py --session-id 1 --no-display
    python run.py --video samples/demo.mp4 --once
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_worker.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
