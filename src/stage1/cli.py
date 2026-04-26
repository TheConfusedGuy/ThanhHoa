# -*- coding: utf-8 -*-
"""CLI entrypoint cho Giai đoạn 1.

Có thể chạy theo 2 cách:
  - python -m stage1.cli        (khi cwd là `src/`)
  - python src/stage1/cli.py    (khi cwd là root project)
"""

try:
    from .config import parse_args
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from stage1.config import parse_args


def main():
    cfg = parse_args()
    try:
        from .pipeline import run_stage1
    except ImportError:
        from stage1.pipeline import run_stage1
    run_stage1(cfg)


if __name__ == "__main__":
    main()
