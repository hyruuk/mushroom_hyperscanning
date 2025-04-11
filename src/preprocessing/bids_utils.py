import shutil
from os.path import exists, join
from shutil import copytree
from typing import Optional


def create_derivative_directory(
    derivative_name: str, bids_root: str, source_bids_root: Optional[str] = None, overwrite: bool = False
) -> str:
    """
    Copy the BIDS dataset at `source_bids_root` over to the `<bids_root>/derivatives` folder and name it `derivative_name`.
    If `source_bids_root` is None, the base BIDS dataset at `bids_root` will be copied.

    Parameters
    ----------
    derivative_name : str
        Name of the derivative dataset.
    bids_root : str
        Path to the root of the BIDS dataset.
    source_bids_root : str, optional
        Path to the root of the source BIDS dataset, by default None
    overwrite : bool, optional
        Whether to overwrite the derivative dataset if it already exists, by default False

    Returns
    -------
    str
        Path to the derivative dataset.
    """
    target_dir = join(bids_root, "derivatives", derivative_name)
    if exists(target_dir):
        if not overwrite:
            raise FileExistsError(f"Derivative {target_dir} already exists.")
        else:
            # remove the existing directory
            print(f"Overwriting derivative {target_dir}...")
            shutil.rmtree(target_dir)

    if source_bids_root is None:
        source_bids_root = bids_root

    print(f"Creating derivative {derivative_name} at {join(bids_root, 'derivatives', derivative_name)}...", end="", flush=True)
    copytree(
        source_bids_root,
        target_dir,
        ignore=lambda _, n: ["derivatives"] if "derivatives" in n else [],
        dirs_exist_ok=overwrite,
    )
    print("done")
    return target_dir


class PrintBlock:
    def __init__(self, title: str):
        self.title = title

    def __enter__(self):
        print("\n=============================")
        print(self.title)
        print("=============================")

    def __exit__(self, exc_type, exc_value, traceback):
        print("=============================")
