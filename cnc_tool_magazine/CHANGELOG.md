# Changelog

## 1.7.2

- Corretto il pulsante **CREA UTENSILE** che in alcune finestre Home Assistant non rendeva visibile il modulo.
- Il modulo ora usa uno stato di apertura esplicito e viene portato automaticamente nella parte visibile della finestra.
- Abilitato lo scorrimento interno di tutte le finestre su schermi bassi, telefono e pannelli Home Assistant incorporati.

## 1.7.1

- Aggiunto in Officina il pulsante evidente **CREA UTENSILE**, che apre su richiesta il modulo di creazione.
- Aggiunta una barra di ricerca dedicata all'Officina.
- La ricerca controlla descrizione, tipo, icona, correttori D/H, dimensioni, passo, taglienti, note e materiali.
- Aggiunti conteggio dei risultati, cancellazione rapida della ricerca e messaggi per elenco vuoto o nessuna corrispondenza.
- Aggiunto il numero T nella creazione e nella scheda completa degli utensili in Officina.
- Evidenziati sempre insieme i valori T, D e H nelle schede e nella scelta di montaggio dall'Officina.
- Selezionando l'icona durante la creazione, tutti i materiali compatibili e i relativi parametri vengono inseriti automaticamente; i valori restano modificabili prima del salvataggio.

## 1.7.0

- Aggiunti otto materiali predefiniti: C45, inox, alluminio, ottone, ghisa, rame, titanio e plastica tecnica.
- Creati parametri di taglio predefiniti specifici e modificabili per tutti i tipi di utensile disponibili.
- Aggiunta la selezione dei materiali, con modifica di Vc, Fz, ap e ae, durante la creazione degli utensili in macchina e in Officina.
- Aggiunta la scheda completa degli utensili in Officina con modifica dei dati, correttori, stato e materiali.
- Resi apribili i materiali direttamente dalle schede Officina, con popup separato e accesso alla modifica.
- Aggiunta una migrazione automatica che conserva i modelli materiali personalizzati dei database precedenti.

## 1.6.0

- Esteso il magazzino macchina fino a 250 posizioni reali.
- Aggiunta navigazione del cerchio in gruppi da 30 con selettore e frecce avanti/indietro.
- Mantenuta la numerazione fisica reale T1–T250 in tutte le schede e operazioni.
- Ricerca e collegamenti QR aprono automaticamente il gruppo contenente la posizione trovata.
- Aggiornati importazione/esportazione, PDF, controlli, montaggio, spostamento e svuotamento per 250 posizioni.
- Migrazione automatica dei database precedenti con limite di 30 o 60 posizioni.

## 1.5.0

- Nuova grafica ispirata a un pannello CNC virtuale, ottimizzata per telefono e tablet.
- Magazzino circolare interattivo con stato delle posizioni, segnalazioni e utensile selezionato.
- Scheda rapida con icona, correttori T/D/H, dimensioni e parametri F/S per materiale.
- Nuova impostazione **Numero posizioni** configurabile da 1 a 60.
- Le posizioni aggiunte vengono create automaticamente con i relativi numeri T/D/H iniziali.
- Riducendo il magazzino, utensili montati e storico delle posizioni eliminate vengono trasferiti in Officina senza perdere dati o allegati.
- Backup JSON, importazione, PDF, QR, montaggio, spostamento e svuotamento ora rispettano il numero configurato.

## 1.4.3

- Nuovo pulsante **GESTISCI FILE** che apre una finestra dedicata.
- Raggruppati Importa JSON, Esporta JSON, Esporta PDF, Etichette QR e Tabella utensili PDF.
- Rimossi questi cinque pulsanti dalla testata principale per rendere la pagina più ordinata su telefono.
- Aggiunti i campi correttore D e H durante la creazione di un utensile in Officina.
- I correttori D/H sono ora visibili direttamente in ogni scheda Officina.
- Nelle posizioni macchina libere compare il nuovo pulsante **Monta utensile**.
- Il pulsante apre direttamente la scelta degli utensili disponibili in Officina e li monta nella posizione selezionata, senza entrare prima nella sezione Officina.

## 1.4.2

- Nuovo pulsante **Svuota tutto il magazzino** con conferma obbligatoria.
- Tutti gli utensili montati vengono trasferiti in un'unica operazione atomica nel magazzino Officina.
- Vengono conservati correttori D/H, materiali, documenti, icone, passo filettatura, stato e ore di utilizzo.
- Le 30 posizioni macchina vengono ripristinate come libere senza eliminare utensili.
- Ogni smontaggio viene registrato automaticamente nei movimenti.

## 1.4.1

- Aggiunto **Maschio a rullare** come tipo utensile selezionabile con icona realistica dedicata.
- Il tipo utensile viene compilato automaticamente dalla nuova icona.
- Il passo filettatura è obbligatorio e viene conservato durante spostamenti, Officina, archivio ed esportazioni.
- L'avanzamento viene calcolato automaticamente con la formula sincronizzata `F = S × passo`.
- Aggiunto un colore personalizzabile separato per il maschio a rullare nella tabella macchina PDF.
- La tabella generale raccoglie tutti gli utensili montati, in Officina e nello storico, ordinandoli per correttori D/H da 1 a 250.
- Aggiunta la scelta del formato di stampa orizzontale **A4** o **A3**.

## 1.4.0

- Nuova esportazione **Tabella macchina PDF** in formato A4 orizzontale.
- La tabella contiene sempre le righe T1-T30, corrispondenti ai posti fisici della macchina.
- Per ogni posto mostra icona, correttore D, correttore H e descrizione dell'utensile montato.
- I materiali vengono raccolti automaticamente da tutti gli utensili montati e mostrano soltanto avanzamento F e giri S.
- Quando i materiali superano lo spazio disponibile vengono distribuiti su più pagine leggibili.
- Nuova configurazione persistente del colore per ciascun tipo/icona utensile.
- I colori personalizzati sono inclusi anche nelle esportazioni e nei ripristini JSON.

## 1.3.0

- Nuovo campo **Passo filettatura (mm)**, mostrato automaticamente per Maschio e Pettine per filetti.
- Aggiunto **Pettine per filetti** all'elenco degli utensili selezionabili.
- Per i maschi l'avanzamento viene calcolato con la formula sincronizzata `F = S × passo`.
- Per i pettini l'avanzamento di taglio resta `F = S × Z × Fz` e il passo indica l'avanzamento assiale per giro dell'interpolazione elicoidale.
- Il passo viene conservato durante spostamenti, archiviazione, Officina, duplicazione, esportazione e ripristino.
- Il passo compare nelle schede, nella ricerca globale e nel PDF.

## 1.2.4

- La scelta dell'icona compila automaticamente il campo **Tipo utensile** con il nome corrispondente.
- La compilazione automatica funziona sia per gli utensili montati sia durante la creazione in Officina.
- Il tipo proposto resta modificabile manualmente prima del salvataggio.

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
