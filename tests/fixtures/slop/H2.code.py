def parse(payload):
    # Step 1: validate the payload
    if not payload:
        return None
    # per the ticket PROJ-142 this stays backwards compatible
    return payload.get("data")
