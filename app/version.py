APP_VERSION = "1.2.3"

CHANGELOG = [
    {
        "version": "1.2.3",
        "date": "25/08/2026",
        "changes": [
            "Corretto il riconoscimento degli allegati inviati da Elementor/Post SMTP.",
            "Le immagini vengono ora riconosciute anche quando il server le invia come application/octet-stream invece di image/jpeg.",
            "Aggiunto supporto al MIME image/jpg oltre a image/jpeg.",
            "Il riconoscimento usa anche l'estensione reale del nome file: .jpg, .jpeg, .png e .webp."
        ],
    },
    {
        "version": "1.2.2",
        "date": "25/08/2026",
        "changes": [
            "Corretto il controllo IMAP: vengono esaminate tutte le email della INBOX e non soltanto quelle marcate come non lette.",
            "Aggiunto controllo Message-ID per impedire la reimportazione delle email già presenti nel database.",
            "Le email con fotografia vengono eliminate dal server soltanto dopo che l'importazione è riuscita.",
            "Aggiunto EXPUNGE IMAP per rendere effettiva l'eliminazione delle email elaborate.",
            "Le email senza immagini valide non vengono eliminate, per evitare la perdita accidentale di messaggi.",
            "Il risultato della sincronizzazione mostra foto importate, email eliminate ed email senza foto."
        ],
    },
    {
        "version": "1.2.1",
        "date": "25/08/2026",
        "changes": [
            "Eliminata la dipendenza dal Postie Shortcodes AddOn a pagamento.",
            "I dati foto_autore, foto_luogo, foto_provincia e foto_data vengono ora inviati tramite un marcatore HTML tecnico invisibile.",
            "Aggiunto nel repository un plugin WordPress gratuito che converte automaticamente i dati ricevuti in custom field.",
            "Il blocco tecnico viene rimosso dal contenuto WordPress dopo il salvataggio dei metadati.",
            "I custom field restano utilizzabili come campi dinamici in Elementor Pro."
        ],
    },
    {
        "version": "1.2.0",
        "date": "25/08/2026",
        "changes": [
            "Aggiunto passaggio automatico a WordPress dei custom field foto_autore, foto_luogo, foto_provincia e foto_data.",
            "Prima implementazione basata su Postie Shortcodes AddOn, sostituita nella v1.2.1 dalla soluzione gratuita."
        ],
    },
    {
        "version": "1.1.0",
        "date": "25/08/2026",
        "changes": [
            "Rimosso 'status: publish' dal contenuto HTML dell'articolo per evitare che compaia nelle anteprime social.",
            "Aggiunta la dicitura 'Foto del giorno' all'inizio del contenuto pubblicato.",
            "Il nome dell'autore dello scatto viene sempre aggiunto al testo come 'Foto di: Nome Cognome'.",
            "Aggiunto supporto all'ID numerico della categoria WordPress per rendere più affidabile l'assegnazione tramite Postie.",
            "Versione dell'app visibile nella barra superiore.",
            "Aggiunta pagina Registro versioni con lo storico delle modifiche."
        ],
    },
    {
        "version": "1.0.0",
        "date": "Agosto 2026",
        "changes": [
            "Prima versione operativa di Foto del giorno.",
            "Ricezione fotografie via IMAP.",
            "Analisi AI delle immagini e generazione del testo.",
            "Programmazione della pubblicazione.",
            "Invio a WordPress tramite Postie.",
            "Archivio, cestino e impostazioni dalla dashboard."
        ],
    },
]
