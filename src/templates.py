"""Deutsche E-Mail-Vorlagen für die Baumkontrolle-Erinnerungen."""

ERINNERUNG_1_SUBJECT = "Erinnerung: Baumkontrolle {ort} – Termin für erneute Kontrolle"

ERINNERUNG_1_BODY = """Guten Tag {anrede_name},

am {letzte_kontrolle} fand die letzte Baumkontrolle bzw. das letzte Gutachten \
für den Standort {ort} statt. Laut unseren Unterlagen ist eine erneute \
Kontrolle mittlerweile fällig.

Wünschen Sie, dass wir eine erneute Baumkontrolle für Sie einplanen?

Wir freuen uns über eine kurze Rückmeldung.

Mit freundlichen Grüßen
"""

INTERNAL_NOTE = """⚠️ INTERNER HINWEIS – vor dem Senden bitte prüfen und diesen \
Absatz löschen:
Hat sich der Kunde eventuell bereits auf anderem Wege gemeldet (Telefon, \
persönlich, etc.)? Falls ja, bitte NICHT senden, sondern den Status direkt \
in der Tabelle nachtragen.

---

"""

WERKVERTRAG_HINWEIS = """⚠️ INTERNER HINWEIS – vor dem Senden bitte prüfen und diesen \
Absatz löschen:
In der Spalte "Werkvertrag" steht für diesen Kunden folgender Eintrag: \
"{werkvertrag}"
Bitte prüfen, ob trotz dieses Eintrags eine Erinnerung gewünscht ist.

---

"""

ERINNERUNG_2_SUBJECT = "Erinnerung (2): Baumkontrolle {ort} – Rückmeldung ausstehend"

ERINNERUNG_2_BODY = """Guten Tag {anrede_name},

vor einiger Zeit hatten wir Sie bezüglich einer erneuten Baumkontrolle bzw. \
Gutachten am Standort {ort} kontaktiert. Bislang haben wir noch keine \
Rückmeldung von Ihnen erhalten.

Wünschen Sie weiterhin eine erneute Kontrolle? Wir freuen uns über eine \
kurze Rückmeldung.

Mit freundlichen Grüßen
"""

MISSING_EMAIL_SUBJECT = "AKTION NÖTIG: E-Mail-Adresse fehlt – {ort} ({name})"

MISSING_EMAIL_BODY = """Für folgenden Eintrag ist eine Erinnerung fällig, es fehlt aber eine \
E-Mail-Adresse in der Tabelle:

Kunde: {vorname} {name}
Ort: {ort}
Projekt/Nr.: {projekt_nr}

Bitte die E-Mail-Adresse in der Spalte "E-Mail" (Kontakt des Kunden) \
ergänzen. Beim nächsten automatischen Lauf wird die Erinnerung dann \
verschickt.
"""
