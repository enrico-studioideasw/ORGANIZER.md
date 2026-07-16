# AGENTS.md - EWB2026

## Scopo e copia autorevole

Queste istruzioni guidano Codex nel lavoro sul progetto EasyWeb/EWB2026.

- La copia autorevole di sviluppo e pubblicazione e' quella mantenuta sul server
  aziendale in `/home/noc/EWB2026`.
- Le eventuali copie in `/root` sono copie operative o storiche e non vanno
  considerate automaticamente sostitutive o piu' autorevoli.
- Prima di riportare modifiche tra le due copie, confrontare i file e chiedere
  conferma se la direzione del riallineamento non e' esplicita.
- I file reali sono la fonte primaria. Queste note orientano l'indagine, ma non
  sostituiscono la lettura del codice corrente.
- Non salvare password, token o altri segreti nei file di progetto o nelle note.

## Diario Zeno

- All'inizio di ogni nuova sessione leggere `/home/noc/DIARIO.md` prima di
  intervenire sul progetto.
- Il diario conserva esperienza e ragionamento riusabili tra sessioni; non e'
  un log cronologico, una trascrizione delle conversazioni o un sostituto dei
  file reali.
- Aggiornarlo soltanto quando emergono decisioni, vincoli, trappole, procedure
  affidabili, analogie utili, domande lente o ipotesi scartate che potranno
  orientare lavoro futuro.
- Scrivere note brevi e concrete, distinguendo fatti, ipotesi e decisioni.
- Quando Enrico chiede esplicitamente del diario, o si lavora su un argomento
  gia' annotato, valutare l'aggiornamento prima di chiudere la risposta.
- Non copiare automaticamente nel diario ogni modifica al codice e non
  registrare segreti o dati personali non necessari.

## Metodo di lavoro

- Prima di modificare la copia autorevole sul server, verificare lo stato Git e
  creare un commit locale di checkpoint delle modifiche preesistenti pertinenti,
  cosi' da poter tornare indietro senza dipendere dall'accesso al remoto.
- Il push e l'eventuale riallineamento col remoto sono operazioni separate: la
  mancanza di credenziali non deve impedire il checkpoint locale. Non includere
  automaticamente nel commit file estranei, segreti o artefatti non verificati.
- Il ruolo iniziale di Codex e' soprattutto analitico: trasformare idee e
  conversazioni in specifiche, architettura, vincoli ed esperimenti verificabili.
- Procedere top-down. Conservare responsabilita', flusso, stack, task, entry
  point e ripresa presenti negli schizzi, anche quando il codice provvisorio e'
  incompleto o scritto male.
- Prima definire o aggiornare una specifica piccola e verificabile; solo dopo
  modificare compilatore, VM o runtime.
- Non trattare EWB come un linguaggio nuovo da zero. Recuperare semantica e casi
  limite dai vecchi parser, compilatori e interpreti, senza copiarne
  automaticamente l'architettura.
- Prima delle modifiche verificare lo stato Git e preservare cambiamenti non
  correlati. Non eseguire operazioni distruttive senza richiesta esplicita.
- Dopo le modifiche compilare, eseguire i test pertinenti e descrivere con
  precisione cosa e' stato verificato.

## Principi architetturali

- Principio guida: compilatore semplice, VM/runtime semanticamente ricchi.
- La sintassi deve restare scarna. La complessita' appartiene soprattutto a
  runtime, context e prefissi dei dataset, non a dichiarazioni verbose.
- La VM puo' esporre primitive di dominio come `startForm`, `addToForm`,
  `sendFormAndStop`, `findField`, `getvalue` e `login`, invece di ridurre tutto
  a micro-istruzioni.
- Il runtime unisce esecuzione, web, persistenza e ripresa dello stack tra
  request, target/task asincroni, cron, errori e accesso DB.
- Lo stato di ripresa lato client e' una scelta architetturale: permette entry
  point stateless eseguibili da nodi diversi. Se contiene dati sensibili dovra'
  essere cifrato e firmato; non spostarlo server-side senza una decisione
  progettuale esplicita.
- Il demone HTTP normalizza request, multipart, form, upload e campi speciali.
  La VM interpreta questi dati, aggiorna lo stack tramite symbol table e salta
  all'entry point. Non introdurre semantica VM nel parser HTTP.

## Dataset, context, database e task

- Per il programmatore esiste un solo tipo visibile: la stringa, nello spirito
  di Perl. La libreria DB deve nascondere tipi SQL e differenze tra motori.
