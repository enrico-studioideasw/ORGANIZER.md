# Diario Zeno

## Servizi del covo malvagio

- Fatto: Apache 2.4 serve esclusivamente l'archivio `/var/www/ewb-5.30` tramite HTTPS su `civolle.it:444`; la home e il servizio EWB restano sotto `ewbd` e Caddy.
- Fatto: Apache riusa il certificato `civolle.it` gestito da Caddy; `apache2-cert-reload.timer` ricarica Apache ogni giorno per acquisire i rinnovi.
- Vincolo: la porta pubblica `444/TCP` deve essere inoltrata direttamente a questo server; non passa da Caddy e non e' ridondata sul cluster.
- Fatto: il server usa Debian 13 e l'indirizzo LAN rilevato il 2026-07-14 e' `192.168.2.51`.
- Fatto: Samba espone `backup-enrico` da `/home/enrico/backup`; accesso guest disabilitato e accesso limitato all'utente `enrico`.
- Vincolo: il backup di Enrico risiede sul disco principale del server; protegge dal guasto del laptop, non dal guasto del disco del server.
- Fatto: Mosquitto 2.0.21 e' installato e attivo; al momento ascolta soltanto su localhost, porta `1883/TCP`.
- Decisione: non esporre MQTT tramite NAT finche' non sono configurati autenticazione e TLS. Per MQTT su TLS usare normalmente `8883/TCP`.

## Diari di progetto

- Decisione: dal 2026-07-16 la copia autorevole di EWB e del sito ufficiale e' `/home/noc/EWB2026` sul server aziendale; le copie in `/root` non sono autorevoli salvo indicazione esplicita.
- Progetto LoRa: vedere `DIARIO_LORA.md`.
- Recupero netbook WM8850: vedere `DIARIO_WM8850.md`.
