# Mensagia Attachment Mailer

Aplicación para enviar correos electrónicos con adxuntos personalizados por contacto usando a [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versións: [Español](../README.md) · [Català](README.ca.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisitos

- Windows 10/11 ou macOS (para os executables)
- Ou Python 3.11+ (para executar dende o código fonte)

---

## Uso do executable (clientes sen Python)

Descarga a versión para o teu ordenador dende a [páxina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Ordenador | Modo gráfico | Modo consola |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Mac con Apple Silicon (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Mac con procesador Intel | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### Token API

A aplicación necesita o teu token API de Mensagia, que podes obter en [mensagia.com](https://mensagia.com) → Usuarios. Se non o tes configurado, pedirache o token ao arrancar. Para non ter que introducilo cada vez, gárdao nun ficheiro `.env` no [cartafol de datos da aplicación](#ficheiros-da-aplicación):

```
MENSAGIA_API_TOKEN=o_teu_token_api_aqui
```

### Windows

1. Descarga o `.exe`. A aplicación garda os seus ficheiros no mesmo cartafol, así que convén poñelo nun cartafol propio.
2. Opcionalmente, crea o ficheiro `.env` nese **mesmo cartafol**.
3. Executa o `.exe`.

> **Aviso de Windows SmartScreen:** a primeira vez que executes o ficheiro, Windows pode mostrar un aviso de seguridade. Fai clic en **"Máis información"** e logo en **"Executar de todos modos"**. Só é necesario facelo unha vez por cada versión descargada.

### macOS

> macOS non está dispoñible en galego: os nomes dos menús que aparecen aquí son os da versión en castelán.

1. **Escolle a versión do teu Mac.** Abre o menú Apple → **Acerca de este Mac**:
   - Se aparece **Chip** (Apple M1, M2, M3…), descarga a versión `apple-silicon`.
   - Se aparece **Procesador** (Intel…), descarga a versión `intel`.

   > GitHub está a retirar as máquinas que compilan para Mac con Intel. Se a última versión non inclúe os ficheiros `intel`, descárgaos da versión máis recente que os teña na [lista de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Fai dobre clic no `.zip` para descomprimilo (Safari pode facelo automaticamente ao descargalo). En modo gráfico obterás `mensagia-mailer-gui.app`, que podes mover a **Aplicaciones**.
3. Opcionalmente, garda o ficheiro `.env` no cartafol **Mensagia Mailer** do teu cartafol persoal. Podes crear ambos dende o Terminal:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=o_teu_token_api_aqui" > ~/"Mensagia Mailer/.env"
   ```

   > O Finder oculta os ficheiros cuxo nome comeza por un punto, como `.env`. Preme **Cmd + Maiús + .** para amosalos ou ocultalos.

4. Abre a aplicación. A primeira vez, macOS bloqueará a aplicación porque non está asinada por Apple (é o equivalente ao aviso de SmartScreen de Windows). Para permitila:
   - **macOS 15 (Sequoia) ou posterior:** despois do aviso, abre **Ajustes del Sistema → Privacidad y seguridad**, baixa ata a mensaxe sobre a aplicación e preme **Abrir igualmente**. Volve abrila e confírmao.
   - **macOS 14 ou anterior:** fai clic dereito sobre a aplicación → **Abrir**, e confírmao no aviso.
   - **En calquera versión, dende o Terminal:** `xattr -cr` seguido da ruta da aplicación, por exemplo `xattr -cr /Applications/mensagia-mailer-gui.app`.

   Só é necesario facelo unha vez por cada versión descargada.

> A versión de consola ábrese con dobre clic e funciona dentro dunha xanela do Terminal.

---

## Ficheiros da aplicación

A aplicación garda os seus ficheiros nun cartafol de datos, que depende de como se execute:

| Execución | Cartafol de datos |
|---|---|
| Windows (`.exe`) | O mesmo cartafol que o `.exe` |
| macOS | `Mensagia Mailer`, dentro do teu cartafol persoal (`~/Mensagia Mailer`) |
| Código fonte | A raíz do proxecto |

Nese cartafol atópanse:

- `.env`: a configuración (token API, idioma, URL base dos adxuntos…). Créalo ti e é opcional.
- `logs/`: un rexistro de cada envío e de cada simulación (ver [Simular un envío](#simular-un-envío)).
- `last_selections.json`: as últimas opcións escollidas (ver [Memoria de seleccións](#memoria-de-seleccións-modo-gráfico)).
- `send_progress.json`: o progreso dos envíos (ver [Retomar un envío interrompido](#retomar-un-envío-interrompido)).

A aplicación crea o cartafol e os ficheiros a medida que os necesita.

---

## Uso dende o código fonte

### Instalación

```bash
# Clonar o repositorio
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Crear contorno virtual (se non existe)
python -m venv .venv

# Activar o contorno
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### Configurar o token API

Crea un ficheiro `.env` na raíz do proxecto (copia de `.env.example`):

```
MENSAGIA_API_TOKEN=o_teu_token_api_aqui
```

### Executar modo gráfico

```bash
python main_gui.py
```

### Executar modo consola

```bash
python main.py
```

---

## Fluxo de envío

1. **Token API** — Lese do `.env` ou solicítase ao usuario.
2. **Asunto, hora de inicio e orixe** — O usuario introduce o asunto do correo, escolle cando saen os correos: agora, nunha data e hora concretas ou o día de cada contacto (ver [Programar a hora de inicio](#programar-a-hora-de-inicio)) e de onde saen os destinatarios: un **grupo da axenda** ou un **ficheiro** (ver [Enviar aos destinatarios dun ficheiro](#enviar-aos-destinatarios-dun-ficheiro)).
3. **Modelo** — Móstrase a lista de modelos de email dispoñibles.
4. **Remitente** — Móstrase a lista de enderezos de envío verificados.
5. **Grupo ou ficheiro**:
   - Coa axenda, móstrase unha primeira páxina de grupos. Se o grupo buscado non aparece, pódese filtrar polo nome. Os grupos sen contactos móstranse, pero non se poden seleccionar.
   - Cun ficheiro, elíxese o ficheiro e, se é un Excel con varias follas, a folla.
6. **Campo adxunto ou columnas**:
   - Coa axenda, elíxese que campo personalizado contén a URL do adxunto. Se os correos saen o día de cada contacto, a continuación elíxese o campo coa data e o seu formato.
   - Cun ficheiro, elíxese que columna contén o correo e cal o adxunto. Se os correos saen o día de cada contacto, tamén a columna coa data e o seu formato.
7. **Certificado** — O usuario decide se certificar os envíos.
8. **Envío** — Descártanse os destinatarios sen un correo válido ou sen adxunto, e envíase un correo por cada un a razón de 5/minuto.

---

## Ruta do adxunto no campo personalizado

O campo personalizado escollido no paso 6 (ou a columna do adxunto, se os destinatarios saen dun ficheiro) pode indicar o adxunto de cada contacto de dúas formas:

- **URL completa**, que comeza por `http://` ou `https://` (por exemplo, `https://cdn.empresa.com/docs/factura_42.pdf`). Úsase tal cal.
- **Nome de arquivo ou ruta relativa** (por exemplo, `factura_42.pdf` ou `2026/factura_42.pdf`). A aplicación antepónlle unha **URL base**: coa base `https://cdn.empresa.com/docs/`, o valor `factura_42.pdf` convértese en `https://cdn.empresa.com/docs/factura_42.pdf`.

As dúas formas pódense combinar dentro do mesmo grupo ou ficheiro.

A URL base pódese indicar de varias maneiras:

- No arquivo `.env`, coa variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- No **modo gráfico**, no campo **URL base adxuntos** da primeira pantalla. Se está definida no `.env`, aparece xa cuberta.
- No **modo consola**, a aplicación pídea só se algún contacto ten unha ruta relativa e a variable non está no `.env`.

> A URL base debe ser sempre un **enderezo web público**, nunca un cartafol do ordenador: é Mensagia quen descarga o arquivo para adxuntalo ao correo. Pode rematar en `/` ou non; a aplicación teno en conta.

---

## Enviar aos destinatarios dun ficheiro

Ademais dun grupo da axenda, os destinatarios poden saír dun ficheiro **Excel (`.xlsx`)** ou **CSV (`.csv`)**. Cada fila do ficheiro é un correo, de modo que un mesmo enderezo pode recibir varios correos con adxuntos distintos no mesmo envío (por exemplo, unha axencia que recibe a documentación de varios dos seus clientes). Os destinatarios non teñen que estar na axenda de Mensagia.

### Como debe ser o ficheiro

- **A primeira fila é a cabeceira** e é obrigatoria: contén o nome de cada columna.
- Os nomes, a orde e o número de columnas son libres. Ao preparar o envío elíxese que columna contén o correo e cal o adxunto; as demais ignóranse.
- As filas e as columnas completamente baleiras ignóranse.
- Se o Excel ten varias follas, elíxese cal usar. Se só ten unha, non se pregunta.
- Nos CSV, o separador (`;` ou `,`) e a codificación (UTF-8 ou a de Windows) detéctanse automaticamente.

Exemplo:

| Cliente | Correo | Adxunto |
|---|---|---|
| Cliente A | axencia@exemplo.com | facturas/cliente_a.pdf |
| Cliente B | axencia@exemplo.com | facturas/cliente_b.pdf |
| Cliente C | info@clientec.com | https://cdn.empresa.com/docs/c.pdf |

A aplicación non deixa continuar se:

- o ficheiro está baleiro ou só ten a cabeceira;
- algunha columna ten datos pero non ten nome na cabeceira;
- hai dúas columnas co mesmo nome (sen distinguir maiúsculas);
- algunha cela da primeira fila contén `@`: probablemente o ficheiro non ten cabeceira.

### Correo e adxunto de cada fila

- **Correo**: elimínanse os espazos do principio e do final. Debe conter un só enderezo: unha soa `@`; antes da `@`, só letras sen acentos, números e `. _ % + -`; despois, letras sen acentos, números, `-` e polo menos un punto. Unha cela con varios enderezos non é válida.
- **Adxunto**: como no campo personalizado, unha URL completa ou unha ruta relativa á URL base (ver [Ruta do adxunto](#ruta-do-adxunto-no-campo-personalizado)). Os números lense sen decimais (`1234`, non `1234.0`).

Descártanse estas filas, e o [log](#simular-un-envío) indica o motivo:

- sen correo (`no_email`) ou cun correo non válido (`invalid_email`);
- sen adxunto (`no_attachment`);
- co mesmo correo (sen distinguir maiúsculas) e o mesmo adxunto que unha fila anterior (`duplicate_row`): só se envía a primeira. Se os correos saen o día de cada contacto, tamén debe coincidir a data. Un nome de arquivo e a URL completa que se obtén coa URL base contan como o mesmo adxunto.

No log, cada fila identifícase polo seu número tal como o mostra Excel (a cabeceira é a fila 1), o correo e o adxunto. Por exemplo:

```
[SEND_SKIP]  row=14 to=axencia@exemplo.com attachment=facturas/cliente_a.pdf reason=duplicate_row
```

### Cambios no ficheiro

O ficheiro vólvese ler ao chegar ao resumo e ao comezar o envío, así que se usan os cambios gardados mentres tanto. Se o ficheiro xa non se pode usar (por exemplo, porque se cambiou o nome dunha columna escollida), a aplicación indícao e non envía nada.

Para [retomar un envío interrompido](#retomar-un-envío-interrompido), un envío con ficheiro identifícase polo **nome do ficheiro** (sen o cartafol), a folla, as columnas escollidas, o modelo, o asunto e o modo de hora de inicio. Por iso:

- Pódese mover o ficheiro a outro cartafol, corrixir filas, engadir filas novas ou cambiar a súa orde. Ao retomar, só se envían as filas que faltaban, porque cada fila se recoñece polo seu correo e o seu adxunto.
- Se se cambia o nome do ficheiro, a folla ou algunha das columnas, trátase como un envío novo.

> No modo consola, a ruta do ficheiro escríbese ou pégase. Acéptanse as comiñas que engade a opción «Copiar como ruta de acceso» de Windows.

---

## ⚠ Aviso sobre os contactos do grupo

O grupo úsase como **fonte de contactos**, non como lista de subscrición. A aplicación enviará o correo a **todos os contactos que pertenzan ao grupo**, estean subscritos a el ou non.

> A API de Mensagia non proporciona información sobre o estado de subscrición de cada contacto nunha axenda. Se desexas limitar o envío aos subscritos, deberás xestionar esa segmentación directamente en Mensagia antes de lanzar a aplicación.

---

## ⚠ Aviso importante sobre o envío

O programa **non envía os correos de forma inmediata**. Por cada contacto elixible crea unha configuración de envío individual na plataforma Mensagia, programada para executarse de forma escalonada:

- O **primeiro envío** execútase entre **10 e 20 minutos** despois de lanzar o envío, para dar marxe a cancelar se se detecta algún erro, ou na data e hora escollidas (ver [Programar a hora de inicio](#programar-a-hora-de-inicio)).
- Os **envíos seguintes** espácianse **12 segundos** entre si (5 por minuto).

> **Se necesitas deter o envío unha vez iniciado**, pechar a aplicación detén a creación de novas configuracións, pero as que xa se crearon enviaranse igualmente: deberás eliminar cada unha de forma individual dende o portal de Mensagia. Non existe un botón de cancelación global. Máis adiante poderás retomar o envío (ver [Retomar un envío interrompido](#retomar-un-envío-interrompido)).
>
> Usa o modo **Simular** para revisar o que se enviaría sen crear ningunha configuración real.

---

## Programar a hora de inicio

Na páxina do asunto (no modo consola, xusto despois do asunto) escóllese cando saen os correos:

- **Agora**: entre 10 e 20 minutos despois de comezar o envío.
- **Día e hora concretos**: o primeiro correo sae na data e hora indicadas, e os seguintes, cada 12 segundos. Os envíos poden pasar da medianoite.
- **Día de cada contacto, a unha hora concreta**: cada correo sae o día indicado nos datos do contacto, á hora escollida (ver [Enviar cada correo o día do contacto](#enviar-cada-correo-o-día-do-contacto)).

A data e a hora escríbense sempre na orde `dd/mm/aaaa` e `hh:mm`, sexa cal sexa o idioma. No modo gráfico hai un campo para cada parte, e o cursor pasa só ao seguinte ao completar un. No modo consola tamén se aceptan outras formas habituais (`8/10/26`, `8-10-2026`, `9h30`, `9`…), e con Intro acéptase o valor proposto entre corchetes.

Límites:

- **Marxe mínima de 10 minutos.** Ao pasar á páxina seguinte, a data e a hora deben ser como mínimo 10 minutos posteriores á hora actual.
- **Aprazamento automático.** Se, mentres se completan os demais pasos, a hora escollida deixa de ter 10 minutos de marxe, ao comezar o envío apránzase automaticamente á primeira hora que a cumpra, como coa opción «Agora». A aplicación non avisa, pero o log do envío indica a hora escollida (`start_at`) e a do primeiro correo (`first_slot`). Os correos nunca saen antes da hora escollida.
- **Como máximo, 6 semanas de antelación** dende o momento de preparar o envío.
- A simulación non comproba a hora, só os datos.

> ⚠ **Fuso horario.** A hora envíase a Mensagia sen fuso horario, e Mensagia interprétaa segundo a **«Zona horaria» configurada no usuario de Mensagia** asociado ao token. Comproba que coincide coa do ordenador que executa a aplicación: se non, os correos sairán a unha hora distinta da escollida.

A aplicación propón a data de hoxe e, como hora, a última escollida no modo gráfico ou, se non hai ningunha, a que correspondería á opción «Agora».

Para [retomar un envío interrompido](#retomar-un-envío-interrompido) hai que repetir exactamente as mesmas opcións, incluído o modo de hora de inicio: se se cambia o modo, trátase como un envío novo. En cambio, cambiar a data ou a hora non crea un envío novo: ao retomalo, os correos continúan despois do último programado, e a nova hora só se usa se ese momento xa non ten 10 minutos de marxe.

---

## Enviar cada correo o día do contacto

Coa opción **Día de cada contacto, a unha hora concreta**, cada destinatario recibe o correo o día indicado nos seus propios datos: nun campo personalizado (axenda) ou nunha columna (ficheiro). Só se escolle a hora, que é a mesma para todos os días.

- Coa axenda, despois do campo do adxunto elíxese o campo coa data. Non pode ser o mesmo que o do adxunto.
- Cun ficheiro, na páxina de columnas elíxese tamén a columna coa data. Non pode ser ningunha das outras dúas.

Cada día comeza á hora escollida e engade 12 segundos por cada correo anterior **do mesmo día**. Por exemplo, coas 09:00, tres correos do 15/10 saen ás 09:00:00, 09:00:12 e 09:00:24, e un do 16/10, ás 09:00:00.

| Data do contacto | Que pasa |
|---|---|
| Un día futuro | Sae á hora escollida dese día |
| Hoxe | Á hora escollida se faltan polo menos 10 minutos; se non, como con «Agora» (de 10 a 20 minutos despois) |
| Un día pasado | Descártase (`past_send_date`) |
| A máis de 6 semanas | Descártase (`send_date_too_far`) |
| Baleira | Descártase (`no_send_date`) |
| Con outro formato | Descártase (`invalid_send_date`) |
| Con hora | Descártase (`send_date_has_time`) |

Por exemplo, ás 10:07 e coa hora 10:00, os contactos de hoxe saen ás 10:20:00, 10:20:12…, e os dos días seguintes, ás 10:00:00, 10:00:12… do seu día.

- Os correos dun día poden pasar da medianoite. O día seguinte non se despraza, aínda que durante un tempo saian máis correos por minuto.
- Os días prográmanse en orde, do máis próximo ao máis afastado.

### Formato da data

Mensagia non indica o formato dos seus campos de data, así que hai que escollelo: `dd/mm/aaaa`, `dd-mm-aaaa`, `aaaa/mm/dd` ou `aaaa-mm-dd`.

A orde e o separador deben coincidir co formato escollido, pero os ceros son opcionais e o ano pode ter 2 cifras: con `dd/mm/aaaa`, `3/4/26` é o 3 de abril de 2026. Unha data con hora (`15/10/2026 10:00`) descártase.

Nun ficheiro, o formato só se aplica ás datas escritas como texto (nun CSV, ou nun Excel coa cela en formato de texto). As celas que Excel xa recoñece como data lense directamente; se teñen unha hora distinta de 00:00, descártanse.

### Resumo previo

Antes de enviar, o resumo mostra:

- unha táboa cunha fila por día, co número de correos e a hora aproximada do primeiro e do último;
- os descartados, agrupados por motivo (o detalle de cada un está no log);
- cun ficheiro, as filas que enviarán o mesmo adxunto ao mesmo enderezo en datas distintas. Envíanse todas; se sobra algunha, pódese eliminar dende o portal de Mensagia.

As horas son orientativas: a hora definitiva de cada correo calcúlase ao programalo.

### Retomar

Cada día retómase por separado: continúa despois do último correo programado dese día ou, se non tiña ningún, á hora escollida (hoxe, só se faltan polo menos 10 minutos). Os contactos pendentes de días que xa pasaron descártanse. O campo ou a columna da data forman parte do envío: se se cambian, é un envío novo.

---

## Simular un envío

O botón **Simular** (no modo consola, a resposta `Sim`) fai todas as comprobacións dun envío real (contactos aptos, URL dos adxuntos e que se poidan descargar), pero **non programa ningún correo** en Mensagia nin modifica o progreso gardado para [retomar un envío](#retomar-un-envío-interrompido).

Cada simulación xera un log co mesmo contido ca o dun envío real: os contactos aos que se lles enviaría o correo e os descartados, co motivo. Ao rematar, a aplicación amosa a ruta do ficheiro.

- Os logs gárdanse no cartafol `logs/` do [cartafol de datos da aplicación](#ficheiros-da-aplicación).
- Os das simulacións chámanse `mensagia_simulation_<data_hora>.log`, e os dos envíos reais, `mensagia_send_<data_hora>.log`. Se ordenas o cartafol por nome, quedan separados.
- A primeira liña dun log de simulación é `[SIMULATION] This is a simulation: no email was sent.` Nel, as liñas `[SEND_OK]` son os correos que se enviarían.

Motivos de descarte (`reason=` nas liñas `[SEND_SKIP]`):

- `no_email`: o contacto ou a fila non ten enderezo de correo.
- `invalid_email`: o enderezo de correo da fila non é válido (só cun ficheiro).
- `no_attachment`: o campo personalizado ou a columna do adxunto está baleiro.
- `duplicate_row`: a fila repite o correo e o adxunto dunha fila anterior (só cun ficheiro).
- `already_sent`: o destinatario xa recibiu o correo nun envío anterior interrompido da mesma campaña.
- `no_send_date`, `invalid_send_date` e `send_date_has_time`: a data do contacto está baleira, non ten o formato escollido ou contén unha hora (ver [Enviar cada correo o día do contacto](#enviar-cada-correo-o-día-do-contacto)).
- `past_send_date` e `send_date_too_far`: a data do contacto xa pasou ou está a máis de 6 semanas.

As liñas `[SEND_OK]` indican tamén a data e a hora para as que se programou cada correo (`start_date`), para atopalo no portal de Mensagia. O resumo previo mostra os descartados agrupados por motivo.

As liñas `[SEND_ERROR]` corresponden a contactos aptos cuxo adxunto non se puido preparar (por exemplo, unha ruta relativa sen URL base ou un ficheiro que non se pode descargar).

Cando **ningún contacto do grupo nin ningunha fila do ficheiro é apto** (ou todos recibiron xa o correo nun envío anterior), non se pode enviar, pero si simular: o log permite saber por que se descartou cada un. No modo gráfico, o botón **Enviar** queda desactivado; no modo consola, a aplicación só ofrece a simulación. Ademais, despois dunha simulación, o modo gráfico só ofrece o botón **Enviar** se se enviaría algún correo (por exemplo, non o ofrece se ningún adxunto se pode descargar).

---

## Retomar un envío interrompido

Se un envío se interrompe a medias (péchase a aplicación, córtase a conexión, apágase o ordenador…), a aplicación lembra a que contactos xa se lles programou o correo.

Ao volver preparar **a mesma campaña** (mesmo grupo —ou mesmo ficheiro, folla e columna do correo—, modelo, campo ou columna do adxunto e modo de hora de inicio —e, se os correos saen o día de cada contacto, o mesmo campo ou columna da data—, e **exactamente o mesmo asunto**), ao chegar ao resumo a aplicación avisa de que hai un envío anterior incompleto e pregunta que facer:

- **Continuar**: só se envía aos contactos pendentes. Os seus correos prográmanse a continuación dos do envío anterior, sen solaparse con eles.
- **Non continuar**: descártase o envío anterior e vólvese enviar a todos os contactos, incluídos os que xa o recibiron.

### Posibles duplicados

Se a interrupción se produce xusto mentres se programaba un correo, ou se Mensagia non chega a responder, a aplicación non pode saber se ese correo quedou programado. Nese caso vólveo programar, pero avisa:

- Ao retomar, o aviso indica o destinatario e a data e hora que hai que revisar.
- Ao rematar, indica se hai un **posible duplicado** (o correo programouse agora, pero quizais tamén antes) ou un envío **non confirmado**.

A API de Mensagia non permite consultar os envíos programados, así que esta comprobación debe facerse a man no portal, eliminando a programación sobrante.

> O progreso gárdase no ficheiro `send_progress.json`, no [cartafol de datos da aplicación](#ficheiros-da-aplicación). Cando un envío remata sen erros, a campaña bórrase do ficheiro. Non o elimines mentres haxa un envío pendente de retomar.

---

## Memoria de seleccións (modo gráfico)

Tras cada envío ou simulación, a aplicación garda os parámetros escollidos
(orixe dos destinatarios, modelo, remitente, grupo, campo adxunto, cartafol do último ficheiro,
columnas do correo e do adxunto, campo ou columna da data e o seu formato, certificado, e o modo e a hora de inicio) nun ficheiro
`last_selections.json`, no [cartafol de datos da aplicación](#ficheiros-da-aplicación).

Na seguinte execución, esas opcións quedarán marcadas por defecto. As columnas só se marcan se
o ficheiro novo ten columnas con eses nomes. O ficheiro e a folla non se lembran: o selector de
ficheiro ábrese no cartafol do último usado.

> Para borrar esta memoria, elimina o ficheiro `last_selections.json`.
> A aplicación funciona con normalidade se o ficheiro non existe.

---

## Idiomas da interface

A interface detecta automaticamente o idioma do sistema operativo.  
Idiomas dispoñibles: **Español, Català, Galego, Euskera, English**.

---

## Xerar os executables

Os executables xéranse automaticamente con GitHub Actions (`.github/workflows/build-release.yml`). PyInstaller non pode compilar para outro sistema, así que cada versión se compila nunha máquina do sistema correspondente: Windows, Mac con Apple Silicon e Mac con Intel.

- **Ao subir un tag `vX.Y.Z`**, o workflow compila as tres versións e crea un **borrador de release** cos seis ficheiros adxuntos. Despois redáctanse as notas e publícase.
- **A man**, dende a lapela **Actions** → **Run workflow**, compila as tres versións sen crear ningunha release e deixa os ficheiros para descargar na propia execución (apartado **Artifacts**).

> Se a compilación para Mac con Intel falla porque GitHub xa retirou esas máquinas, o borrador de release créase igualmente cos ficheiros de Windows e de Apple Silicon.

---

## Executar os tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Estrutura do proxecto

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entidades e portos (interfaces)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Lóxica de calendarización
│   ├── application/
│   │   └── use_cases/      # Casos de uso
│   └── infrastructure/
│       ├── api/             # Cliente e adaptadores da API Mensagia
│       ├── config/          # Carga de configuración (.env)
│       ├── files/           # Lectura de ficheiros Excel e CSV
│       ├── logging/         # Escritura dos logs de envío
│       ├── persistence/     # Gardado do progreso dos envíos
│       ├── recipients/      # Orixes dos destinatarios (axenda ou ficheiro)
│       └── ui/
│           ├── console/     # Interface de consola
│           ├── gui/         # Interface gráfica (customtkinter)
│           └── locales/     # Traducións
├── tests/
├── main.py                 # Punto de entrada consola
├── main_gui.py             # Punto de entrada gráfico
├── .github/workflows/      # Compilación dos executables (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
