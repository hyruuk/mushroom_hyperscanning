"""
1. Clean triggers (TODO: ceremony 2)
"""

from .reject import reject


def main(derivative_dir: str):
    # clean triggers
    reject(derivative_dir)
