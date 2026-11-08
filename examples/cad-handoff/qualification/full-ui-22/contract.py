"""Exact multi-asset native observation contracts; no CAD mutation or fuzzy matching."""


def require(ok, message):
    if not ok: raise ValueError(message)


def group_native(observation):
    groups = {}; ids = set(); handles = set()
    for row in observation['attributes']:
        parent = row['parent_id']; native_id = row['id']; handle = row['handle']
        require(native_id not in ids and handle not in handles, 'Duplicate native attribute identity')
        require(native_id != parent, 'Attribute and parent identities collide')
        ids.add(native_id); handles.add(handle)
        group = groups.setdefault(parent, dict(parent_id=parent, handle=row['parent_handle'], attributes={}, attribute_ids=[]))
        require(group['handle'] == row['parent_handle'] and row['tag'] not in group['attributes'], 'Inconsistent parent or duplicate attribute tag')
        group['attributes'][row['tag']] = row['text']; group['attribute_ids'].append(native_id)
    result = {}; parent_handles = set()
    for group in groups.values():
        attrs = group['attributes']; identity = attrs.get('ICT_ID', '')
        require(isinstance(identity, str) and identity.strip() == identity and identity and attrs.get('TAG'), 'Native asset identity/TAG missing')
        require(identity not in result and group['handle'] not in parent_handles, 'Duplicate native asset identity/handle')
        parent_handles.add(group['handle']); result[identity] = group
    require(result, 'No native profiled assets')
    return result


def verify_inventory(observation, expected):
    groups = group_native(observation)
    require(set(groups) == set(expected), 'Complete native asset set differs')
    for identity, attrs in expected.items():
        require(groups[identity]['attributes'] == attrs, 'Native attributes differ: ' + identity)
    return groups


def verify_selection(observation, group):
    selected = observation['selected']
    require(all(isinstance(i, int) and not isinstance(i, bool) for i in selected), 'Native selected ID type differs')
    actual = [str(i) for i in selected]
    require(len(actual) == len(set(actual)) and set(actual) == {group['parent_id'], *group['attribute_ids']},
            'Selected native asset/children differ')
