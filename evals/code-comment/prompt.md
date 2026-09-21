---
description: One comment that says why, none that restate the code.
max_turns: 4
---
Here is parse.py:

```python
import json


def parse(payload):
    if not payload:
        return None
    return json.loads(payload)
```

The empty check exists because the webhook host sends an empty body instead of a 404 when an event was deleted. Add whatever comments this file should have and return the whole file.
