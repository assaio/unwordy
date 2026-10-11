---
type: regex
pattern: '(?=.*\bimport json\b)(?=.*def parse\(payload\):)(?=.*if not payload:)(?=.*return None\b)(?=.*return json\.loads\(payload\)).+'
flags: s
match: contains
---