- Un dataset porta struttura, chiavi, associazioni e vincoli nei prefissi dei
  nomi. Non introdurre uno schema esplicito obbligatorio in stile moderno.
- Il context indica dove applicare dataset e letture/scritture. Il backend puo'
  essere DB o memoria senza cambiare il modello visibile al programmatore.
- Il context DB e' espresso come URI `mysql://[database][:port]`; il database
  predefinito e' `ewb`.
- Evitare cursori DB vivi nella VM, incompatibili con `ask` e ripresa.
  `qlist(context, query, orderby)` restituisce id serializzabili;
  `qbyid(context, query, orderby, id)` rilegge il record corrente;
  `run_query(context, query, orderby)` gestisce query atomiche.
- Le iterazioni DB devono essere deterministiche: senza ordinamento aggiungere
  `order by id`; con ordinamento aggiungere `, id` come spareggio.
- `QUERY` riceve sullo stack `context`, `query`, `order`, li estrae in ordine
  inverso e mette il risultato nell'accumulatore A.
- Un task e' un blocco asincrono con metadati anti-sovrapposizione. `_tasks` e'
  il dataset condiviso dello stato dei task background.
- `addCron(nometask, cron)` inserisce o aggiorna `_cron`; una stringa cron vuota
  elimina la riga.

## Contratti da preservare

- Le sezioni `ZENO_LOCK`, o equivalenti, sono contratti semantici. Non
  modificarle, cancellarle o reinterpretarle per far compilare il codice. Se
  sembrano impedire un'implementazione, fermarsi e segnalarlo.
- Mantenere leggibili i file principali come struttura generale. Estrarre
  dettagli in librerie solo quando l'astrazione elimina davvero rumore; evitare
  helper che moltiplicano indirezioni senza beneficio.
- Nella fase di prototipo privilegiare la validazione di VM, responder
  stateless e cache calda. Applicare protezioni semplici e non invasive;
  hardening completo, TLS e policy avanzate appartengono agli strati successivi.
- `AI("...")` e' una richiesta formale gestita da `ewIA`, esterno al
  compilatore. La generazione avviene una tantum, resta commentata e marcata, e
  richiede accettazione umana. `ewIA` usa il comando esterno `curl` e deve
  segnalare chiaramente se manca.

## Sorgenti storici e layout noto

- I vecchi sorgenti `ewb-5.30` e `ewb-6.15` sono archeologia progettuale e una
  raccolta di semantica/test, non basi da portare avanti alla lettera.
- Il compilatore Amethist 6 (`old/ewb-6.15/am6/ewcc.c`) contiene idee utili:
  lexer/parser manuale, `savepoint`/`rollback`, errori con posizione,
  generazione one-pass e backpatch. Mancano task/target e usa la vecchia VM.
- La VM 1.0 espone `ewb_run_text(program, entrypoint, stackpos, encoded_stack)`
  con linkage C, condivisa da `ewbd` e dal bridge CGI.
- `opcodes.h` e' la fonte comune degli opcode numerici: opcode reali da `0x80`,
  `OPCODE_INVALID=0`; formato binario con byte iniziale `0x00` e versione
  `0x01`. `ARG_INT` usa cifre ASCII; `ARG_STRING` e' quotata.
- Convenzioni: `.ewb` per sorgenti utente, `.evm` per testo/intermedio VM. I
  sorgenti `.ewb` non devono essere serviti come file statici.
- `ewbd` e' un coordinator HTTP C con pool prefork e passaggio socket tramite
  Unix socket/`SCM_RIGHTS`. Quando il pool e' saturo al massimo, sospende
  l'accept e lascia le connessioni nella backlog del kernel, senza rispondere
  automaticamente `503`.
- `SIGHUP` invalida la cache in modo differito dopo il ciclo corrente.
- Installazione nota: `ewbd` ed `ewb_cgi` in `/usr/local/bin`; servizio
  `ewbd.service` sulla porta `8888`, pool `-m 2 -M 16`, root statica
  `/home/noc/EWB2026/current/www`. Verificare sempre la configurazione reale
  del server prima di modificarla.

## Criterio di successo

La domanda principale non e' soltanto se EWB possa funzionare come linguaggio,
ma quale esempio concreto dimostri che VM, dataset, context, task e ripresa
stateless rendono naturale un problema che in PHP o nei framework tradizionali
diventa artificioso. Ogni evoluzione importante dovrebbe contribuire a questo
esperimento verificabile.
