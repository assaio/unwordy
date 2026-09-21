def sync(items, sink):
    seen = set()
    # loop over the incoming items
    for item in items:
        # skip anything empty
        if not item:
            continue
        # push it downstream
        sink.send(item)
        # remember what went out
        seen.add(item.id)
    # hand back the ids
    return seen
