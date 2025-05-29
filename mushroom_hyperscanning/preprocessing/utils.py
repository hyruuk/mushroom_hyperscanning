import shutil
from os.path import dirname, exists, join
from shutil import copytree
from typing import Optional


def create_derivative_directory(
    derivative_name: str, bids_root: str, previous_derivative: Optional[str] = None, overwrite: bool = False
) -> str:
    """
    Copy the BIDS dataset at `source_bids_root` over to the `<bids_root>/../<derivative_name>` folder.
    If `source_bids_root` is None, the base BIDS dataset at `bids_root` will be copied.

    Args:
        derivative_name (str): Name of the derivative directory to create.
        bids_root (str): Root directory of the BIDS dataset.
        previous_derivative (Optional[str]): Path to the previous derivative to copy from. If None, uses `bids_root`.
        overwrite (bool): Whether to overwrite the existing derivative directory if it exists.
    Returns:
        str: Path to the created derivative directory.
    """
    target_dir = join(dirname(bids_root), derivative_name)
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
    """
    A context manager that prints a block of text with a title, indicating the start and end of a process.
    It also handles exceptions by printing an error message if an exception occurs.
    """

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
