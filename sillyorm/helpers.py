import re


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
