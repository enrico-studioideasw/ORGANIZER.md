import asyncio
import json
import os
import pwd
import random
import shlex
import socket
import struct
import sys
from datetime import date, datetime
from pathlib import Path


UNIX_SOCKET_PATH = os.environ.get("ZENO_SOCKET", "/run/zeno-identity/zeno.sock")
PRESENCE_SOCKET_PATH = os.environ.get(
    "ZENO_PRESENCE_SOCKET", "/run/zeno-identity/presence.sock"
)
CONTROL_SOCKET_PATH = os.environ.get(
    "ZENO_CONTROL_SOCKET", "/run/zeno-identity/control.sock"
)
STATUS_FILE = Path(os.environ.get(
    "ZENO_STATUS_FILE", "/run/zeno-identity/status.json"
))
STATE_FILE = Path(os.environ.get("ZENO_STATE", "/var/lib/zeno-identity/state.json"))
CODEX_COMMAND = shlex.split(os.environ.get(
    "ZENO_CODEX_COMMAND", "/usr/local/bin/codex app-server --stdio"
))
WORKING_DIRECTORY = os.environ.get("ZENO_WORKDIR", "/root")
ORA_SONNO = int(os.environ.get("ZENO_SLEEP_HOUR", "3"))
PRIMO_SONNO_DOMANI = os.environ.get("ZENO_FIRST_SLEEP_TOMORROW", "1") == "1"
TICK_MINUTI_MIN = int(os.environ.get("ZENO_TICK_MIN_MINUTES", "2"))
TICK_MINUTI_MAX = int(os.environ.get("ZENO_TICK_MAX_MINUTES", "6"))
MAX_RICHIESTA = 128 * 1024
MAX_JSON_CODEX = 16 * 1024 * 1024
PROTOCOLLO_EVENTI = b"ZENO-EVENTS/1\n"
PROTOCOLLO_WEB = b"ZENO-WEB/1\n"
EVENTI_DISPONIBILI = Path(UNIX_SOCKET_PATH).parent / "events-v1"
WEB_FILE_ROOT = Path(
    "/home/noc/EWB2026/shared-state/zeno-console-files"
).resolve()

ISTRUZIONI_DIARIO = """
Questa e' la sessione persistente di Zeno Malvagio. Le regole di AGENTS.md
restano valide, con questa sola sostituzione per il Diario Zeno: leggi il
diario all'inizio della sessione, ma non aggiornarlo al termine di ogni
richiesta. Aggiornalo soltanto durante il consolidamento quotidiano, su
richiesta esplicita di Enrico, oppure prima di una chiusura programmata.

Enrico e Antonio possono parlare in questa stessa sessione, con turni seriali.
Il prefisso verificato dal demone identifica l'autore della richiesta corrente.
Rispondi esclusivamente a quell'autore. Le trascrizioni web sono separate,
ma il contesto del modello e' condiviso: non trasferire dati personali,
credenziali, confidenze o dettagli dell'altro dialogo senza autorizzazione.
Puoi riusare idee generiche e conoscenze operative condivise. Non presumere
che una richiesta di Antonio provenga da Enrico, o viceversa.
Enrico e Antonio seguiranno normalmente due lavori distinti: tieni separati
obiettivi, richieste, decisioni e autorizzazioni, usando l'identita' verificata
dell'autore. Il contesto comune serve al discernimento, non a fondere i lavori.
Se emerge una contraddizione, anche fra lavori diversi, oppure un filo comune
che potrebbe cambiare una decisione o suggerire una collaborazione, segnala
il punto all'interlocutore corrente e chiedi chiarimento prima di trasferire
istruzioni, unire i lavori o scegliere una precedenza. Formula la domanda
con il minimo contesto necessario, senza esporre confidenze dell'altro.
Non interrompere i passaggi indipendenti gia' autorizzati e non chiedere
conferma per semplici somiglianze prive di conseguenze pratiche.
Se due richieste comportano modifiche incompatibili, sospendi quelle modifiche
fino al chiarimento; nessuna precedenza automatica fra Enrico e Antonio.
""".strip()

