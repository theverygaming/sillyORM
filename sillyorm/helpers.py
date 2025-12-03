import re
import hashlib
from .exceptions import SillyORMException


def str_hash(s: str, n: int) -> str:
    """
    Hashes a string

    :param s: The string to hash
    :type s: str
    :param n: The maximum length of the output hash
    :type n: int

    :return:
        The hash
    :rtype: str
    """
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return h[:n]


def sanitize_table_name(table_name: str) -> str:
    """
    Sanitizes an SQL table name

    :param table_name: The table name string to sanitize
    :type table_name: str

    :return:
        The sanitized table name
    :rtype: str
    """
    # first character (special)
    first = re.sub(r"[^a-zA-Z_]", "_", table_name[0])
    return first + re.sub(r"[^a-zA-Z0-9_]", "_", table_name[1:])


def sanitize_constraint_name(constraint_name: str, max_len: int = 60) -> str:
    """
    Sanitizes an SQL constraint name (may shorten it and hash the input)

    :param constraint_name: The constraint name string to sanitize
    :type constraint_name: str
    :param max_len: The maximum output length
    :type max_len: int

    :return:
        The sanitized constraint name
    :rtype: str
    """
    hash_len = 6
    if max_len < hash_len:
        raise SillyORMException(
            f"sanitize_constraint_name wants at least {hash_len} characters so the hash can fit"
        )
    cn = sanitize_table_name(constraint_name)
    if len(cn) > max_len:
        h = str_hash(cn, hash_len)
        return cn[: max_len - hash_len] + h
    return cn
