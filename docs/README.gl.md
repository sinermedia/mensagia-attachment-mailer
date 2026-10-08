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
- `logs/`: un rexistro de cada envío.
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
2. **Asunto** — O usuario introduce o asunto do correo.
3. **Modelo** — Móstrase a lista de modelos de email dispoñibles.
4. **Remitente** — Móstrase a lista de enderezos de envío verificados.
5. **Grupo** — Móstrase unha primeira páxina de grupos da axenda. Se o grupo buscado non aparece, pódese filtrar polo nome. Os grupos sen contactos móstranse, pero non se poden seleccionar.
6. **Campo adxunto** — Elíxese que campo personalizado contén a URL do adxunto.
7. **Certificado** — O usuario decide se certificar os envíos.
8. **Envío** — Fíltrase os contactos con email e URL de adxunto válidos, e envíase un correo por cada un a razón de 5/minuto.

---

## Ruta do adxunto no campo personalizado

O campo personalizado escollido no paso 6 pode indicar o adxunto de cada contacto de dúas formas:

- **URL completa**, que comeza por `http://` ou `https://` (por exemplo, `https://cdn.empresa.com/docs/factura_42.pdf`). Úsase tal cal.
- **Nome de arquivo ou ruta relativa** (por exemplo, `factura_42.pdf` ou `2026/factura_42.pdf`). A aplicación antepónlle unha **URL base**: coa base `https://cdn.empresa.com/docs/`, o valor `factura_42.pdf` convértese en `https://cdn.empresa.com/docs/factura_42.pdf`.

As dúas formas pódense combinar dentro do mesmo grupo.

A URL base pódese indicar de varias maneiras:

- No arquivo `.env`, coa variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- No **modo gráfico**, no campo **URL base adxuntos** da primeira pantalla. Se está definida no `.env`, aparece xa cuberta.
- No **modo consola**, a aplicación pídea só se algún contacto ten unha ruta relativa e a variable non está no `.env`.

> A URL base debe ser sempre un **enderezo web público**, nunca un cartafol do ordenador: é Mensagia quen descarga o arquivo para adxuntalo ao correo. Pode rematar en `/` ou non; a aplicación teno en conta.

---

## ⚠ Aviso sobre os contactos do grupo

O grupo úsase como **fonte de contactos**, non como lista de subscrición. A aplicación enviará o correo a **todos os contactos que pertenzan ao grupo**, estean subscritos a el ou non.

> A API de Mensagia non proporciona información sobre o estado de subscrición de cada contacto nunha axenda. Se desexas limitar o envío aos subscritos, deberás xestionar esa segmentación directamente en Mensagia antes de lanzar a aplicación.

---

## ⚠ Aviso importante sobre o envío

O programa **non envía os correos de forma inmediata**. Por cada contacto elixible crea unha configuración de envío individual na plataforma Mensagia, programada para executarse de forma escalonada:

- O **primeiro envío** execútase entre **10 e 20 minutos** despois de lanzar a aplicación, para dar marxe a cancelar se se detecta algún erro.
- Os **envíos seguintes** espácianse **12 segundos** entre si (5 por minuto).

> **Se necesitas deter o envío unha vez iniciado**, pechar a aplicación detén a creación de novas configuracións, pero as que xa se crearon enviaranse igualmente: deberás eliminar cada unha de forma individual dende o portal de Mensagia. Non existe un botón de cancelación global. Máis adiante poderás retomar o envío (ver [Retomar un envío interrompido](#retomar-un-envío-interrompido)).
>
> Usa o modo **Simular** para revisar o que se enviaría sen crear ningunha configuración real.

---

## Retomar un envío interrompido

Se un envío se interrompe a medias (péchase a aplicación, córtase a conexión, apágase o ordenador…), a aplicación lembra a que contactos xa se lles programou o correo.

Ao volver preparar **a mesma campaña** (mesmo grupo, modelo e campo adxunto, e **exactamente o mesmo asunto**), ao chegar ao resumo a aplicación avisa de que hai un envío anterior incompleto e pregunta que facer:

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
(modelo, remitente, grupo, campo adxunto e certificado) nun ficheiro
`last_selections.json`, no [cartafol de datos da aplicación](#ficheiros-da-aplicación).

Na seguinte execución, esas opcións quedarán marcadas por defecto.

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
│       ├── logging/         # Escritura dos logs de envío
│       ├── persistence/     # Gardado do progreso dos envíos
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