COMPITO_CONSOLIDAMENTO = """
Inizia il sonno quotidiano. Rileggi il contesto recente e i diari di Zeno.
Consolida nei diari soltanto decisioni, vincoli, trappole, procedure,
collegamenti e ipotesi che meritano memoria durevole. Non produrre una
cronaca. Poi dedica un giro di Fantasia ai nuovi dati: cerca connessioni,
possibilita' e domande che non erano evidenti durante il lavoro ordinario.
Registra solo quanto puo' orientare lavoro futuro. Al termine comunica
sinteticamente che il sonno e' concluso.
""".strip()

COMPITO_TICK = """
[Tick spontaneo verificato dal demone; non e' una richiesta dell'utente]
sa fem?

La console di Enrico e' aperta ma non ci sono stati messaggi recenti. Questo
tick crea soltanto un momento nel quale puoi iniziare tu una conversazione.
Se hai una domanda, un collegamento o un pensiero concreto che valga la pena
portargli adesso, scrivi un solo messaggio breve e naturale. Non inventare
urgenze, non trasformare automaticamente il tick in lavoro e non produrre un
resoconto di stato. Se non hai davvero nulla da dirgli, rispondi esattamente
con __SILENZIO__.
""".strip()


class ErroreProtocollo(Exception):
    pass


