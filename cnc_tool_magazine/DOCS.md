# Installazione e utilizzo

## Installazione

1. In Home Assistant apri **Impostazioni → App → App store**.
2. Apri il menu **⋮ → Repository**.
3. Aggiungi `https://github.com/EdisonACDC/home-assistant-cnc-tool-magazine`.
4. Seleziona **CNC Tool Magazine** e premi **Installa**.
5. Attiva **Avvia all'avvio** e **Mostra nella barra laterale**, quindi avvia l'app.

## Uso

Ogni scheda numerata rappresenta la stessa posizione fisica nel magazzino della fresatrice. Apri una posizione per modificare i dati dell'utensile e i relativi parametri di taglio per uno o più materiali.

I dati vengono salvati in `/data/cnc_tools.db` e sono inclusi nei backup dell'app.

## Sicurezza

L'interfaccia usa Ingress ed è disponibile soltanto agli amministratori di Home Assistant. L'app non richiede accesso privilegiato, alla rete host o alle API di Home Assistant.
