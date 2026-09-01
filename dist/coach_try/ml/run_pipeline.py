"""Train form models on synthetic_gym_dataset (or regenerate the old data/ml set)."""

import sys

from ml.train import train_all


def main():
    if "--legacy" in sys.argv:
        from ml.generate import export_dataset

        print("Generating legacy dataset into data/ml/...")
        split, path = export_dataset()
        print("Wrote", path)
        print(
            "Athletes train/val/test:",
            len(split["train"]),
            len(split["val"]),
            len(split["test"]),
        )
    print("Training...")
    train_all()
    print("Done. See models/form/metrics.json and docs/ml-report.md")


if __name__ == "__main__":
    main()
