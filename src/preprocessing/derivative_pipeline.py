import ast
import subprocess
from glob import glob
from os.path import dirname, join


def run():
    pipeline_dir = dirname(__file__)

    # discover all derivative scripts
    scripts = sorted(glob(join(pipeline_dir, "deriv-*", "main.py")))

    # parse multiline string at the top of each script (docstring)
    docstrings = "\n"
    for script in scripts:
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

    # run all scripts in order
    for script in scripts:
        print(f"Running {script}...")
        subprocess.run(["python", script], check=True)


def extract_module_docstring(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        file_content = file.read()
    module = ast.parse(file_content)
    docstring = ast.get_docstring(module)
    return docstring


if __name__ == "__main__":
    run()
