from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path(r"D:\crypto\okx\data\swap\BTC-USDT-SWAP.parquet")
DEFAULT_OUTPUT = Path(__file__).with_name("ret_10m.parquet")


def build_factor(input_path: Path, window: int) -> pd.DataFrame:
    frame = pd.read_parquet(input_path, columns=["datetime_utc", "close"])
    timestamp = pd.DatetimeIndex(
        pd.to_datetime(frame["datetime_utc"], utc=True, errors="raise")
    ).as_unit("ns")
    if timestamp.has_duplicates:
        raise ValueError(f"K-line data contains duplicate timestamps: {input_path}")

    close = pd.Series(frame["close"].to_numpy(), index=timestamp).sort_index()
    factor = close / close.shift(window) - 1
    return factor.rename("factor").to_frame().rename_axis("timestamp")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args()

    if args.window <= 0:
        parser.error("--window must be greater than zero")
    if not args.input.is_file():
        parser.error(f"K-line parquet not found: {args.input}")

    factor = build_factor(args.input, args.window)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    factor.to_parquet(args.output, index=True)
    print(f"Wrote {len(factor)} rows to {args.output.resolve()}")


if __name__ == "__main__":
    main()
