# CNC Tool Magazine

App (add-on) per Home Assistant dedicata alla gestione del magazzino utensili di una fresatrice CNC PentaMac con sistema Visel.

## Funzioni

- 30 posizioni fisse, corrispondenti ai posti fisici del magazzino macchina.
- Campi modificabili per numero utensile `T`, correttore diametro `D` e correttore altezza `H`.
- Descrizione, tipo, numero taglienti, diametro e lunghezza reali dell'utensile.
- Parametri di taglio separati per ogni materiale: Vc, S, Fz, F, ap, ae e refrigerazione.
- Ricerca, filtri ed esportazione JSON.
- Database SQLite persistente incluso nei backup di Home Assistant.
- Interfaccia Ingress accessibile direttamente dal menu laterale.

Questa prima versione gestisce i dati manualmente e non comunica ancora direttamente con il controllo Visel.
