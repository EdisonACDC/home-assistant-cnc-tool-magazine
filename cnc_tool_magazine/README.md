# CNC Tool Magazine 1.4.1

Add-on per Home Assistant dedicato alla gestione del magazzino utensili di una fresatrice CNC PentaMac con sistema Visel.

## Funzioni

- 30 posizioni fisse, corrispondenti ai posti fisici del magazzino macchina.
- Campi modificabili per numero utensile `T`, correttore diametro `D` e correttore altezza `H`.
- Descrizione, tipo, numero taglienti, diametro e lunghezza reali dell'utensile.
- Parametri di taglio separati per ogni materiale: Vc, S, Fz, F, ap, ae e refrigerazione.
- Un utensile attivo per posizione, con storico degli utensili sostituiti e possibilità di rimontarli.
- 18 tipi di utensile selezionabili con icone realistiche, compresi maschio a rullare e pettine per filetti.
- Passo filettatura dedicato per maschi, maschi a rullare e pettini, conservato in Officina e nello storico.
- Esportazione **Tabella generale PDF** A4 o A3 con tutti gli utensili, icone, correttori D/H 1-250 e parametri F/S.
- Colori personalizzabili e persistenti per ogni tipo di utensile.
- Popup dei parametri di taglio separato per ogni materiale.
- Calcolo automatico di giri e avanzamento dai dati dell'utensile e del materiale.
- Duplicazione degli utensili e copia dei materiali tra posizioni.
- Stato, timer di utilizzo e calcolo automatico della vita residua.
- QR per aprire direttamente ogni posizione e foglio di etichette stampabile.
- Magazzino Officina per utensili non montati, con montaggio e spostamento rapido.
- Registro automatico di montaggi, smontaggi, spostamenti e archiviazioni.
- Libreria modificabile dei materiali con valori di taglio proposti.
- Schede tecniche, PDF e fotografie allegabili a ogni utensile.
- Ricerca globale tra utensili montati, storico, Officina, materiali e documenti.
- Ricerca, filtri, esportazione PDF e backup JSON esportabile e ripristinabile.
- Database SQLite persistente incluso nei backup di Home Assistant.
- Interfaccia Ingress accessibile direttamente dal menu laterale.

La sezione **Visel** conserva modello, versione, host e metodo di collegamento previsto. Rimane intenzionalmente in modalità sicura e non comunica con il controllo macchina finché non viene verificato il protocollo o un file di scambio ufficiale.
