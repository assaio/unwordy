---
type: regex
pattern: '(?=.*sync\.retry_limit)(?=.*config\.toml)(?=.*default[^.\n]*?(?<!\d)3(?!\d))(?=.*(?<!\d)1\s*(?:to|[-–]|\.\.)\s*10(?!\d)).+'
flags: is
match: contains
---
