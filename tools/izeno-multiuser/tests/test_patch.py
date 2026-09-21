#!/usr/bin/env python3
"""Usage: python3 test_patch.py /path/to/patched/package. No Codex/network calls."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

root=Path(sys.argv.pop(1)).resolve()
spec=importlib.util.spec_from_file_location('patched_demone',root/'reference/demone.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Writer:
    def __init__(self):self.data=bytearray()
    def write(self,data):self.data.extend(data)
    async def drain(self):pass
    def close(self):pass
    async def wait_closed(self):pass

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old_status=m.STATUS_FILE;self.old_state=m.STATE_FILE
        m.STATUS_FILE=Path(self.tmp.name)/'status.json';m.STATE_FILE=Path(self.tmp.name)/'state.json'
    def tearDown(self):
        m.STATUS_FILE=self.old_status;m.STATE_FILE=self.old_state;self.tmp.cleanup()
    async def test_shared_authorization_and_exclusive_console(self):
        s=m.CodexSupervisor();s.aggiungi_console('web:Enrico','web','Enrico')
        s.web_presence={'Enrico':1,'Antonio':2}
        self.assertTrue(s.console_autorizzata('web:Antonio',True))
        self.assertFalse(s.console_autorizzata('web:Antonio',False))
        self.assertFalse(s.console_autorizzata('web:Assente',True))
        s.web_presence['Terzo']=1
        self.assertFalse(s.console_autorizzata('web:Antonio',True))
    async def test_sync_is_idempotent_and_restores_tabs(self):
        s=m.CodexSupervisor();s.imposta_riposo()
        for actors in [{'Enrico':1,'Antonio':2},{'Enrico':1,'Antonio':2},{'Antonio':1}]:
            r=asyncio.StreamReader();r.feed_data((json.dumps({'event':'sync','actors':actors})+'\n').encode());r.feed_eof();w=Writer()
            with patch.object(m,'credenziali_peer',return_value=(1,0)):await s.gestisci_controllo(r,w)
            self.assertEqual(bytes(w.data),b'OK\n');self.assertEqual(s.web_presence,actors)
        self.assertEqual(set(s.console_presences),{'web:Antonio'})
    async def test_json_failure_and_busy_state_ownership(self):
        s=m.CodexSupervisor();s.codex.run_turn=AsyncMock(side_effect=RuntimeError('fixture failure'))
        s.imposta_riposo();s.web_presence={'Enrico':1};s.aggiungi_console('web:Enrico','web','Enrico')
        request=m.PROTOCOLLO_WEB+json.dumps({'actor':'Enrico','text':'test','shared':True}).encode()+b'\r\n\r\n'
        r=asyncio.StreamReader();r.feed_data(request);r.feed_eof();w=Writer()
        with patch.object(m,'credenziali_peer',return_value=(1,0)):await s.gestisci_client(r,w)
        events=[json.loads(l) for l in w.data.decode().splitlines()]
        self.assertEqual([e['type'] for e in events],['error','done'])
        self.assertEqual(s.stato,'DISPONIBILE')
        # A malformed second client must not clear another request's busy state.
        s.imposta_stato('OCCUPATO','Antonio');r=asyncio.StreamReader();r.feed_data(m.PROTOCOLLO_WEB+b'{bad}\r\n\r\n');r.feed_eof();w=Writer()
        with patch.object(m,'credenziali_peer',return_value=(1,0)):await s.gestisci_client(r,w)
        self.assertEqual(s.stato,'OCCUPATO');self.assertEqual(s.current_actor,'Antonio')
    async def test_sleep_is_a_framed_error(self):
        s=m.CodexSupervisor();s.imposta_stato('DORME')
        r=asyncio.StreamReader();r.feed_data(m.PROTOCOLLO_WEB+json.dumps({'actor':'Enrico','text':'test'}).encode()+b'\r\n\r\n');r.feed_eof();w=Writer()
        with patch.object(m,'credenziali_peer',return_value=(1,0)):await s.gestisci_client(r,w)
        events=[json.loads(l) for l in w.data.decode().splitlines()]
        self.assertEqual(events[0]['type'],'error');self.assertEqual(s.stato,'DORME')
    async def test_bad_state_does_not_create_fresh_identity(self):
        m.STATE_FILE.write_text('{bad}')
        with self.assertRaises(json.JSONDecodeError):m.load_state()
        c=m.CodexAppServer();c.request=AsyncMock(side_effect=m.ErroreProtocollo('cannot resume'))
        with patch.object(m,'load_state',return_value={'thread_id':'old-thread'}):
            with self.assertRaises(m.ErroreProtocollo):await c._open_thread()
        self.assertEqual(c.request.await_count,1)
        self.assertEqual(c.request.await_args.args[0],'thread/resume')
    async def test_notifications_before_start_response(self):
        c=m.CodexAppServer();c.thread_id='thread'
        async def request(method,params):
            await c._dispatch({'method':'turn/started','params':{'threadId':'thread','turn':{'id':'turn'}}})
            await c._dispatch({'method':'item/completed','params':{'turnId':'turn','item':{'type':'agentMessage','phase':'final_answer','text':'OK'}}})
            await c._dispatch({'method':'turn/completed','params':{'turn':{'id':'turn','status':'completed'}}})
            return {'turn':{'id':'turn'}}
        c.request=request
        self.assertEqual(await asyncio.wait_for(c.run_turn('test'),1),'OK')

unittest.main()
