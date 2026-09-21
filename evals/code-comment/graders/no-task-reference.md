---
type: regex
pattern: '#.*(step \d|as requested|per the (ticket|task|spec)|\b[A-Z]{2,10}-\d{2,}\b|updated to|added to)'
flags: im
match: not_contains
---
