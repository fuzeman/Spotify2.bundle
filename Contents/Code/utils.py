def localized_format(key, args):
    """ Return the a localized string formatted with the given args """
    return str(L(key)) % args
