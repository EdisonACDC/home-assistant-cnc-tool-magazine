# Installazione e utilizzo

## Installazione

1. In Home Assistant apri **Impostazioni → App → App store**.
2. Apri il menu **⋮ → Repository**.
3. Aggiungi `https://github.com/EdisonACDC/home-assistant-cnc-tool-magazine`.
4. Seleziona **CNC Tool Magazine** e premi **Installa**.
5. Attiva **Avvia all'avvio** e **Mostra nella barra laterale**, quindi avvia l'app.

## Uso

Ogni scheda numerata rappresenta la stessa posizione fisica nel magazzino della fresatrice. Apri una posizione per modificare i dati dell'utensile e i relativi parametri di taglio per uno o più materiali.

## Ricerca globale

La barra **Cerca in tutto il magazzino**, all'inizio della pagina, controlla contemporaneamente utensili montati, storico, Officina, libreria materiali e nomi dei documenti allegati. Puoi cercare descrizioni, tipi, numeri T/D/H, diametri, note, materiali e parametri di taglio. Ogni risultato indica dove si trova l'elemento, mostra per ogni materiale Vc, S, Fz, F, ap, ae e refrigerazione, e apre direttamente la scheda corrispondente.

Quando scegli una **Icona utensile**, il campo **Tipo utensile** viene compilato automaticamente con il nome dell'icona. La proposta funziona sia nella scheda di una posizione sia durante la creazione in Officina e può essere modificata manualmente prima del salvataggio.

La versione attuale cerca il nome degli allegati, non il testo contenuto all'interno dei PDF o delle fotografie.

## Magazzino CNC virtuale e numero posizioni

La schermata principale mostra il magazzino circolare della macchina. Tocca una posizione per vedere immediatamente icona, descrizione, correttori T/D/H, dimensioni e valori F/S dei materiali; dalla scheda rapida puoi aprire l'utensile oppure montarne uno dall'Officina se la posizione è libera.

Apri **Impostazioni → Numero posizioni** per configurare il magazzino da 1 a 250 posti. Aumentando il numero vengono create nuove posizioni libere. Riducendolo, gli utensili montati e quelli presenti nello storico delle posizioni eliminate vengono trasferiti automaticamente in Officina, conservando correttori, materiali, documenti, icone e dati di utilizzo.

Il magazzino circolare mostra 30 posizioni alla volta. Usa le frecce o il selettore **Gruppo posizioni** per passare, ad esempio, da 1–30 a 31–60, fino a 241–250. La ricerca globale continua a lavorare contemporaneamente su tutte le posizioni.

Usa **Archivia e inserisci nuovo** quando sostituisci l'utensile montato. L'utensile precedente e tutti i suoi parametri di taglio restano nello storico della stessa posizione. Il comando **Monta** riporta uno storico in posizione attiva e archivia automaticamente quello attualmente montato.

## Stato e vita utensile

Scegli lo stato tra **Nuovo**, **In uso**, **Da affilare**, **In manutenzione** e **Fuori servizio**. Imposta le ore già utilizzate e la vita prevista. Con **Avvia** e **Ferma** il timer registra l'utilizzo anche se chiudi la finestra; la percentuale residua viene calcolata automaticamente. Quando raggiunge il limite, lo stato passa a **Da affilare**.

## QR ed etichette

Il pulsante **QR** nella scheda crea l'etichetta dell'utensile montato. **Etichette QR** nella schermata principale prepara gli utensili montati, archiviati e presenti in Officina e permette di mostrare anche tutte le posizioni configurate. Premi **Stampa etichette** per stampare o salvare il foglio in PDF.

Scansionando il QR si apre direttamente la scheda della posizione. Il telefono deve poter raggiungere lo stesso indirizzo di Home Assistant ed essere già autenticato.

## Magazzino Officina e movimenti

Apri **Officina** per registrare gli utensili disponibili ma non montati. Il comando **Svuota posizione → Officina** libera il posto fisico e trasferisce automaticamente l'utensile in Officina senza eliminare dati, parametri o documenti. Con **Monta** scegli una delle posizioni configurate senza ricreare i dati; se è occupata, l'utensile presente viene conservato automaticamente in Officina.

In cima all'Officina trovi **CREA UTENSILE**, che apre il modulo completo per aggiungere un nuovo utensile direttamente al magazzino esterno. Durante la creazione puoi assegnare T, D e H; questi tre valori sono sempre mostrati insieme e in evidenza nelle schede Officina. La barra di ricerca filtra subito l'elenco usando descrizione, tipo di utensile, numeri T/D/H, dimensioni, note e materiali associati.

Selezionando l'icona di un utensile nuovo, l'app seleziona automaticamente tutti i materiali predefiniti compatibili e carica i parametri specifici per quel tipo. Prima di creare l'utensile puoi deselezionare i materiali non necessari e modificare Vc, Fz, ap e ae; S e F vengono calcolati quando sono disponibili diametro, taglienti o passo.

Il comando **Sposta** trasferisce un utensile montato in un'altra posizione libera. La pagina **Movimenti** registra automaticamente creazione, montaggio, smontaggio, spostamento e archiviazione.

