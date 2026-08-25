# Foto del giorno — Montagne & Paesi

MVP pensato per Raspberry Pi + Portainer.

Flusso:

1. legge una casella IMAP;
2. salva le immagini allegate e la mail originale;
3. dalla dashboard scegli una foto;
4. l'AI analizza immagine + testo e prepara articolo/caption;
5. puoi modificare tutto;
6. programmi una data/ora;
7. il sistema invia una mail a Postie con foto allegata;
8. Postie pubblica su WordPress nella categoria configurata.

## Compatibilità Raspberry

Il Dockerfile usa `python:3.12-slim`, disponibile anche per ARM64. Con Raspberry Pi OS 64 bit non servono modifiche particolari.

## Avvio locale / Portainer da repository Git

```bash
cp .env.example .env
docker compose up -d --build
```

Dashboard:

`http://IP_DEL_RASPBERRY:8090`

I dati persistenti sono in:

`./data`

## Pubblicazione GitHub + Portainer Stack

### Opzione A — Portainer con repository Git

Puoi creare uno Stack scegliendo **Repository** e indicando il repository GitHub che contiene questo progetto.
Come compose path usa:

`docker-compose.yml`

Questa modalità esegue la build direttamente sul Raspberry.

### Opzione B — immagine GHCR

Puoi creare una GitHub Action che compila un'immagine ARM64 e la pubblica su GHCR.
Nel file `stack-portainer.yml` sostituisci:

`ghcr.io/TUO-UTENTE/foto-del-giorno:latest`

con la tua immagine.

## OpenAI

La API key va impostata come variabile d'ambiente:

`OPENAI_API_KEY`

Il modello si può cambiare dalla dashboard. L'app usa il Responses API e invia come input il testo della mail e l'immagine.

## Postie: categoria

L'app genera l'oggetto così:

`[La foto del giorno] Titolo dell'articolo`

Se viene impostato l'ID numerico della categoria WordPress, l'app preferisce l'ID:

`[123] Titolo dell'articolo`

Postie supporta l'override della categoria tramite parentesi quadre nel subject. La categoria deve esistere già in WordPress e in Postie deve essere abilitata l'opzione per riconoscere le categorie tramite parentesi quadre.

### Nota HTML/Postie

Per ottenere il corpo formattato, configura Postie per preferire HTML e consentire HTML nel corpo del messaggio.

## Custom field per Elementor

Dalla versione 1.2.0 l'app invia automaticamente a WordPress questi custom field:

- `foto_autore` — nome di chi ha scattato la foto;
- `foto_luogo` — località dello scatto;
- `foto_provincia` — provincia;
- `foto_data` — data dello scatto.

I campi vengono inviati tramite gli shortcode `[pcustom]` del **Postie Shortcodes AddOn**. Perché WordPress salvi realmente questi valori come custom field è necessario installare e attivare il Postie Shortcodes AddOn.

In Elementor Pro puoi poi usare **Tag dinamici → Campo personalizzato** e indicare una delle chiavi sopra. Per esempio:

- `Foto di: ` + campo dinamico `foto_autore`
- icona posizione + campo dinamico `foto_luogo`
- icona calendario + campo dinamico `foto_data`

Se l'add-on non è attivo, gli shortcode tecnici sono comunque inseriti in un contenitore HTML nascosto e non dovrebbero risultare visibili nell'articolo.

## Impostazioni disponibili

- IMAP: host, porta, SSL, account, password, cartella, intervallo.
- AI: modello e prompt modificabile.
- SMTP: host, porta, TLS, account, password, mittente.
- Postie: destinatario, categoria, ID categoria, tag, stato.
- Programmazione: ora predefinita.
- Footer: testo modificabile con `{email_foto}`.
- Pulizia automatica:
  - file delle foto già pubblicate dopo N giorni;
  - cestino dopo N giorni.

## Pulizia manuale

Da Impostazioni puoi:

- svuotare il cestino;
- eliminare le foto ricevute/non programmate;
- svuotare completamente il database foto.

Per le foto pubblicate la pulizia automatica può eliminare il JPEG mantenendo il record storico nel database.

## Limiti della V1

- Le password IMAP/SMTP sono salvate nel database SQLite locale. Il progetto è pensato per una LAN privata: non esporre la dashboard direttamente su Internet senza autenticazione/reverse proxy.
- Se una mail contiene più immagini, la V1 crea un elemento distinto per ciascuna.
- Lo stato `sent` significa che l'email è stata consegnata al server SMTP; non verifica ancora che Postie abbia effettivamente creato l'articolo WordPress.
- L'AI non deve essere considerata una fonte per identificare con certezza montagne o persone: il prompt le vieta di inventare dettagli non forniti.

## Prossimi miglioramenti consigliati

- login per la dashboard;
- cifratura delle password salvate;
- selezione multipla immagini;
- endpoint JSON per l'automazione Instagram;
- webhook/controllo WordPress per confermare la pubblicazione effettiva;
- riordino drag-and-drop della coda;
- statistiche e ricerca archivio.
