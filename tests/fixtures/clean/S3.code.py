def sync(items, sink):
    seen = set()
    for item in items:
        if not item:
            continue
        # The sink drops duplicates silently, so ids are tracked here.
        sink.send(item)
        seen.add(item.id)
    return seen
