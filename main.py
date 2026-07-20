#!/usr/bin/env python3
"""
SOMEONE-CALL-ME
ฟังไมโครโฟน แล้วแจ้งเตือนเมื่อได้ยินชื่อของคุณ
(แม้เสียงไกล / ออกเสียงคล้าย ๆ กัน)

ใช้งาน:
  1. แก้ชื่อใน config.yaml
  2. pip install -r requirements.txt
  3. python main.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from someone_call_me.app import print_mics, run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ฟังไมโครโฟนแล้วแจ้งเตือนเมื่อมีคนเรียกชื่อคุณ",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="path ไปยัง config.yaml",
    )
    parser.add_argument(
        "--list-mics",
        action="store_true",
        help="แสดงรายการไมโครโฟนแล้วออก",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="แสดง log ละเอียด",
    )
    args = parser.parse_args()

    if args.list_mics:
        print_mics()
        return

    run(config_path=args.config, verbose=args.verbose)


if __name__ == "__main__":
    main()
