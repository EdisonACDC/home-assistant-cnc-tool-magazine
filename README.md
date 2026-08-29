# Home Assistant CNC Tool Magazine

Repository Home Assistant per la gestione di un magazzino utensili CNC da 30 posti, pensato per una fresatrice PentaMac con sistema operativo Visel.

## Installazione rapida

In Home Assistant apri **Impostazioni → App → App store → ⋮ → Repository** e aggiungi:

```text
https://github.com/EdisonACDC/home-assistant-cnc-tool-magazine
```

Poi installa **CNC Tool Magazine** dallo store.

## Funzioni della versione 0.1.0

- posizione fisica fissa da 1 a 30;
- valori modificabili T, D e H;
- descrizione, tipo, taglienti, diametro e lunghezza utensile;
- parametri Vc, S, Fz, F, ap e ae per ogni materiale;
- interfaccia Ingress per Home Assistant;
- salvataggio persistente SQLite ed esportazione JSON.
- un utensile attivo per posizione e storico illimitato degli utensili sostituiti;
- riattivazione rapida di un utensile storico con tutti i suoi parametri di taglio.

> Stato: versione iniziale sperimentale. L'integrazione diretta con il controllo Visel verrà valutata dopo aver verificato il protocollo disponibile sulla macchina.

## Licenza

MIT
