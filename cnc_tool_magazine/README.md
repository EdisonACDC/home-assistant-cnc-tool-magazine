# CNC Tool Magazine 1.7.1

Add-on per Home Assistant dedicato alla gestione del magazzino utensili di una fresatrice CNC PentaMac con sistema Visel.

## Funzioni

- Da 1 a 250 posizioni configurabili, corrispondenti ai posti fisici del magazzino macchina.
- Visualizzazione circolare a gruppi da 30, mantenendo sempre leggibile la numerazione reale.
- Nuova interfaccia CNC virtuale responsive con carosello delle posizioni e scheda rapida dell'utensile selezionato.
- Riduzione sicura del numero di posizioni con trasferimento automatico in Officina degli utensili e dello storico rimossi dalla macchina.
- Campi modificabili per numero utensile `T`, correttore diametro `D` e correttore altezza `H`.
- Descrizione, tipo, numero taglienti, diametro e lunghezza reali dell'utensile.
- Parametri di taglio separati per ogni materiale: Vc, S, Fz, F, ap, ae e refrigerazione.
- Un utensile attivo per posizione, con storico degli utensili sostituiti e possibilità di rimontarli.
- 18 tipi di utensile selezionabili con icone realistiche, compresi maschio a rullare e pettine per filetti.
- Passo filettatura dedicato per maschi, maschi a rullare e pettini, conservato in Officina e nello storico.
- Esportazione **Tabella generale PDF** A4 o A3 con tutti gli utensili, icone, correttori D/H 1-250 e parametri F/S.
- Menu **GESTISCI FILE** che raccoglie backup JSON, PDF, tabella utensili ed etichette QR.
- Colori personalizzabili e persistenti per ogni tipo di utensile.
- Popup dei parametri di taglio separato per ogni materiale.
- Calcolo automatico di giri e avanzamento dai dati dell'utensile e del materiale.
- Duplicazione degli utensili e copia dei materiali tra posizioni.
- Stato, timer di utilizzo e calcolo automatico della vita residua.
- QR per aprire direttamente ogni posizione e foglio di etichette stampabile.
- Magazzino Officina per utensili non montati, con montaggio e spostamento rapido.
- Correttori D/H visibili e assegnabili nelle schede Officina; nelle posizioni macchina libere il pulsante **Monta utensile** apre direttamente la scelta degli utensili disponibili.
- Svuotamento completo del magazzino macchina con trasferimento sicuro di tutti gli utensili in Officina.
- Registro automatico di montaggi, smontaggi, spostamenti e archiviazioni.
- Libreria modificabile con otto materiali predefiniti e valori di taglio specifici per ogni tipo di utensile.
- Materiali selezionabili e modificabili già durante la creazione di un utensile in macchina o in Officina.
- Scheda completa per ogni utensile in Officina, con popup e modifica dei singoli materiali.
- Pulsante **CREA UTENSILE** e barra di ricerca interna all'Officina per utensili, correttori e materiali.
- Schede tecniche, PDF e fotografie allegabili a ogni utensile.
- Ricerca globale tra utensili montati, storico, Officina, materiali e documenti.
- Ricerca, filtri, esportazione PDF e backup JSON esportabile e ripristinabile.
- Database SQLite persistente incluso nei backup di Home Assistant.
- Interfaccia Ingress accessibile direttamente dal menu laterale.

La sezione **Visel** conserva modello, versione, host e metodo di collegamento previsto. Rimane intenzionalmente in modalità sicura e non comunica con il controllo macchina finché non viene verificato il protocollo o un file di scambio ufficiale.
