# CNC Tool Magazine 0.8.0

Add-on per Home Assistant dedicato alla gestione del magazzino utensili di una fresatrice CNC PentaMac con sistema Visel.

## Funzioni

- 30 posizioni fisse, corrispondenti ai posti fisici del magazzino macchina.
- Campi modificabili per numero utensile `T`, correttore diametro `D` e correttore altezza `H`.
- Descrizione, tipo, numero taglienti, diametro e lunghezza reali dell'utensile.
- Parametri di taglio separati per ogni materiale: Vc, S, Fz, F, ap, ae e refrigerazione.
- Un utensile attivo per posizione, con storico degli utensili sostituiti e possibilità di rimontarli.
- 16 icone realistiche selezionabili per utensili montati e archiviati.
- Popup dei parametri di taglio separato per ogni materiale.
- Calcolo automatico di giri e avanzamento dai dati dell'utensile e del materiale.
- Duplicazione degli utensili e copia dei materiali tra posizioni.
- Ricerca, filtri, esportazione PDF e backup JSON esportabile e ripristinabile.
- Database SQLite persistente incluso nei backup di Home Assistant.
- Interfaccia Ingress accessibile direttamente dal menu laterale.

Questa prima versione gestisce i dati manualmente e non comunica ancora direttamente con il controllo Visel.
