def set_defaults(d, defaults):
    if d is None:
        d = {}

    for key, value in defaults.items():
        d.setdefault(key, value)

    return d


def etree_convert(node, groups=None):
    if node.text and node.text.strip():
        return node.text

    if len(node) and node.tag.startswith(node[0].tag):
        return etree_list(node, groups)

    return etree_dict(node, groups)


def etree_dict(node, groups=None):
    result = {}
    result.update(node.attrib)

    cur_group = None
    cur_item = None

    for sub in node:
        sub_group = groups.get(sub.tag) if groups else None

        # Group match, reset state
        if sub_group:
            cur_group = sub_group
            cur_item = {}

        # Group
        if cur_group and sub.tag in cur_group:
            # New element found for group
            cur_item[sub.tag] = etree_convert(sub)

            if len(cur_item) == len(cur_group):
                # Group complete, append and reset
                if sub.tag not in result:
                    result[sub.tag] = []

                result[sub.tag].append(cur_item)

                cur_group = None
                cur_item = None

            continue

        # Basic element update
        result[sub.tag] = etree_convert(sub)

    return result


def etree_list(node, groups=None):
    return [etree_convert(sub, groups) for sub in node]


def convert(value, to_type, default=None):
    if value is None:
        return default

    try:
        return to_type(value)
    except:
        return default


def repr_trim(value, length=1000):
    value = repr(value)

    if len(value) < length:
        return value

    return '<%s - %s characters>' % (type(value).__name__, len(value))
