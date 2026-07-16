# DIARIO

Questo e' il Diario Zeno del progetto EWB2026. Serve a non perdere tra una
sessione e l'altra esperienza, ragionamento e decisioni utili. Non e' un log
cronologico e non sostituisce la lettura del codice, dei test o dello stato
reale del server.

## Come usarlo

- Leggere questo file all'inizio di ogni nuova sessione sul progetto.
- Aggiungere soltanto materiale riusabile: decisioni, vincoli, trappole,
  procedure affidabili, analogie che chiariscono il modello, domande che
  richiedono tempo e ipotesi scartate ma istruttive.
- Preferire note brevi e concrete: contesto, osservazione, conseguenza pratica.
- Distinguere chiaramente fatti verificati, ipotesi e decisioni provvisorie.
- Il codice corrente resta la fonte primaria; una nota vecchia puo' essere
  superata e deve essere corretta quando i fatti cambiano.
- Non trasformare il diario in una lista di commit o in una trascrizione della
  conversazione.
- Non inserire password, token, chiavi, dati personali o dettagli operativi
  sensibili non indispensabili.
- Non cancellare subito un'ipotesi risultata sbagliata se spiega una trappola o
  aiuta a distinguere "impossibile" da "non ancora compreso".

## Laboratorio

Decisioni, vincoli tecnici, problemi, procedure e strade scartate.

### Decisioni

- Il diario conserva esperienza tra sessioni, ma non decide al posto dei file
  reali e delle verifiche correnti.
- La copia di sviluppo principale del progetto resta quella mantenuta da
  Enrico in `/root`; questa installazione e' una copia operativa aggiuntiva.

### Vincoli

- Prima di modificare EWB, leggere anche `/home/noc/AGENTS.md`.
- Non registrare segreti nel diario.

### Trappole

- Un diario troppo narrativo diventa rumore. Conservare cio' che puo' cambiare
  una decisione futura, non tutto cio' che e' accaduto.
- Non assumere che questa copia sia piu' aggiornata della copia di sviluppo:
  verificare la direzione di ogni riallineamento.

### Procedure affidabili

- A fine lavoro chiedersi se e' emerso qualcosa che evitera' un errore o
  abbreviera' un'indagine futura. Se si', annotarlo nella sezione appropriata.

### Domande aperte

- Inserire qui soltanto questioni che richiedono piu' sessioni o che
  condizionano scelte architetturali future.

## Progetti

Conoscenza sedimentata sui singoli sottosistemi EWB: compilatore, VM, `ewbd`,
dataset/context, task/cron, database ed `ewIA`.

## Pausa caffe'

Analogie e intuizioni laterali che aiutano a vedere il progetto da un punto di
vista diverso, senza confonderle con requisiti gia' decisi.
