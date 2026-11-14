"""Strict identity inputs for research runs whose Git metadata is Windows-owned."""
import re


def full_commit(value):
    if not re.fullmatch(r'[0-9a-f]{40}',value):
        raise ValueError('Pass the full verified40-character native Git commit SHA')
    return value
