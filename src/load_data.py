import os
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

# Define expected columns for each dataset
EXPECTED_JOBS_COLUMNS = ["job_id", "job_title", "sector", "district", "job_description"]
EXPECTED_CURRICULUM_COLUMNS = ["course_id", "course_name", "sector", "skills_taught"]

# Default data directory relative to repository root
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"


def load_jobs_data(file_path: Optional[Path | str] = None) -> Optional[pd.DataFrame]:
    """
    Load and validate the jobs CSV dataset into a pandas DataFrame.
    """
    path = Path(file_path) if file_path else DEFAULT_DATA_DIR / "jobs_sample.csv"

    if not path.exists():
        print(f"[ERROR] Jobs data file not found at: {path}")
        return None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Failed to read jobs CSV file '{path}': {e}")
        return None

    missing_cols = [col for col in EXPECTED_JOBS_COLUMNS if col not in df.columns]
    if missing_cols:
        print(
            f"[ERROR] Jobs dataset column mismatch in '{path}'. "
            f"Missing required columns: {missing_cols}. Found columns: {list(df.columns)}"
        )
        return None

    return df


def load_curriculum_data(file_path: Optional[Path | str] = None) -> Optional[pd.DataFrame]:
    """
    Load and validate the curriculum CSV dataset into a pandas DataFrame.
    """
    path = Path(file_path) if file_path else DEFAULT_DATA_DIR / "curriculum_sample.csv"

    if not path.exists():
        print(f"[ERROR] Curriculum data file not found at: {path}")
        return None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Failed to read curriculum CSV file '{path}': {e}")
        return None

    missing_cols = [col for col in EXPECTED_CURRICULUM_COLUMNS if col not in df.columns]
    if missing_cols:
        print(
            f"[ERROR] Curriculum dataset column mismatch in '{path}'. "
            f"Missing required columns: {missing_cols}. Found columns: {list(df.columns)}"
        )
        return None

    return df


def load_all_data(
    jobs_path: Optional[Path | str] = None,
    curriculum_path: Optional[Path | str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load both jobs and curriculum datasets.
    """
    jobs_df = load_jobs_data(jobs_path)
    curriculum_df = load_curriculum_data(curriculum_path)
    return jobs_df, curriculum_df


def display_dataframe_summary(name: str, df: Optional[pd.DataFrame]) -> None:
    """
    Prints row counts, column names, and the first 3 rows of a dataset.
    """
    print(f"\n{'=' * 60}")
    print(f" DATASET SUMMARY: {name.upper()}")
    print(f"{'=' * 60}")

    if df is None:
        print(f"[ERROR] Unable to display summary because {name} DataFrame is None.")
        return

    print(f"Row count    : {len(df)}")
    print(f"Column count : {len(df.columns)}")
    print(f"Column names : {list(df.columns)}\n")
    print("First 3 rows:")
    print(df.head(3).to_string(index=False))


def main():
    jobs_df, curriculum_df = load_all_data()

    display_dataframe_summary("Jobs Sample", jobs_df)
    display_dataframe_summary("Curriculum Sample", curriculum_df)


if __name__ == "__main__":
    main()
