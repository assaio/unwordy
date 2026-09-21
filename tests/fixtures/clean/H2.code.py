def parse(payload):
    # The upstream API sends an empty body instead of a 404.
    if not payload:
        return None
    return payload.get("data")
