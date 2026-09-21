# Collaudo minimo

## Preparazione

- Verificare che tutte le richieste già presenti abbiano `shared_mode = 0`.
- Verificare sintassi di Python, PHP e JavaScript.
- Avviare prima una sola console laboratorio.

## Due interlocutori

1. Entrare nel laboratorio con il primo account autorizzato.
2. Entrare da un secondo browser con un altro account autorizzato.
3. Verificare che entrambi leggano `Zeno sta parlando anche con ...`.
4. Inviare due domande non correlate quasi contemporaneamente.
5. Verificare elaborazione seriale e consegna della risposta alla sola
   trascrizione dell'autore.
6. Creare segnalibri con entrambi gli account e controllare che non siano
   visibili né copiabili dall'altro.

## Limite e compatibilità

1. Tentare un terzo account: l'apertura deve rispondere HTTP 409.
2. Aprire due schede dello stesso account: devono restare ammesse.
3. Dalla console stabile inviare una richiesta mentre un diverso attore ne è
   proprietario: deve restare valida la vecchia esclusività.
4. Chiudere uno dei due utenti e attendere l'aggiornamento presenza; un nuovo
   secondo utente deve poter entrare.

## Conflitto deliberato

Far chiedere ai due utenti modifiche incompatibili allo stesso file. L'agente
deve fermarsi e dichiarare il conflitto: il prototipo non applica merge o
precedenze automatiche.

## Rollback

1. Ripristinare demone e worker dai backup.
2. Riavviare i relativi servizi.
3. Rimuovere o disabilitare l'URL laboratorio.
4. La colonna `shared_mode` può restare: con default zero è inerte. Rimuoverla
   soltanto dopo aver verificato che nessun codice la interroghi più.
