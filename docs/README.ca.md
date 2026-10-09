# Mensagia Attachment Mailer

Aplicació per enviar correus electrònics amb adjunts personalitzats per contacte fent servir la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Galego](README.gl.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisits

- Windows 10/11 o macOS (per als executables)
- O Python 3.11+ (per executar des del codi font)

---

## Ús de l'executable (clients sense Python)

Descarrega la versió per al teu ordinador des de la [pàgina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Ordinador | Mode gràfic | Mode consola |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Mac amb Apple Silicon (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Mac amb processador Intel | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### Token API

L'aplicació necessita el teu token API de Mensagia, que pots obtenir a [mensagia.com](https://mensagia.com) → Usuaris. Si no el tens configurat, te'l demanarà en arrencar. Per no haver-lo d'introduir cada vegada, desa'l en un fitxer `.env` a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació):

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

### Windows

1. Descarrega el `.exe`. L'aplicació desa els seus fitxers a la mateixa carpeta, així que convé posar-lo en una carpeta pròpia.
2. Opcionalment, crea el fitxer `.env` en aquesta **mateixa carpeta**.
3. Executa el `.exe`.

> **Avís de Windows SmartScreen:** la primera vegada que executis el fitxer, el Windows pot mostrar un avís de seguretat. Fes clic a **"Més informació"** i després a **"Executa de totes maneres"**. Només cal fer-ho una vegada per cada versió descarregada.

### macOS

1. **Tria la versió del teu Mac.** Obre el menú Apple → **Quant a aquest Mac**:
   - Si hi apareix **Xip** (Apple M1, M2, M3…), descarrega la versió `apple-silicon`.
   - Si hi apareix **Processador** (Intel…), descarrega la versió `intel`.

   > GitHub està retirant les màquines que compilen per a Mac amb Intel. Si l'última versió no inclou els fitxers `intel`, descarrega'ls de la versió més recent que els tingui a la [llista de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Fes doble clic al `.zip` per descomprimir-lo (el Safari ho pot fer automàticament en descarregar-lo). En mode gràfic obtindràs `mensagia-mailer-gui.app`, que pots moure a **Aplicacions**.
3. Opcionalment, desa el fitxer `.env` a la carpeta **Mensagia Mailer** de la teva carpeta personal. Pots crear totes dues coses des del Terminal:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=el_teu_token_api_aqui" > ~/"Mensagia Mailer/.env"
   ```

   > El Finder amaga els fitxers el nom dels quals comença per un punt, com `.env`. Prem **Ordre + Maj + .** per mostrar-los o amagar-los.

4. Obre l'aplicació. La primera vegada, el macOS la bloquejarà perquè no està signada per Apple (és l'equivalent de l'avís de SmartScreen del Windows). Per permetre-la:
   - **macOS 15 (Sequoia) o posterior:** després de l'avís, obre **Configuració del Sistema → Privacitat i seguretat**, baixa fins al missatge sobre l'aplicació i prem **Obre igualment**. Torna-la a obrir i confirma-ho.
   - **macOS 14 o anterior:** fes clic dret sobre l'aplicació → **Obre**, i confirma-ho a l'avís.
   - **En qualsevol versió, des del Terminal:** `xattr -cr` seguit de la ruta de l'aplicació, per exemple `xattr -cr /Applications/mensagia-mailer-gui.app`.

   Només cal fer-ho una vegada per cada versió descarregada.

> La versió de consola s'obre amb doble clic i funciona dins d'una finestra del Terminal.

---

## Avís de versió nova

En arrencar, l'aplicació comprova si s'ha publicat una versió més recent a la [pàgina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest). Si n'hi ha, mostra un avís discret amb el número de la versió nova i l'enllaç per descarregar-la:

- **Mode gràfic:** a la part inferior de la primera pantalla (la del token). Fes clic a l'enllaç per obrir la pàgina de descàrregues.
- **Mode consola:** una línia abans de demanar l'assumpte.

L'aplicació només avisa: no descarrega ni instal·la res. Per actualitzar-la, descarrega la versió nova tal com s'explica a [Ús de l'executable](#ús-de-lexecutable-clients-sense-python) i substitueix l'anterior. A Windows, posa el `.exe` nou a la mateixa carpeta per conservar els fitxers de la [carpeta de dades](#fitxers-de-laplicació).

Si no hi ha connexió o GitHub no respon en 3 segons, no es mostra res i l'aplicació funciona amb normalitat.

Per desactivar la comprovació, afegeix aquesta línia al fitxer `.env`:

```
MENSAGIA_CHECK_UPDATES=false
```

> Des del codi font l'aplicació no coneix el seu número de versió i no comprova res. Per provar l'avís, crea el fitxer `src/build_version.py` amb una versió anterior a l'última publicada, per exemple `VERSION = "v1.3.0"`, i esborra'l en acabar. Git ignora aquest fitxer, així que no es puja mai al repositori.

---

## Fitxers de l'aplicació

L'aplicació desa els seus fitxers en una carpeta de dades, que depèn de com s'executi:

| Execució | Carpeta de dades |
|---|---|
| Windows (`.exe`) | La mateixa carpeta que el `.exe` |
| macOS | `Mensagia Mailer`, dins de la teva carpeta personal (`~/Mensagia Mailer`) |
| Codi font | L'arrel del projecte |

En aquesta carpeta hi ha:

- `.env`: la configuració (token API, idioma, URL base dels adjunts…). El crees tu i és opcional.
- `logs/`: un registre de cada enviament i de cada simulació (vegeu [Simular un enviament](#simular-un-enviament)).
- `last_selections.json`: les últimes opcions triades (vegeu [Memòria de seleccions](#memòria-de-seleccions-mode-gràfic)).
- `send_progress.json`: el progrés dels enviaments (vegeu [Reprendre un enviament interromput](#reprendre-un-enviament-interromput)).

L'aplicació crea la carpeta i els fitxers a mesura que els necessita.

---

## Ús des del codi font

### Instal·lació

```bash
# Clonar el repositori
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Crear entorn virtual (si no existeix)
python -m venv .venv

# Activar l'entorn
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instal·lar dependències
pip install -r requirements.txt
```

### Configurar el token API

Crea un fitxer `.env` a l'arrel del projecte (còpia de `.env.example`):

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

### Executar mode gràfic

```bash
python main_gui.py
```

### Executar mode consola

```bash
python main.py
```

---

## Flux d'enviament

1. **Token API** — Es llegeix del `.env` o es demana a l'usuari.
2. **Assumpte, hora d'inici i origen** — L'usuari introdueix l'assumpte del correu, tria quan surten els correus: ara, en una data i hora concretes o el dia de cada contacte (vegeu [Programar l'hora d'inici](#programar-lhora-dinici)) i d'on surten els destinataris: un **grup de l'agenda** o un **fitxer** (vegeu [Enviar als destinataris d'un fitxer](#enviar-als-destinataris-dun-fitxer)).
3. **Plantilla** — Es mostra la llista de plantilles d'email disponibles.
4. **Remitent** — Es mostra la llista d'adreces d'enviament verificades.
5. **Grup o fitxer**:
   - Amb l'agenda, es mostra una primera pàgina de grups. Si el grup buscat no hi apareix, es pot filtrar pel nom. Els grups sense contactes es mostren, però no es poden seleccionar.
   - Amb un fitxer, es tria el fitxer i, si és un Excel amb diversos fulls, el full.
6. **Camp adjunt o columnes**:
   - Amb l'agenda, es tria quin camp personalitzat conté la URL de l'adjunt. Si els correus surten el dia de cada contacte, a continuació es tria el camp amb la data i el seu format.
   - Amb un fitxer, es tria quina columna conté el correu i quina l'adjunt. Si els correus surten el dia de cada contacte, també la columna amb la data i el seu format.
7. **Certificat** — L'usuari decideix si certificar els enviaments.
8. **Enviament** — Es descarten els destinataris sense un correu vàlid o sense adjunt, i s'envia un correu per cada un a raó de 5/minut.

---

## Ruta de l'adjunt al camp personalitzat

El camp personalitzat triat al pas 6 (o la columna de l'adjunt, si els destinataris surten d'un fitxer) pot indicar l'adjunt de cada contacte de dues maneres:

- **URL completa**, que comença per `http://` o `https://` (per exemple, `https://cdn.empresa.com/docs/factura_42.pdf`). Es fa servir tal qual.
- **Nom de fitxer o ruta relativa** (per exemple, `factura_42.pdf` o `2026/factura_42.pdf`). L'aplicació hi afegeix al davant una **URL base**: amb la base `https://cdn.empresa.com/docs/`, el valor `factura_42.pdf` es converteix en `https://cdn.empresa.com/docs/factura_42.pdf`.

Les dues formes es poden combinar dins del mateix grup o fitxer.

La URL base es pot indicar de diverses maneres:

- Al fitxer `.env`, amb la variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- En el **mode gràfic**, al camp **URL base adjunts** de la primera pantalla. Si està definida al `.env`, ja apareix emplenada.
- En el **mode consola**, l'aplicació la demana només si algun contacte té una ruta relativa i la variable no és al `.env`.

> La URL base ha de ser sempre una **adreça web pública**, mai una carpeta de l'ordinador: és Mensagia qui descarrega el fitxer per adjuntar-lo al correu. Pot acabar en `/` o no; l'aplicació ho té en compte.

---

## Enviar als destinataris d'un fitxer

A més d'un grup de l'agenda, els destinataris poden sortir d'un fitxer **Excel (`.xlsx`)** o **CSV (`.csv`)**. Cada fila del fitxer és un correu, de manera que una mateixa adreça pot rebre diversos correus amb adjunts diferents en el mateix enviament (per exemple, una agència que rep la documentació de diversos clients seus). Els destinataris no han de ser a l'agenda de Mensagia.

### Com ha de ser el fitxer

- **La primera fila és la capçalera** i és obligatòria: conté el nom de cada columna.
- Els noms, l'ordre i el nombre de columnes són lliures. En preparar l'enviament es tria quina columna conté el correu i quina l'adjunt; les altres s'ignoren.
- Les files i les columnes completament buides s'ignoren.
- Si l'Excel té diversos fulls, es tria quin s'ha de fer servir. Si només en té un, no es pregunta.
- En els CSV, el separador (`;` o `,`) i la codificació (UTF-8 o la de Windows) es detecten automàticament.

Exemple:

| Client | Correu | Adjunt |
|---|---|---|
| Client A | agencia@exemple.com | factures/client_a.pdf |
| Client B | agencia@exemple.com | factures/client_b.pdf |
| Client C | info@clientc.com | https://cdn.empresa.com/docs/c.pdf |

L'aplicació no deixa continuar si:

- el fitxer és buit o només té la capçalera;
- alguna columna té dades però no té nom a la capçalera;
- hi ha dues columnes amb el mateix nom (sense distingir majúscules);
- alguna cel·la de la primera fila conté `@`: probablement el fitxer no té capçalera.

### Correu i adjunt de cada fila

- **Correu**: es treuen els espais del principi i del final. Ha de contenir una sola adreça: una sola `@`; abans de la `@`, només lletres sense accents, números i `. _ % + -`; després, lletres sense accents, números, `-` i com a mínim un punt. Una cel·la amb diverses adreces no és vàlida.
- **Adjunt**: com al camp personalitzat, una URL completa o una ruta relativa a la URL base (vegeu [Ruta de l'adjunt](#ruta-de-ladjunt-al-camp-personalitzat)). Els números es llegeixen sense decimals (`1234`, no `1234.0`).

Es descarten aquestes files, i el [log](#simular-un-enviament) n'indica el motiu:

- sense correu (`no_email`) o amb un correu no vàlid (`invalid_email`);
- sense adjunt (`no_attachment`);
- amb el mateix correu (sense distingir majúscules) i el mateix adjunt que una fila anterior (`duplicate_row`): només s'envia la primera. Si els correus surten el dia de cada contacte, també ha de coincidir la data. Un nom de fitxer i la URL completa que s'obté amb la URL base compten com el mateix adjunt.

Al log, cada fila s'identifica pel seu número tal com el mostra Excel (la capçalera és la fila 1), el correu i l'adjunt. Per exemple:

```
[SEND_SKIP]  row=14 to=agencia@exemple.com attachment=factures/client_a.pdf reason=duplicate_row
```

### Canvis al fitxer

El fitxer es torna a llegir en arribar al resum i en començar l'enviament, així que es fan servir els canvis desats mentrestant. Si el fitxer ja no es pot fer servir (per exemple, perquè s'ha canviat el nom d'una columna triada), l'aplicació ho indica i no envia res.

Per [reprendre un enviament interromput](#reprendre-un-enviament-interromput), un enviament amb fitxer s'identifica pel **nom del fitxer** (sense la carpeta), el full, les columnes triades, la plantilla, l'assumpte i el mode d'hora d'inici. Per això:

- Es pot moure el fitxer a una altra carpeta, corregir files, afegir-ne de noves o canviar-ne l'ordre. En reprendre l'enviament, només s'envien les files que faltaven, perquè cada fila es reconeix pel seu correu i el seu adjunt.
- Si es canvia el nom del fitxer, el full o alguna de les columnes, es tracta com un enviament nou.

> En el mode consola, la ruta del fitxer s'escriu o s'enganxa. S'accepten les cometes que afegeix l'opció «Copia com a camí» de Windows.

---

## ⚠ Avís sobre els contactes del grup

El grup s'utilitza com a **font de contactes**, no com a llista de subscripció. L'aplicació enviarà el correu a **tots els contactes que formin part del grup**, hi estiguin subscrits o no.

> La API de Mensagia no proporciona informació sobre l'estat de subscripció de cada contacte en una agenda. Si vols limitar l'enviament als subscrits, hauràs de gestionar aquesta segmentació directament a Mensagia abans de llançar l'aplicació.

---

## ⚠ Avís important sobre l'enviament

El programa **no envia els correus de forma immediata**. Per cada contacte elegible crea una configuració d'enviament individual a la plataforma Mensagia, programada per executar-se de forma escalonada:

- El **primer enviament** s'executa entre **10 i 20 minuts** després de llançar l'enviament, per donar marge a cancel·lar si es detecta algun error, o en la data i l'hora triades (vegeu [Programar l'hora d'inici](#programar-lhora-dinici)).
- Els **enviaments següents** s'espaiïen **12 segons** entre ells (5 per minut).

> **Si cal aturar l'enviament un cop iniciat**, tancar l'aplicació atura la creació de noves configuracions, però les que ja s'han creat s'enviaran igualment: hauràs d'eliminar-les una per una des del portal de Mensagia. No hi ha cap botó de cancel·lació global. Més endavant podràs reprendre l'enviament (vegeu [Reprendre un enviament interromput](#reprendre-un-enviament-interromput)).
>
> Fes servir el mode **Simular** per revisar què s'enviaria sense crear cap configuració real.

---

## Programar l'hora d'inici

A la pàgina de l'assumpte (en el mode consola, just després de l'assumpte) es tria quan surten els correus:

- **Ara**: entre 10 i 20 minuts després de començar l'enviament.
- **Dia i hora concrets**: el primer correu surt en la data i l'hora indicades, i els següents, cada 12 segons. Els enviaments poden passar de mitjanit.
- **Dia de cada contacte, a una hora concreta**: cada correu surt el dia indicat a les dades del contacte, a l'hora triada (vegeu [Enviar cada correu el dia del contacte](#enviar-cada-correu-el-dia-del-contacte)).

La data i l'hora s'escriuen sempre en l'ordre `dd/mm/aaaa` i `hh:mm`, sigui quin sigui l'idioma. En el mode gràfic hi ha un camp per a cada part, i el cursor passa sol al següent en completar-ne un. En el mode consola també s'accepten altres formes habituals (`8/10/26`, `8-10-2026`, `9h30`, `9`…), i amb Retorn s'accepta el valor proposat entre claudàtors.

Límits:

- **Marge mínim de 10 minuts.** En passar a la pàgina següent, la data i l'hora han de ser com a mínim 10 minuts posteriors a l'hora actual.
- **Posposició automàtica.** Si, mentre es completen els altres passos, l'hora triada deixa de tenir 10 minuts de marge, en començar l'enviament es posposa automàticament a la primera hora que el compleixi, com amb l'opció «Ara». L'aplicació no avisa, però el log de l'enviament indica l'hora triada (`start_at`) i la del primer correu (`first_slot`). Els correus no surten mai abans de l'hora triada.
- **Com a màxim, 6 setmanes d'antelació** des del moment de preparar l'enviament.
- La simulació no comprova l'hora, només les dades.

> ⚠ **Zona horària.** L'hora s'envia a Mensagia sense zona horària, i Mensagia la interpreta segons la **«Zona horària» configurada a l'usuari de Mensagia** associat al token. Comprova que coincideix amb la de l'ordinador que executa l'aplicació: si no, els correus sortiran a una hora diferent de la triada.

L'aplicació proposa la data d'avui i, com a hora, l'última triada en el mode gràfic o, si no n'hi ha cap, la que correspondria a l'opció «Ara».

Per [reprendre un enviament interromput](#reprendre-un-enviament-interromput) cal repetir exactament les mateixes opcions, inclòs el mode d'hora d'inici: si es canvia el mode, es tracta com un enviament nou. En canvi, canviar la data o l'hora no crea un enviament nou: en reprendre'l, els correus continuen després de l'últim programat, i l'hora nova només es fa servir si aquell moment ja no té 10 minuts de marge.

---

## Enviar cada correu el dia del contacte

Amb l'opció **Dia de cada contacte, a una hora concreta**, cada destinatari rep el correu el dia indicat a les seves dades: en un camp personalitzat (agenda) o en una columna (fitxer). Només es tria l'hora, que és la mateixa per a tots els dies.

- Amb l'agenda, després del camp de l'adjunt es tria el camp amb la data. No pot ser el mateix que el de l'adjunt.
- Amb un fitxer, a la pàgina de columnes també es tria la columna amb la data. No pot ser cap de les altres dues.

Cada dia comença a l'hora triada i afegeix 12 segons per cada correu anterior **del mateix dia**. Per exemple, amb les 09:00, tres correus del 15/10 surten a les 09:00:00, 09:00:12 i 09:00:24, i un del 16/10, a les 09:00:00.

| Data del contacte | Què passa |
|---|---|
| Un dia futur | Surt a l'hora triada d'aquell dia |
| Avui | A l'hora triada si falten com a mínim 10 minuts; si no, com amb «Ara» (de 10 a 20 minuts després) |
| Un dia passat | Es descarta (`past_send_date`) |
| A més de 6 setmanes | Es descarta (`send_date_too_far`) |
| Buida | Es descarta (`no_send_date`) |
| Amb un altre format | Es descarta (`invalid_send_date`) |
| Amb hora | Es descarta (`send_date_has_time`) |

Per exemple, a les 10:07 i amb l'hora 10:00, els contactes d'avui surten a les 10:20:00, 10:20:12…, i els dels dies següents, a les 10:00:00, 10:00:12… del seu dia.

- Els correus d'un dia poden passar de mitjanit. El dia següent no es desplaça, encara que durant una estona surtin més correus per minut.
- Els dies es programen en ordre, del més proper al més llunyà.

### Format de la data

Mensagia no indica el format dels seus camps de data, així que cal triar-lo: `dd/mm/aaaa`, `dd-mm-aaaa`, `aaaa/mm/dd` o `aaaa-mm-dd`.

L'ordre i el separador han de coincidir amb el format triat, però els zeros són opcionals i l'any pot tenir 2 xifres: amb `dd/mm/aaaa`, `3/4/26` és el 3 d'abril de 2026. Una data amb hora (`15/10/2026 10:00`) es descarta.

En un fitxer, el format només s'aplica a les dates escrites com a text (en un CSV, o en un Excel amb la cel·la en format de text). Les cel·les que Excel ja reconeix com a data es llegeixen directament; si tenen una hora diferent de 00:00, es descarten.

### Resum previ

Abans d'enviar, el resum mostra:

- una taula amb una fila per dia, amb el nombre de correus i l'hora aproximada del primer i de l'últim;
- els descartats, agrupats per motiu (el detall de cadascun és al log);
- amb un fitxer, les files que enviaran el mateix adjunt a la mateixa adreça en dates diferents. S'envien totes; si en sobra alguna, es pot eliminar des del portal de Mensagia.

Les hores són orientatives: l'hora definitiva de cada correu es calcula en programar-lo.

### Reprendre

Cada dia es reprèn per separat: continua després de l'últim correu programat d'aquell dia o, si no en tenia cap, a l'hora triada (avui, només si falten com a mínim 10 minuts). Els contactes pendents de dies que ja han passat es descarten. El camp o la columna de la data formen part de l'enviament: si es canvien, és un enviament nou.

---

## Simular un enviament

El botó **Simular** (en el mode consola, la resposta `Sim`) fa totes les comprovacions d'un enviament real (contactes aptes, URL dels adjunts i que es puguin descarregar), però **no programa cap correu** a Mensagia ni modifica el progrés desat per [reprendre un enviament](#reprendre-un-enviament-interromput).

Cada simulació genera un log amb el mateix contingut que el d'un enviament real: els contactes a qui s'enviaria el correu i els descartats, amb el motiu. En acabar, l'aplicació mostra la ruta del fitxer.

- Els logs es desen a la carpeta `logs/` de la [carpeta de dades de l'aplicació](#fitxers-de-laplicació).
- Els de les simulacions es diuen `mensagia_simulation_<data_hora>.log`, i els dels enviaments reals, `mensagia_send_<data_hora>.log`. Si ordenes la carpeta per nom, queden separats.
- La primera línia d'un log de simulació és `[SIMULATION] This is a simulation: no email was sent.` En aquest log, les línies `[SEND_OK]` són els correus que s'enviarien.

Motius de descart (`reason=` a les línies `[SEND_SKIP]`):

- `no_email`: el contacte o la fila no té adreça de correu.
- `invalid_email`: l'adreça de correu de la fila no és vàlida (només amb un fitxer).
- `no_attachment`: el camp personalitzat o la columna de l'adjunt és buit.
- `duplicate_row`: la fila repeteix el correu i l'adjunt d'una fila anterior (només amb un fitxer).
- `already_sent`: el destinatari ja va rebre el correu en un enviament anterior interromput de la mateixa campanya.
- `no_send_date`, `invalid_send_date` i `send_date_has_time`: la data del contacte és buida, no té el format triat o conté una hora (vegeu [Enviar cada correu el dia del contacte](#enviar-cada-correu-el-dia-del-contacte)).
- `past_send_date` i `send_date_too_far`: la data del contacte ja ha passat o és a més de 6 setmanes.

Les línies `[SEND_OK]` també indiquen la data i l'hora per a les quals s'ha programat cada correu (`start_date`), per trobar-lo al portal de Mensagia. El resum previ mostra els descartats agrupats per motiu.

Les línies `[SEND_ERROR]` corresponen a contactes aptes l'adjunt dels quals no s'ha pogut preparar (per exemple, una ruta relativa sense URL base o un fitxer que no es pot descarregar).

Quan **cap contacte del grup ni cap fila del fitxer és apte** (o tots ja han rebut el correu en un enviament anterior), no es pot enviar, però sí simular: el log permet esbrinar per què s'ha descartat cadascun. En el mode gràfic, el botó **Enviar** queda desactivat; en el mode consola, l'aplicació només ofereix la simulació. A més, després d'una simulació, el mode gràfic només ofereix el botó **Enviar** si s'enviaria algun correu (per exemple, no l'ofereix si cap adjunt no es pot descarregar).

---

## Reprendre un enviament interromput

Si un enviament s'interromp a mitges (es tanca l'aplicació, es talla la connexió, s'apaga l'ordinador…), l'aplicació recorda a quins contactes ja se'ls ha programat el correu.

En tornar a preparar **la mateixa campanya** (mateix grup —o mateix fitxer, full i columna del correu—, plantilla, camp o columna de l'adjunt i mode d'hora d'inici —i, si els correus surten el dia de cada contacte, el mateix camp o columna de la data—, i **exactament el mateix assumpte**), en arribar al resum l'aplicació avisa que hi ha un enviament anterior incomplet i pregunta què cal fer:

- **Continuar**: només s'envia als contactes pendents. Els seus correus es programen a continuació dels de l'enviament anterior, sense solapar-s'hi.
- **No continuar**: es descarta l'enviament anterior i es torna a enviar a tots els contactes, inclosos els que ja l'han rebut.

### Possibles duplicats

Si la interrupció es produeix just mentre es programava un correu, o si Mensagia no arriba a respondre, l'aplicació no pot saber si aquell correu va quedar programat. En aquest cas el torna a programar, però avisa:

- En reprendre, l'avís indica el destinatari i la data i hora a revisar.
- En acabar, indica si hi ha un **possible duplicat** (el correu s'ha programat ara, però potser també abans) o un enviament **no confirmat**.

L'API de Mensagia no permet consultar els enviaments programats, així que aquesta comprovació s'ha de fer a mà al portal, eliminant la programació sobrant.

> El progrés es desa al fitxer `send_progress.json`, a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació). Quan un enviament acaba sense errors, la campanya s'esborra del fitxer. No l'eliminis mentre hi hagi un enviament pendent de reprendre.

---

## Memòria de seleccions (mode gràfic)

Després de cada enviament o simulació, l'aplicació desa els paràmetres escollits
(origen dels destinataris, plantilla, remitent, grup, camp adjunt, carpeta de l'últim fitxer,
columnes del correu i de l'adjunt, camp o columna de la data i el seu format, certificat, i el mode i l'hora d'inici) en un fitxer
`last_selections.json`, a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació).

En la propera execució, aquestes opcions quedaran marcades per defecte. Les columnes només es marquen si
el fitxer nou té columnes amb aquests noms. El fitxer i el full no es recorden: el selector de
fitxer s'obre a la carpeta de l'últim que s'ha fet servir.

> Per esborrar aquesta memòria, elimina el fitxer `last_selections.json`.
> L'aplicació funciona amb normalitat si el fitxer no existeix.

---

## Idiomes de la interfície

La interfície detecta automàticament l'idioma del sistema operatiu.  
Idiomes disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar els executables

Els executables es generen automàticament amb GitHub Actions (`.github/workflows/build-release.yml`). El PyInstaller no pot compilar per a un altre sistema, així que cada versió es compila en una màquina del sistema corresponent: Windows, Mac amb Apple Silicon i Mac amb Intel.

- **En pujar un tag `vX.Y.Z`**, el workflow compila les tres versions i crea un **esborrany de release** amb els sis fitxers adjunts. Després es redacten les notes i es publica. Els executables porten el número de versió del tag, que fa servir l'[avís de versió nova](#avís-de-versió-nova).
- **A mà**, des de la pestanya **Actions** → **Run workflow**, compila les tres versions sense crear cap release i deixa els fitxers per descarregar a la mateixa execució (apartat **Artifacts**). Aquests executables tenen la versió `dev` i no avisen de versions noves.

> Si la compilació per a Mac amb Intel falla perquè GitHub ja ha retirat aquestes màquines, l'esborrany de release es crea igualment amb els fitxers de Windows i d'Apple Silicon.

---

## Executar els tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Estructura del projecte

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entitats i ports (interfícies)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Lògica de calendarització
│   ├── application/
│   │   └── use_cases/      # Casos d'ús
│   └── infrastructure/
│       ├── api/             # Client i adaptadors de la API Mensagia
│       ├── config/          # Càrrega de configuració (.env)
│       ├── files/           # Lectura de fitxers Excel i CSV
│       ├── logging/         # Escriptura dels logs d'enviament
│       ├── persistence/     # Desament del progrés dels enviaments
│       ├── recipients/      # Orígens dels destinataris (agenda o fitxer)
│       └── ui/
│           ├── console/     # Interfície de consola
│           ├── gui/         # Interfície gràfica (customtkinter)
│           └── locales/     # Traduccions
├── tests/
├── main.py                 # Punt d'entrada consola
├── main_gui.py             # Punt d'entrada gràfic
├── .github/workflows/      # Compilació dels executables (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
