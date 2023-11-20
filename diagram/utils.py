from collections.abc import Mapping


# https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
    return dct

def listify(element):
    """
    Converts the various forms of finger/position defs into a list of [ None, int ]
    """
    pass

def convert_int(item):
    """
    Used to coerce an item from an iterable to int, but to gracefully
    handle it already being so.
    Used to convert provided fret positions to integers (or None)
    """
    if isinstance(item, int):
        return item
    if isinstance(item, str):
        if item.isdigit():
            return int(item)
        else:
            return None
