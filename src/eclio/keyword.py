def until_space(string):
    """
    returns the given string until the first space.
    Similar to string.split(max_split=1)[0] except
    initial spaces are not ignored:
    >>> until_space(" hello")
    ''
    >>> until_space("hello world")
    'hello'

    """
    result = ""
    for w in string:
        if w.isspace():
            return result
        result += w
    return result


def match_keyword(kw1, kw2):
    """
    Perhaps surprisingly, the eclipse input format considers keywords
    as 8 character strings with space denoting end. So PORO, 'PORO ', and
    'PORO    ' are all considered the same keyword.

    >>> match_keyword("PORO", "PORO ")
    True
    >>> match_keyword("PORO", "PERM")
    False

    """
    return until_space(kw1) == until_space(kw2)
