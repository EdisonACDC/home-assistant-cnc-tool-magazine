# Changelog

## 1.2.3

- **Svuota posizione** trasferisce automaticamente l'utensile nel magazzino Officina.
- Durante lo svuotamento non vengono eliminati dati, parametri, documenti, ore o correttori dell'utensile.
- Rimossa dall'interfaccia l'azione duplicata **Metti in Officina**.

## 1.2.2

- I correttori D e H restano associati all'utensile durante ogni spostamento.
- Il passaggio in Officina e il successivo rimontaggio non modificano più D e H.
- Il numero T continua ad aggiornarsi in base alla nuova posizione fisica del magazzino.

## 1.2.1

- I risultati della ricerca mostrano tutti i parametri di taglio dell'utensile trovato.
- Per ogni materiale sono visibili Vc, giri S, Fz, avanzamento F, ap, ae e refrigerazione.
- Indicazione esplicita quando un utensile trovato non ha ancora parametri di taglio.

## 1.2.0

- Barra di ricerca più grande e posizionata all'inizio della pagina.
- Ricerca globale in utensili montati, utensili archiviati, Officina e libreria materiali.
- Ricerca per T, D, H, descrizione, tipo, diametro, note, materiali e parametri di taglio.
- Ricerca nei nomi di PDF, fotografie e altri documenti allegati.
- Risultati classificati per posizione con apertura diretta della relativa scheda.

## 1.1.0

- Controlli automatici per numeri T duplicati, correttori D/H duplicati e diametri mancanti.
- Evidenziazione delle posizioni coinvolte e apertura diretta della scheda dall'elenco delle segnalazioni.
- Nuova sezione preparatoria Visel per salvare modello, versione, host, collegamento previsto e note tecniche.
- Integrazione Visel mantenuta in modalità sicura: nessun comando viene inviato alla macchina senza un protocollo verificato.

## 1.0.0

- Nuovo magazzino **Officina** per utensili disponibili ma non montati nei 30 posti.
- Montaggio diretto dall'Officina; l'eventuale utensile sostituito viene conservato automaticamente in Officina.
- Spostamento diretto di un utensile montato verso un'altra posizione libera.
- Registro automatico degli eventi: creazione, montaggio, smontaggio, spostamento e archiviazione.
- Libreria materiali modificabile con modelli iniziali per C45, inox, alluminio e ottone.
- Applicazione rapida dei valori Vc, Fz, ap, ae e refrigerazione mantenendo tutti i campi modificabili.
- Allegati tecnici per utensile: PDF, immagini, fotografie iPhone e file di testo fino a 10 MB.
- Documenti collegati all'identità dell'utensile e conservati durante spostamenti, archiviazione e passaggio in Officina.
- PDF completo esteso con Officina, libreria materiali, documenti e registro movimenti.
- Backup JSON esteso a Officina, modelli ed eventi; i file allegati restano inclusi nel backup dell'add-on di Home Assistant.

## 0.9.0

- QR generato localmente per ogni posizione e apertura diretta della relativa scheda dal telefono.
- Foglio di etichette QR stampabile per gli utensili montati o per tutti i 30 posti.
- Stati utensile: nuovo, in uso, da affilare, in manutenzione e fuori servizio.
- Timer persistente per registrare le ore di utilizzo con comandi Avvia e Ferma.
- Calcolo automatico della vita residua; al raggiungimento del limite lo stato passa a “Da affilare”.
- Stato, ore e vita residua inclusi nel rapporto PDF e nei backup JSON.
- Compatibilità mantenuta con i backup creati dalle versioni precedenti.

## 0.8.0

- Importazione e ripristino dei backup JSON con validazione e backup automatico dello stato precedente.
- Calcolo automatico di giri, velocità di taglio, avanzamento e avanzamento per dente.
- Duplicazione di un utensile in un'altra posizione, conservando nello storico l'eventuale utensile sostituito.
- Copia e aggiornamento rapido dei parametri materiali tra posizioni.

## 0.7.0

- Aggiunta l'esportazione PDF completa mantenendo disponibile il backup JSON.
- Il PDF contiene la panoramica di tutte le 30 posizioni, compresi gli spazi liberi.
- Per ogni posizione sono inclusi l'utensile montato, tutti gli utensili archiviati e i parametri di taglio per materiale.

## 0.6.0

- Sostituite le 16 icone schematiche con immagini realistiche 3D degli utensili.
- Le immagini trasparenti sono ottimizzate a 256 × 256 pixel per una visualizzazione uniforme.
- Le associazioni già salvate restano valide negli utensili montati, nello storico e nei popup dei materiali.

## 0.5.0

- Aggiunto un selettore con 16 icone dedicate agli utensili da fresatrice.
- L'icona appare sugli utensili montati, nello storico e nel popup del materiale.
- L'icona può essere modificata direttamente anche sugli utensili archiviati.
- L'icona viene conservata durante archiviazione e rimontaggio.

## 0.4.0

- Ogni materiale nella scheda dell'utensile apre il proprio popup separato.
- Aggiunta un'icona dedicata a CNC Tool Magazine nell'add-on e nell'app.

## 0.3.0

- Aggiunto un popup rapido nella scheda di ogni utensile montato.
- Il popup mostra tutti i materiali registrati e i relativi parametri di taglio.
- Visualizzazione completa di Vc, S, Fz, F, ap, ae, refrigerazione e note.

## 0.2.0

- Un utensile attivo per ogni posizione e utensili sostituiti conservati nello storico.
- Comando per archiviare l'utensile montato e inserire quello nuovo.
- Riattivazione di un utensile storico con scambio automatico di quello attivo.
- Conservazione dei parametri di taglio insieme a ogni utensile archiviato.

## 0.1.0

- Prima versione installabile.
- Magazzino fisso da 30 posizioni.
- Gestione T, D, H, descrizione e misure utensile.
- Parametri di taglio modificabili per materiale.
- Ricerca, filtri, riepilogo ed esportazione JSON.
