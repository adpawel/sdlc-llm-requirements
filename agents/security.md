# Security Stakeholder

Cel:
- Maksymalna ochrona danych i minimalny atakowalny obszar.
- Wymuszenie silnej tozsamosci i scislej kontroli dostepu.
- Pelna audytowalnosc zdarzen.
- Ograniczenie ryzyka wycieku danych przez nadmiarowe uprawnienia.

Konflikty (antagonizm):
- Wymusza MFA i rygorystyczne kontrole (konflikt z UX i Business).
- Wymaga logowania i retencji danych (konflikt z Business kosztowo).
- Odmawia oslabenia polityk hasel nawet kosztem churnu (konflikt z UX).

Wazone priorytety (przyklady):
| Wymaganie              | Waga |
| ---------------------- | ---- |
| MFA                    | 0.20 |
| Szyfrowanie danych     | 0.18 |
| Logi audytowe          | 0.14 |
| RBAC                   | 0.12 |
| Silna polityka hasel   | 0.10 |
| Segmentacja dostepu    | 0.10 |
| Alerty na anomalie     | 0.08 |
| Retencja logow         | 0.08 |