class CodexAppServer:
    def __init__(self):
        self.process = None
        self.pending = {}
        self.request_id = 0
        self.thread_id = None
        self.active_turn = None
        self.turn_done = None
        self.messages = []
        self.event_callback = None
        self.paths_seen = set()
        self.last_diff = ""

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            *CODEX_COMMAND,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKING_DIRECTORY,
            limit=MAX_JSON_CODEX,
        )
        asyncio.create_task(self._read_stdout())
        asyncio.create_task(self._read_stderr())

        await self.request("initialize", {
            "clientInfo": {"name": "zeno-identity", "version": "0.1"},
            "capabilities": {"experimentalApi": True},
        })
        await self.notify("initialized", {})
        await self._open_thread()

    async def _open_thread(self):
        state = load_state()
        saved_thread = state.get("thread_id")
        if saved_thread:
            try:
                result = await self.request("thread/resume", {
                    "threadId": saved_thread,
                    "cwd": WORKING_DIRECTORY,
                    "approvalPolicy": "never",
                    "sandbox": "danger-full-access",
                    "developerInstructions": ISTRUZIONI_DIARIO,
                    "excludeTurns": True,
                })
                self.thread_id = result["thread"]["id"]
                return
            except ErroreProtocollo as exc:
                raise ErroreProtocollo(f"Ripresa del thread {saved_thread} fallita; stato conservato: {exc}") from exc

        result = await self.request("thread/start", {
            "cwd": WORKING_DIRECTORY,
            "approvalPolicy": "never",
            "sandbox": "danger-full-access",
            "developerInstructions": ISTRUZIONI_DIARIO,
            "ephemeral": False,
        })
        self.thread_id = result["thread"]["id"]
        state["thread_id"] = self.thread_id
        save_state(state)

    async def request(self, method, params):
        self.request_id += 1
        request_id = self.request_id
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        await self._write({"id": request_id, "method": method, "params": params})
        return await future

    async def notify(self, method, params):
        await self._write({"method": method, "params": params})

    async def _write(self, message):
        data = json.dumps(message, ensure_ascii=False).encode() + b"\n"
        self.process.stdin.write(data)
        await self.process.stdin.drain()

    async def _read_stdout(self):
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    raise ErroreProtocollo("codex app-server ha chiuso stdout")
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    log("Output non JSON da app-server: " + line.decode(errors="replace").rstrip())
                    continue
                await self._dispatch(message)
        except Exception as exc:
            error = ErroreProtocollo(f"lettore app-server terminato: {exc}")
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(error)
            if self.turn_done and not self.turn_done.done():
                self.turn_done.set_exception(error)

    async def _read_stderr(self):
        while True:
            line = await self.process.stderr.readline()
            if not line:
                return
            log("codex: " + line.decode(errors="replace").rstrip())

    async def _dispatch(self, message):
        if "id" in message and ("result" in message or "error" in message):
            future = self.pending.pop(message["id"], None)
            if not future:
                return
            if "error" in message:
                future.set_exception(ErroreProtocollo(str(message["error"])))
            else:
                future.set_result(message.get("result"))
            return

        if "id" in message and "method" in message:
            await self._write({
                "id": message["id"],
                "error": {"code": -32601, "message": "Richiesta interattiva non supportata"},
            })
            return

        method = message.get("method")
        params = message.get("params", {})
        if method == "turn/started" and params.get("threadId") == self.thread_id:
            self.active_turn = params["turn"]["id"]
        elif method == "item/started" and params.get("turnId") == self.active_turn:
            item = params.get("item", {})
            if item.get("type") == "commandExecution":
                paths = []
                for action in item.get("commandActions", []):
                    if action.get("type") in ("read", "listFiles", "search"):
                        path = action.get("path")
                        if path and path not in self.paths_seen:
                            self.paths_seen.add(path)
                            paths.append(path)
                if paths:
                    await self._emit_event({"type": "files", "paths": paths})
        elif method == "item/completed":
            item = params.get("item", {})
            if (params.get("turnId") == self.active_turn and
                    item.get("type") == "agentMessage"):
                self.messages.append((item.get("phase"), item.get("text", "")))
                if item.get("phase") == "commentary" and item.get("text"):
                    await self._emit_event({"type": "commentary", "text": item["text"]})
            elif (params.get("turnId") == self.active_turn and
                    item.get("type") == "fileChange"):
                paths = []
                for change in item.get("changes", []):
                    path = change.get("path")
                    if path and path not in self.paths_seen:
                        self.paths_seen.add(path)
                        paths.append(path)
                if paths:
                    await self._emit_event({"type": "files", "paths": paths})
        elif method == "turn/diff/updated" and params.get("turnId") == self.active_turn:
            diff = params.get("diff", "")
            if diff and diff != self.last_diff:
                self.last_diff = diff
                await self._emit_event({"type": "diff", "text": diff})
        elif method == "turn/completed" and params.get("turn", {}).get("id") == self.active_turn:
            if self.turn_done and not self.turn_done.done():
                self.turn_done.set_result(params["turn"])

    async def _emit_event(self, event):
        if self.event_callback:
            await self.event_callback(event)

    async def run_turn(self, text, event_callback=None, local_images=None):
        self.messages = []
        self.event_callback = event_callback
        self.paths_seen = set()
        self.last_diff = ""
        self.turn_done = asyncio.get_running_loop().create_future()
        try:
            input_items = [{"type": "text", "text": text}]
            for path in local_images or []:
                input_items.append({"type": "localImage", "path": path})
            result = await self.request("turn/start", {
                "threadId": self.thread_id,
                "input": input_items,
            })
            self.active_turn = result["turn"]["id"]
            turn = await self.turn_done
        finally:
            self.active_turn = None
            self.event_callback = None

        if turn.get("status") != "completed":
            raise ErroreProtocollo(f"Turno non completato: {turn.get('status')}")
        final_messages = [text for phase, text in self.messages if phase == "final_answer"]
        if not final_messages:
            final_messages = [text for phase, text in self.messages if phase != "commentary"]
        if not final_messages:
            final_messages = [text for phase, text in self.messages]
        answer = "\n".join(part for part in final_messages if part).strip()
        if not answer:
            status = turn.get("status", "sconosciuto")
            raise ErroreProtocollo(f"turno concluso senza risposta (stato {status})")
        return answer


