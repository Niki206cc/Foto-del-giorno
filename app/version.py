APP_VERSION = "1.2.6"

CHANGELOG = [
    {
        "version": "1.2.6",
        "date": "28/08/2026",
        "changes": [
            "La riga iniziale degli articoli ora mostra 'La foto del giorno - Nome Autore' quando l'autore è disponibile, così può comparire anche nelle anteprime/condivisioni WhatsApp.",
            "Aggiunto il custom field WordPress foto_instagram_url con il link completo al profilo Instagram.",
            "Aggiunto lo shortcode WordPress [foto_instagram_link] per mostrare @nomeutente come link cliccabile nei Loop Elementor.",
            "Il parser Instagram accetta nomeutente, @nomeutente e URL Instagram nei campi del modulo/email.",
            "Aggiunta email automatica di ringraziamento dopo la ricezione di una foto dal modulo.",
            "Aggiunte nelle impostazioni le URL di sito, Instagram, Facebook, Telegram e WhatsApp da inserire nella mail di ringraziamento.",
            "Preimpostati i canali Telegram e WhatsApp ufficiali rilevati sul sito Montagne & Paesi.",
            "Aggiornato il plugin WordPress Foto del Giorno Meta alla versione 1.3.0."
        ],
    },
    {
        "version": "1.2.5",
        "date": "28/08/2026",
        "changes": [
            "Aggiunto supporto al nome utente Instagram facoltativo inviato dal modulo del sito.",
            "Il sistema riconosce automaticamente campi email etichettati Instagram, Nome utente Instagram o Username Instagram.",
            "Aggiunto il campo Instagram nella schermata di modifica della foto.",
            "Se presente, il profilo Instagram viene pubblicato nel testo dell'articolo come link cliccabile a @nomeutente.",
            "Aggiunto il custom field WordPress foto_instagram utilizzabile anche nei template Elementor.",
            "Aggiornato il plugin WordPress Foto del Giorno Meta alla versione 1.2.0."
        ],
    },
    {
        "version": "1.2.4",
        "date": "25/08/2026",
        "changes": [
            "Corretto il passaggio dei custom field verso WordPress: autore, luogo, provincia e data vengono ora codificati in JSON Base64 per evitare che Postie unisca le righe.",
            "Aggiornato il plugin WordPress alla versione 1.1.0 con parsing robusto dei metadati.",
            "Aggiunta compatibilità con i vecchi marcatori della v1.2.1-v1.2.3.",
            "Aggiunta riparazione automatica dei post in cui foto_autore conteneva per errore anche luogo, provincia e data."
        ],
    },
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
