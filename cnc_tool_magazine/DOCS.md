# Installazione e utilizzo

## Installazione

1. In Home Assistant apri **Impostazioni → App → App store**.
2. Apri il menu **⋮ → Repository**.
3. Aggiungi `https://github.com/EdisonACDC/home-assistant-cnc-tool-magazine`.
4. Seleziona **CNC Tool Magazine** e premi **Installa**.
5. Attiva **Avvia all'avvio** e **Mostra nella barra laterale**, quindi avvia l'app.

## Uso

Ogni scheda numerata rappresenta la stessa posizione fisica nel magazzino della fresatrice. Apri una posizione per modificare i dati dell'utensile e i relativi parametri di taglio per uno o più materiali.

Usa **Archivia e inserisci nuovo** quando sostituisci l'utensile montato. L'utensile precedente e tutti i suoi parametri di taglio restano nello storico della stessa posizione. Il comando **Monta** riporta uno storico in posizione attiva e archivia automaticamente quello attualmente montato.

## Stato e vita utensile

Scegli lo stato tra **Nuovo**, **In uso**, **Da affilare**, **In manutenzione** e **Fuori servizio**. Imposta le ore già utilizzate e la vita prevista. Con **Avvia** e **Ferma** il timer registra l'utilizzo anche se chiudi la finestra; la percentuale residua viene calcolata automaticamente. Quando raggiunge il limite, lo stato passa a **Da affilare**.

## QR ed etichette

Il pulsante **QR** nella scheda crea l'etichetta dell'utensile montato. **Etichette QR** nella schermata principale prepara gli utensili montati e archiviati e permette di mostrare anche tutti i 30 posti. Premi **Stampa etichette** per stampare o salvare il foglio in PDF.

Scansionando il QR si apre direttamente la scheda della posizione. Il telefono deve poter raggiungere lo stesso indirizzo di Home Assistant ed essere già autenticato.

## Calcoli e riutilizzo dei dati

- **Calcola automaticamente** usa diametro, Vc, numero di taglienti e Fz per calcolare giri e avanzamento. Può anche ricavare Vc o Fz quando sono i valori mancanti.
- **Duplica** copia l'utensile e i suoi materiali in un'altra posizione. Se la destinazione è occupata, il suo utensile viene prima conservato nello storico.
- **Copia materiali** importa i parametri da un'altra posizione e aggiorna quelli con lo stesso nome.

## Esportazione e ripristino

- **Esporta PDF** genera un documento A4 completo con tutte le 30 posizioni, gli utensili montati, l'intero archivio e i parametri di taglio per materiale.
- **Esporta JSON** genera una copia strutturata dei dati per il backup.
- **Importa JSON** ripristina un backup dopo averlo controllato. Prima del ripristino viene sempre salvata automaticamente una copia dello stato corrente in `/data/backups`.

I dati vengono salvati in `/data/cnc_tools.db` e sono inclusi nei backup dell'app.

## Sicurezza

L'interfaccia usa Ingress ed è disponibile soltanto agli amministratori di Home Assistant. L'app non richiede accesso privilegiato, alla rete host o alle API di Home Assistant.