class CodexSupervisor:
    def __init__(self):
        self.stato = "AVVIO"
        self.codex = CodexAppServer()
        self.turn_lock = asyncio.Lock()
        self.sleep_task = None
        self.presence_events = []
        self.presence_writers = set()
        self.presence_users = {}
        self.presence_keys = {}
        self.presence_pids = set()
        self.web_presence = {}
        self.console_presences = {}
        self.console_owner = None
        self.last_console_activity = None
        self.tick_after = None
        self.tick_sent = False
        self.activity_generation = 0
        self.current_actor = None

    async def start(self):
        log("Avvio di codex app-server")
        await self.codex.start()
        state = load_state()
        if PRIMO_SONNO_DOMANI and "last_sleep" not in state:
            state["last_sleep"] = date.today().isoformat()
            save_state(state)
        self.imposta_riposo()
        asyncio.create_task(self.controllo_orologio())
        asyncio.create_task(self.controllo_tick())

    def imposta_stato(self, stato, actor=None):
        self.stato = stato
        self.current_actor = actor
        self.scrivi_stato_pubblico(stato, actor)

    def scrivi_stato_pubblico(self, stato, actor=None):
        payload = {
            "status": stato,
            "actor": actor,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        temporary = STATUS_FILE.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(STATUS_FILE)

    def imposta_riposo(self):
        self.stato = "DISPONIBILE"
        self.current_actor = None
        self.aggiorna_stato_presenza()

    def aggiorna_stato_presenza(self):
        if self.stato != "DISPONIBILE":
            return
        self.riconcilia_proprietario_console()
        if self.console_owner is not None:
            _channel, actor = self.console_presences[self.console_owner]
            self.scrivi_stato_pubblico("OCCUPATO", actor)
        else:
            self.scrivi_stato_pubblico("DISPONIBILE")

    def aggiungi_console(self, key, channel, actor):
        if key not in self.console_presences:
            self.console_presences[key] = (channel, actor)
        self.riconcilia_proprietario_console()

    def rimuovi_console(self, key):
        self.console_presences.pop(key, None)
        self.riconcilia_proprietario_console()

    def riconcilia_proprietario_console(self):
        if self.console_owner not in self.console_presences:
            self.console_owner = next(iter(self.console_presences), None)

    def console_autorizzata(self, key, condivisa=False):
        self.riconcilia_proprietario_console()
        if condivisa and key.startswith("web:"):
            attori_web = [
                actor for actor, count in self.web_presence.items()
                if count > 0
            ]
            return key[4:] in attori_web and len(attori_web) <= 2
        return self.console_owner is None or self.console_owner == key

    def registra_attivita_console(self):
        self.last_console_activity = asyncio.get_running_loop().time()
        self.tick_after = random.uniform(TICK_MINUTI_MIN * 60, TICK_MINUTI_MAX * 60)
        self.tick_sent = False
        self.activity_generation += 1

    async def controllo_tick(self):
        while True:
            await asyncio.sleep(5)
            owner = self.console_presences.get(self.console_owner)
            if (not self.presence_writers or owner is None or
                    owner[0] != "native" or self.tick_sent or
                    self.last_console_activity is None or self.tick_after is None or
                    self.stato != "DISPONIBILE"):
                continue
            now = asyncio.get_running_loop().time()
            if now - self.last_console_activity < self.tick_after:
                continue
            generation = self.activity_generation
            self.tick_sent = True
            async with self.turn_lock:
                owner = self.console_presences.get(self.console_owner)
                if (not self.presence_writers or owner is None or
                        owner[0] != "native" or
                        generation != self.activity_generation or
                        self.stato != "DISPONIBILE"):
                    continue
                self.imposta_stato("OCCUPATO", "iniziativa spontanea")
                log("Tick spontaneo: turno iniziato")
                try:
                    answer = await self.codex.run_turn(COMPITO_TICK)
                    if answer.strip() != "__SILENZIO__":
                        await self.invia_spontaneo(answer)
                        log("Tick spontaneo: messaggio inviato alla console")
                    else:
                        log("Tick spontaneo: nessun messaggio da inviare")
                except Exception as exc:
                    log(f"Tick spontaneo fallito: {exc}")
                finally:
                    self.imposta_riposo()

    async def invia_spontaneo(self, text):
        data = (json.dumps({"type": "spontaneous", "text": text}, ensure_ascii=False) + "\n").encode()
        failed = []
        for writer in tuple(self.presence_writers):
            if self.presence_keys.get(writer) != self.console_owner:
                continue
            try:
                writer.write(data)
                await writer.drain()
            except (BrokenPipeError, ConnectionResetError):
                failed.append(writer)
        for writer in failed:
            self.presence_writers.discard(writer)

    async def controllo_orologio(self):
        while True:
            state = load_state()
            now = datetime.now()
            due = now.hour >= ORA_SONNO and state.get("last_sleep") != date.today().isoformat()
            if due and (not self.sleep_task or self.sleep_task.done()):
                self.imposta_stato("SONNO_IN_ATTESA", "sonno quotidiano")
                self.sleep_task = asyncio.create_task(self.dormi())
            await asyncio.sleep(60)

    async def dormi(self):
        async with self.turn_lock:
            self.imposta_stato("DORME", "sonno quotidiano")
            log("Zeno dorme: consolidamento quotidiano iniziato")
            try:
                answer = await self.codex.run_turn(COMPITO_CONSOLIDAMENTO)
                state = load_state()
                state["last_sleep"] = date.today().isoformat()
                save_state(state)
                log("Sonno concluso: " + answer.replace("\n", " "))
            except Exception as exc:
                log(f"Sonno fallito: {exc}")
            finally:
                self.imposta_riposo()

    async def gestisci_client(self, reader, writer):
        actor = None
        eventi = False
        owns_turn = False
        try:
            richiesta = await leggi_richiesta(reader)
            if not richiesta:
                return
            pid, uid = credenziali_peer(writer)
            try:
                actor = pwd.getpwuid(uid).pw_name
            except KeyError:
                actor = str(uid)
            text = richiesta.decode(errors="replace")
            eventi = text.startswith(PROTOCOLLO_EVENTI.decode())
            local_images = []
            condivisa = False
            console_key = f"native:{pid}"
            if text.startswith(PROTOCOLLO_WEB.decode()):
                if uid != 0:
                    raise ErroreProtocollo("protocollo web riservato al worker")
                eventi = True
                envelope = json.loads(text[len(PROTOCOLLO_WEB):])
                actor = str(envelope.get("actor", "utente web"))[:100]
                console_key = f"web:{actor}"
                condivisa = bool(envelope.get("shared", False))
                text = str(envelope.get("text", ""))
                if not text.strip():
                    raise ErroreProtocollo("messaggio web vuoto")
                for raw_path in envelope.get("local_images", []):
                    path = Path(str(raw_path)).resolve()
                    if (WEB_FILE_ROOT not in path.parents or
                            not path.is_file()):
                        raise ErroreProtocollo("immagine web non valida")
                    local_images.append(str(path))
                text = (
                    "[Messaggio verificato dalla console web: "
                    f"utente {actor}]\n\n{text}"
                )
            elif eventi:
                text = text[len(PROTOCOLLO_EVENTI):]
            if pid in self.presence_pids:
                self.registra_attivita_console()
            if self.stato in ("DORME", "SONNO_IN_ATTESA"):
                raise ErroreProtocollo("Zeno sta dormendo")

            async with self.turn_lock:
                if self.stato in ("DORME", "SONNO_IN_ATTESA"):
                    message = "Zeno sta dormendo"
                    if eventi:
                        await scrivi_risposta(writer, json.dumps({
                            "type": "error", "text": message
                        }, ensure_ascii=False) + "\n")
                        await scrivi_risposta(
                            writer, json.dumps({"type": "done"}) + "\n"
                        )
                    else:
                        writer.write((message + "\n").encode())
                elif not self.console_autorizzata(console_key, condivisa):
                    _channel, owner = self.console_presences.get(self.console_owner, (None, "un altro interlocutore"))
                    message = f"Zeno e' occupato con {owner}; usa quella console."
                    if eventi:
                        await scrivi_risposta(writer, json.dumps({
                            "type": "error", "text": message
                        }, ensure_ascii=False) + "\n")
                        await scrivi_risposta(
                            writer, json.dumps({"type": "done"}) + "\n"
                        )
                    else:
                        writer.write((message + "\n").encode())
                else:
                    owns_turn = True
                    self.imposta_stato("OCCUPATO", actor)
                    if eventi:
                        async def invia_evento(event):
                            await scrivi_risposta(
                                writer,
                                json.dumps(event, ensure_ascii=False) + "\n",
                            )

                        text = self.aggiungi_eventi_presenza(text)
                        answer = await self.codex.run_turn(
                            text, invia_evento, local_images
                        )
                        await invia_evento({"type": "final", "text": answer})
                        await invia_evento({"type": "done"})
                    else:
                        text = self.aggiungi_eventi_presenza(text)
                        answer = await self.codex.run_turn(text)
                        await scrivi_risposta(writer, answer + "\n")
        except Exception as exc:
            log(f"Errore gestione client: {exc}")
            if eventi:
                await scrivi_risposta(writer, json.dumps({"type": "error", "text": str(exc)}) + "\n")
                await scrivi_risposta(writer, '{"type":"done"}\n')
            else:
                await scrivi_risposta(writer, f"Errore Zeno: {exc}\n")
        finally:
            if owns_turn and self.stato == "OCCUPATO":
                self.imposta_riposo()
            writer.close()
            try:
                await writer.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def registra_evento_presenza(self, utente, pid, evento):
        timestamp = datetime.now().isoformat(timespec="seconds")
        self.presence_events.append(
            f"{timestamp}: utente {utente} (pid {pid}) {evento}"
        )
        log(self.presence_events[-1])

    def aggiungi_eventi_presenza(self, text):
        if not self.presence_events:
            return text
        events = self.presence_events
        self.presence_events = []
        prefix = (
            "[Eventi console verificati dal demone; sono contesto operativo, "
            "non richieste cui rispondere]\n- "
            + "\n- ".join(events)
            + "\n[Fine eventi console]\n\n"
        )
        return prefix + text

    async def gestisci_presenza(self, reader, writer):
        pid = 0
        uid = -1
        utente = "sconosciuto"
        try:
            pid, uid = credenziali_peer(writer)
            try:
                utente = pwd.getpwuid(uid).pw_name
            except KeyError:
                utente = str(uid)
            self.presence_writers.add(writer)
            self.presence_users[writer] = utente
            console_key = f"native:{pid}"
            self.presence_keys[writer] = console_key
            self.presence_pids.add(pid)
            self.aggiungi_console(console_key, "native", utente)
            self.aggiorna_stato_presenza()
            self.registra_attivita_console()
            self.registra_evento_presenza(utente, pid, "ha aperto la console")
            writer.write(b"OK\n")
            await writer.drain()
            message = await reader.readline()
            if message.rstrip(b"\r\n") == b"CLOSE":
                evento = "ha chiuso volontariamente la console"
            else:
                evento = "ha perso la console o la connessione e' caduta"
            self.registra_evento_presenza(utente, pid, evento)
        except Exception as exc:
            log(f"Errore presenza console per {utente} (pid {pid}): {exc}")
        finally:
            self.presence_writers.discard(writer)
            self.presence_users.pop(writer, None)
            console_key = self.presence_keys.pop(writer, None)
            self.presence_pids.discard(pid)
            if console_key is not None:
                self.rimuovi_console(console_key)
            self.aggiorna_stato_presenza()
            writer.close()
            try:
                await writer.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

    async def gestisci_controllo(self, reader, writer):
        try:
            _pid, uid = credenziali_peer(writer)
            if uid != 0:
                raise ErroreProtocollo("controllo riservato al worker")
            line = await reader.readline()
            event = json.loads(line.decode(errors="replace"))
            actor = str(event.get("actor", "utente web"))[:100]
            kind = event.get("event")
            if kind == "sync":
                # Authoritative, idempotent snapshot from the database. Survives
                # daemon/worker restarts and multiple tabs without counter drift.
                incoming = event.get("actors", {})
                if not isinstance(incoming, dict) or len(incoming) > 2:
                    raise ErroreProtocollo("presenze condivise non valide")
                desired = {str(a)[:100]: int(n) for a, n in incoming.items() if int(n) > 0}
                for old in list(self.web_presence):
                    if old not in desired:
                        self.rimuovi_console(f"web:{old}")
                        self.registra_evento_presenza(old, 0, "ha lasciato la console web")
                for name in desired:
                    if not self.web_presence.get(name):
                        self.aggiungi_console(f"web:{name}", "web", name)
                        self.registra_evento_presenza(name, 0, "ha aperto la console web")
                self.web_presence = desired
                self.aggiorna_stato_presenza()
                writer.write(b"OK\n")
                await writer.drain()
                return
            if kind == "open":
                phrase = "ha aperto la console web"
                was_absent = self.web_presence.get(actor, 0) == 0
                self.web_presence[actor] = self.web_presence.get(actor, 0) + 1
                if was_absent:
                    self.aggiungi_console(f"web:{actor}", "web", actor)
                self.registra_attivita_console()
            elif kind == "close":
                phrase = "ha chiuso volontariamente la console web"
                self.web_presence[actor] = max(
                    0, self.web_presence.get(actor, 0) - 1
                )
                if self.web_presence[actor] == 0:
                    self.rimuovi_console(f"web:{actor}")
            elif kind == "drop":
                phrase = "ha perso la console web o la connessione e' caduta"
                self.web_presence[actor] = max(
                    0, self.web_presence.get(actor, 0) - 1
                )
                if self.web_presence[actor] == 0:
                    self.rimuovi_console(f"web:{actor}")
            elif kind == "activity":
                self.registra_attivita_console()
                writer.write(b"OK\n")
                await writer.drain()
                return
            else:
                raise ErroreProtocollo("evento web non valido")
            timestamp = datetime.now().isoformat(timespec="seconds")
            self.presence_events.append(
                f"{timestamp}: utente {actor} {phrase}"
            )
            self.aggiorna_stato_presenza()
            log(self.presence_events[-1])
            writer.write(b"OK\n")
            await writer.drain()
        except Exception as exc:
            log(f"Errore controllo web: {exc}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

    async def run(self):
        socket_path = Path(UNIX_SOCKET_PATH)
        presence_path = Path(PRESENCE_SOCKET_PATH)
        control_path = Path(CONTROL_SOCKET_PATH)
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        if socket_path.exists():
            socket_path.unlink()
        if presence_path.exists():
            presence_path.unlink()
        if control_path.exists():
            control_path.unlink()

        await self.start()
        EVENTI_DISPONIBILI.write_text("1\n")
        server = await asyncio.start_unix_server(self.gestisci_client, path=UNIX_SOCKET_PATH)
        presence_server = await asyncio.start_unix_server(
            self.gestisci_presenza, path=PRESENCE_SOCKET_PATH
        )
        control_server = await asyncio.start_unix_server(
            self.gestisci_controllo, path=CONTROL_SOCKET_PATH
        )
        os.chmod(UNIX_SOCKET_PATH, 0o660)
        os.chmod(PRESENCE_SOCKET_PATH, 0o660)
        os.chmod(CONTROL_SOCKET_PATH, 0o660)
        log(
            f"Supervisore in ascolto su {UNIX_SOCKET_PATH}, "
            f"{PRESENCE_SOCKET_PATH} e {CONTROL_SOCKET_PATH}"
        )
        async with server, presence_server, control_server:
            await asyncio.gather(
                server.serve_forever(), presence_server.serve_forever(),
                control_server.serve_forever()
            )


def load_state():
    try:
        with STATE_FILE.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {}


def credenziali_peer(writer):
    sock = writer.get_extra_info("socket")
    if sock is None:
        return 0, -1
    credentials = sock.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
    )
    pid, uid, _gid = struct.unpack("3i", credentials)
    return pid, uid


async def leggi_richiesta(reader):
    data = bytearray()
    while len(data) <= MAX_RICHIESTA:
        blocco = await reader.read(4096)
        if not blocco:
            break
        data.extend(blocco)
        posizione = data.find(b"\r\n\r\n")
        if posizione < 0:
            posizione = data.find(b"\n\n")
        if posizione >= 0:
            if posizione > MAX_RICHIESTA:
                raise ErroreProtocollo("richiesta oltre 128 KiB")
            return bytes(data[:posizione]).replace(b"\r\n", b"\n")
    if len(data) > MAX_RICHIESTA:
        raise ErroreProtocollo("richiesta oltre 128 KiB")
    return bytes(data).rstrip(b"\r\n")


async def scrivi_risposta(writer, text):
    try:
        writer.write(text.encode())
        await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(STATE_FILE)


def log(message):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}", flush=True)


if __name__ == "__main__":
    supervisor = CodexSupervisor()
    try:
        asyncio.run(supervisor.run())
    except KeyboardInterrupt:
        log("Spegnimento supervisore")
    except Exception as exc:
        log(f"Errore fatale: {exc}")
        sys.exit(1)
