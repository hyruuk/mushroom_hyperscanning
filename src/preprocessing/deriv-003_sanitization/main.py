"""
1. Clean triggers (TODO: ceremony 2)
"""

from .clean_triggers import clean_triggers


def main(derivative_dir: str):
    # clean triggers
    clean_triggers(derivative_dir)
