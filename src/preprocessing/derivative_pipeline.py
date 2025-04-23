import ast
import importlib
import os
import shutil
from glob import glob
from os.path import dirname, join
from typing import Dict, Optional

from bids_utils import PrintBlock, create_derivative_directory

PIPELINE_DIR = dirname(__file__)
BIDS_ROOT = join(dirname(dirname(PIPELINE_DIR)), "data", "bids_dataset")


def extract_module_docstring(file_path: str) -> Optional[str]:
    """
    Extract the docstring from a Python module.

    Parameters
    ----------
    file_path : str
        Path to the Python module file.

    Returns
    -------
    str
        The docstring of the module, or None if no docstring is found.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    module = ast.parse(file_content)
    docstring = ast.get_docstring(module)
    return docstring


def update_readme(steps: Dict[str, str], pipeline_dir: str):
    """
    Update the README file with the docstrings of the derivative steps.

    Parameters
    ----------
    steps : Dict[str, str]
        Dictionary mapping step names to script paths.
    pipeline_dir : str
        Path to the pipeline directory.
    """
    # parse multiline string at the top of each script (docstring)
    docstrings = "\n"
    for script in steps.values():
        name = dirname(script).split("-")[-1]
        docstring = extract_module_docstring(script)
        if docstring is None:
            docstring = "TODO: no docstring found"
        docstrings += f"## {name}\n{docstring}\n"

    # find the start and end lines of the section to be replaced in the README
    with open(join(pipeline_dir, "README.md"), "r", encoding="utf-8") as readme:
        readme_content = [line.strip("\n") for line in readme.readlines()]
    start_line = [i for i, line in enumerate(readme_content) if "DERIVATIVE_STEPS_AUTOGENERATE_START" in line][0]
    end_line = [i for i, line in enumerate(readme_content) if "DERIVATIVE_STEPS_AUTOGENERATE_END" in line][0]

    # replace the section with the new content
    new_readme_content = readme_content[: start_line + 1] + [docstrings] + readme_content[end_line:]
    with open(join(pipeline_dir, "README.md"), "w", encoding="utf-8") as readme:
        readme.write("\n".join(new_readme_content))


def main(overwrite: bool = True):
    """
    This function discovers all derivative steps in the pipeline, runs them in order,
    and updates the README file with their docstrings.
    A derivative step is defined as a directory named `deriv-<name>` containing a `main.py` file. The `main.py` file
    should contain a `main` function that takes a single argument: the path to the derivative directory.

    Parameters
    ----------
    overwrite : bool, optional
        Whether to overwrite existing derivative directories
    """
    # discover all derivative steps in the pipeline
    steps_dirs = sorted(glob(join(PIPELINE_DIR, "deriv-*")))

    print(f"Found {len(steps_dirs)} derivative steps:")
    steps = []
    for step_dir in steps_dirs:
        # check if the directory contains a main.py file
        main_file = join(step_dir, "main.py")
        if os.path.isfile(main_file):
            steps.append(main_file)
            print(f" - {step_dir.split(os.sep)[-1].replace('deriv-', '')}")
        else:
            print(f"\nERROR: Derivative step {step_dir.split(os.sep)[-1]} must contain a main.py file.")
            return
    steps = {fname.split(os.sep)[-2].replace("deriv-", ""): fname for fname in steps}

    # update the README file with the docstrings of the derivative steps
    update_readme(steps, PIPELINE_DIR)

    # run all scripts in order
    previous_derivative = None
    for name in steps.keys():
        # check if the derivative already exists
        derivative_dir = join(dirname(BIDS_ROOT), name)
        if not overwrite and os.path.exists(derivative_dir):
            previous_derivative = derivative_dir
            print(f"Derivative {name} already finished, skipping.")
            continue

        # load the module
        module = importlib.import_module(f"deriv-{name}.main")
        if not hasattr(module, "main"):
            print(f"\nERROR: Derivative step {name} must contain a main function as the entry point.")
            return

        print()
        with PrintBlock(name):
            # create a new derivative directory for each step
            previous_derivative = derivative_dir = create_derivative_directory(
                name, BIDS_ROOT, previous_derivative, overwrite=overwrite
            )

            # run the main function of the module
            try:
                module.main(derivative_dir)
            except:
                # clean up the derivative directory if an error occurs
                shutil.rmtree(derivative_dir)
                raise


if __name__ == "__main__":
    main()
