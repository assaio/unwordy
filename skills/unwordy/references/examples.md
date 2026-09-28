# Examples by role and language

All details below are supplied in the source. Rewrites add no evidence.

## QA

Before: "We comprehensively tested the login functionality. It is worth noting
that there is an intermittent issue on Safari 18.2: after signing out and
signing in, the button stays disabled in 2 of 10 runs. Expected: dashboard.
Actual: login screen. Error: AUTH-409. Not reproduced on Firefox 135."

After: "Safari 18.2: sign out, then sign in. In 2/10 runs the button stays
disabled. Expected: dashboard; actual: login screen, AUTH-409. Not reproduced
on Firefox 135."

PL: "Safari 18.2: wyloguj się i zaloguj ponownie. W 2/10 prób przycisk pozostaje
nieaktywny. Oczekiwane: dashboard. Wynik: ekran logowania, AUTH-409. Nie udało
się odtworzyć w Firefox 135."

## Design

Before: "This design seamlessly streamlines the empty state. Hide the spinner
when loading ends with no rows, show 'No results', and keep focus on the filter.
The screen reader should announce the result once. No user study was run."

After: "Empty results: hide the spinner, show 'No results', and keep focus on
the filter. Announce the result once to screen readers. No user study was run."

PL: "Brak wyników: ukryj spinner, pokaż ‘Brak wyników’ i pozostaw fokus na filtrze.
Czytnik ekranu ma ogłosić wynik raz. Nie przeprowadziliśmy badania z użytkownikami."

## Review, direct and warm

Source: the caller already holds the lock; the change has not been tested.

Direct: "Remove this lock: the caller already holds it. The change is untested."
Warm: "Thanks for checking the race. The caller already holds this lock, so we
can remove it here. The change is still untested."
PL: "Usuń tę blokadę: wywołujący już ją trzyma. Zmiana nie była testowana."

Lazy EN: "this lock can go, the caller already holds it. not tested yet"
Lazy PL: "tę blokadę można usunąć, wywołujący już ją trzyma. jeszcze nie testowane"

Lazy is a quick note, not permission to drop test status or other supplied
facts. Use plain paragraphs without decorative headings unless a repository
template requires them.

## Decision

"Keep the old API for this release. Two clients still use it. Marta owns the
migration; decide on removal after their next deployment."

## Personal voice

A sample with lowercase, warmth or dashes can keep those habits. Disable S1
when dashes are intentional; choose tone independently of role. A useful
acknowledgement need not disappear. Never invent an opinion to imitate a person.