Durante gli spostamenti il numero **T** viene aggiornato in base alla nuova posizione fisica. I correttori **D e H** restano invece quelli assegnati all'utensile e vengono conservati anche nel passaggio in Officina e nel successivo rimontaggio.

## Libreria dei materiali

La libreria include modelli iniziali modificabili per C45, acciaio inox, alluminio, ottone, ghisa, rame, titanio e plastica tecnica. Ogni tipo di utensile ha una propria serie di valori proposti per Vc, Fz, ap, ae e refrigerazione. Puoi filtrare la libreria per tipo, modificare i modelli esistenti o crearne di nuovi.

Durante la creazione di un utensile, sia in una posizione macchina sia in Officina, scegli l'icona/tipo e seleziona uno o più materiali predefiniti. I valori proposti restano modificabili prima del salvataggio; quando diametro, taglienti e passo lo consentono, vengono calcolati anche S e F.

In **Officina**, premi **Apri scheda** per visualizzare e modificare tutti i dati dell'utensile, i correttori D/H, lo stato e i materiali. Toccando un materiale si apre il suo popup dedicato con tutti i parametri; da lì puoi entrare direttamente nella modifica, aggiungere altri materiali o eliminarli.

I valori sono soltanto indicativi: devono essere controllati in base a utensile, materiale reale, macchina, serraggio e dati del produttore.

## Documenti e fotografie

Nella scheda dell'utensile usa **Aggiungi file** per allegare PDF, JPG, PNG, WEBP, HEIC o TXT fino a 10 MB. I documenti seguono l'utensile durante gli spostamenti, il passaggio in Officina e l'archiviazione.

Il backup completo dell'add-on di Home Assistant include database e file allegati. L'esportazione JSON contiene i dati strutturati ma non incorpora il contenuto binario dei documenti.

## Calcoli e riutilizzo dei dati

- **Calcola automaticamente** usa diametro, Vc, numero di taglienti e Fz per calcolare giri e avanzamento. Può anche ricavare Vc o Fz quando sono i valori mancanti.
- Se scegli l'icona **Maschio**, **Maschio a rullare** o **Pettine per filetti**, compare il campo obbligatorio **Passo filettatura (mm)**. Per entrambi i tipi di maschio l'app calcola l'avanzamento sincronizzato `F = S × passo`. Per il pettine calcola `F = S × Z × Fz` e usa il passo come avanzamento assiale per ogni giro dell'interpolazione elicoidale.
- **Duplica** copia l'utensile e i suoi materiali in un'altra posizione. Se la destinazione è occupata, il suo utensile viene prima conservato nello storico.
- **Copia materiali** importa i parametri da un'altra posizione e aggiorna quelli con lo stesso nome.

## Svuotamento completo del magazzino

Il pulsante **Svuota tutto il magazzino** trasferisce in Officina tutti gli utensili attualmente montati e libera tutte le posizioni macchina configurate. Prima dell'operazione viene richiesta una conferma. Utensili, correttori D/H, parametri dei materiali, allegati, ore, icone e passo filettatura restano conservati; ogni smontaggio viene registrato nei movimenti.

Per montare rapidamente un utensile, usa **Monta utensile** direttamente su una posizione macchina libera. Si apre l'elenco degli utensili disponibili in Officina: premi **Monta qui** sull'utensile desiderato per inserirlo nella posizione selezionata.

## Esportazione e ripristino

- Il pulsante **GESTISCI FILE** apre una finestra che raccoglie Importa JSON, Esporta JSON, Esporta PDF completo, Etichette QR e Tabella utensili PDF.
- **Esporta PDF** genera un documento A4 completo con tutte le posizioni configurate, gli utensili montati, l'intero archivio e i parametri di taglio per materiale.
- **Tabella generale utensili PDF** apre la configurazione dei colori e permette di scegliere il formato orizzontale A4 o A3. Raccoglie tutti gli utensili montati, presenti in Officina e archiviati, ordinandoli per correttore D e poi H nell'intervallo 1-250. La colonna T indica la posizione soltanto per gli utensili attualmente montati. Per ogni materiale sono riportati soltanto F (mm/min) e S (giri/min); materiali e utensili vengono distribuiti automaticamente su più pagine.
- **Esporta JSON** genera una copia strutturata dei dati per il backup.
- **Importa JSON** ripristina un backup dopo averlo controllato. Prima del ripristino viene sempre salvata automaticamente una copia dello stato corrente in `/data/backups`.

I dati vengono salvati in `/data/cnc_tools.db` e sono inclusi nei backup dell'app.

## Sicurezza

L'interfaccia usa Ingress ed è disponibile soltanto agli amministratori di Home Assistant. L'app non richiede accesso privilegiato, alla rete host o alle API di Home Assistant.

## Controlli automatici

Apri **Controlli** per trovare numeri T duplicati, correttori D o H duplicati e utensili montati senza diametro. I posti liberi vengono ignorati. Toccando una segnalazione si apre direttamente la posizione da correggere.

## Preparazione integrazione Visel

La pagina **Visel** permette di annotare modello del controllo, versione software, host e metodo di collegamento previsto. È una predisposizione in modalità sicura: non apre connessioni e non invia comandi. Per sviluppare lo scambio effettivo serve la documentazione del protocollo Visel oppure un file reale esportato dal controllo, privo di dati sensibili.
