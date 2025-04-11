import shutil
import traceback
from os.path import exists, join
from shutil import copytree
from typing import Optional


def create_derivative_directory(
    derivative_name: str, bids_root: str, previous_derivative: Optional[str] = None, overwrite: bool = False
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
    previous_derivative : str, optional
        Path to the previous derivative dataset, by default None
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
            shutil.rmtree(target_dir)

    if previous_derivative is None:
        previous_derivative = bids_root

    print(
        f"{'Overwriting' if overwrite else 'Creating'} derivative {derivative_name} at "
        f"{join(bids_root, 'derivatives', derivative_name)}...",
        end="",
        flush=True,
    )
    copytree(
        previous_derivative,
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
        title = "Starting " + self.title
        width = len(title) + 4
        print("╒" + "═" * width + "╕")
        print(f"│ {title.center(width - 2)} │")
        print("╘" + "═" * width + "╛")

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            print()
            traceback.print_exception(exc_type, exc_value, tb)

            title = "Error in " + self.title + f" ({exc_type.__name__})"
            width = len(title) + 4
            print("╒" + "═" * width + "╕")
            print(f"│ {title.center(width - 2)} │")
            print("╘" + "═" * width + "╛")
        else:
            title = "Finished " + self.title
            width = len(title) + 4
            print("╒" + "═" * width + "╕")
            print(f"│ {title.center(width - 2)} │")
            print("╘" + "═" * width + "╛")
        return True
