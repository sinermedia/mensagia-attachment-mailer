# Mensagia Attachment Mailer

Aplicación para enviar correos electrónicos con adjuntos personalizados por contacto usando la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versiones: [Català](docs/README.ca.md) · [Galego](docs/README.gl.md) · [Euskera](docs/README.eu.md) · [English](docs/README.en.md)

---

## Requisitos

- Windows 10/11 o macOS (para los ejecutables)
- O Python 3.11+ (para ejecutar desde el código fuente)

---

## Uso del ejecutable (clientes sin Python)

Descarga la versión para tu ordenador desde la [página de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Ordenador | Modo gráfico | Modo consola |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Mac con Apple Silicon (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Mac con procesador Intel | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### Token API

La aplicación necesita tu token API de Mensagia, que puedes obtener en [mensagia.com](https://mensagia.com) → Usuarios. Si no lo tienes configurado, te lo pedirá al arrancar. Para no tener que introducirlo cada vez, guárdalo en un archivo `.env` en la [carpeta de datos de la aplicación](#archivos-de-la-aplicación):

```
MENSAGIA_API_TOKEN=tu_token_api_aqui
```

### Windows

1. Descarga el `.exe`. La aplicación guarda sus archivos en la misma carpeta, así que conviene ponerlo en una carpeta propia.
2. Opcionalmente, crea el archivo `.env` en esa **misma carpeta**.
3. Ejecuta el `.exe`.

> **Aviso de Windows SmartScreen:** la primera vez que ejecutes el archivo, Windows puede mostrar una advertencia de seguridad. Haz clic en **"Más información"** y luego en **"Ejecutar de todos modos"**. Solo es necesario hacerlo una vez por cada versión descargada.

### macOS

1. **Elige la versión de tu Mac.** Abre el menú Apple → **Acerca de este Mac**:
   - Si aparece **Chip** (Apple M1, M2, M3…), descarga la versión `apple-silicon`.
   - Si aparece **Procesador** (Intel…), descarga la versión `intel`.

   > GitHub está retirando las máquinas que compilan para Mac con Intel. Si la última versión no incluye los archivos `intel`, descárgalos de la versión más reciente que los tenga en la [lista de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Haz doble clic en el `.zip` para descomprimirlo (Safari puede hacerlo automáticamente al descargarlo). En modo gráfico obtendrás `mensagia-mailer-gui.app`, que puedes mover a **Aplicaciones**.
3. Opcionalmente, guarda el archivo `.env` en la carpeta **Mensagia Mailer** de tu carpeta personal. Puedes crear ambos desde el Terminal:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=tu_token_api_aqui" > ~/"Mensagia Mailer/.env"
   ```

   > El Finder oculta los archivos cuyo nombre empieza por un punto, como `.env`. Pulsa **Cmd + Mayús + .** para mostrarlos u ocultarlos.

4. Abre la aplicación. La primera vez, macOS la bloqueará porque no está firmada por Apple (es el equivalente al aviso de SmartScreen de Windows). Para permitirla:
   - **macOS 15 (Sequoia) o posterior:** después del aviso, abre **Ajustes del Sistema → Privacidad y seguridad**, baja hasta el mensaje sobre la aplicación y pulsa **Abrir igualmente**. Vuelve a abrirla y confírmalo.
   - **macOS 14 o anterior:** haz clic derecho sobre la aplicación → **Abrir**, y confírmalo en el aviso.
   - **En cualquier versión, desde el Terminal:** `xattr -cr` seguido de la ruta de la aplicación, por ejemplo `xattr -cr /Applications/mensagia-mailer-gui.app`.

   Solo es necesario hacerlo una vez por cada versión descargada.

> La versión de consola se abre con doble clic y funciona dentro de una ventana del Terminal.

---

## Archivos de la aplicación

La aplicación guarda sus archivos en una carpeta de datos, que depende de cómo se ejecute:

| Ejecución | Carpeta de datos |
|---|---|
| Windows (`.exe`) | La misma carpeta que el `.exe` |
| macOS | `Mensagia Mailer`, dentro de tu carpeta personal (`~/Mensagia Mailer`) |
| Código fuente | La raíz del proyecto |

En esa carpeta se encuentran:

- `.env`: la configuración (token API, idioma, URL base de los adjuntos…). Lo creas tú y es opcional.
- `logs/`: un registro de cada envío y de cada simulación (ver [Simular un envío](#simular-un-envío)).
- `last_selections.json`: las últimas opciones elegidas (ver [Memoria de selecciones](#memoria-de-selecciones-modo-gráfico)).
- `send_progress.json`: el progreso de los envíos (ver [Reanudar un envío interrumpido](#reanudar-un-envío-interrumpido)).

La aplicación crea la carpeta y los archivos a medida que los necesita.

---

## Uso desde el código fuente

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Crear entorno virtual (si no existe)
python -m venv .venv

# Activar el entorno
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### Configurar el token API

Crea un archivo `.env` en la raíz del proyecto (copia de `.env.example`):

```
MENSAGIA_API_TOKEN=tu_token_api_aqui
```

### Ejecutar modo gráfico

```bash
python main_gui.py
```

### Ejecutar modo consola

```bash
python main.py
```

---

## Flujo de envío

1. **Token API** — Se lee del `.env` o se solicita al usuario.
2. **Asunto** — El usuario introduce el asunto del correo.
3. **Plantilla** — Se muestra la lista de plantillas de email disponibles.
4. **Remitente** — Se muestra la lista de direcciones de envío verificadas.
5. **Grupo** — Se muestra una primera página de grupos de la agenda. Si el grupo buscado no aparece, se puede filtrar por nombre. Los grupos sin contactos se muestran, pero no se pueden seleccionar.
6. **Campo adjunto** — Se elige qué campo personalizado contiene la URL del adjunto.
7. **Certificado** — El usuario decide si certificar los envíos.
8. **Envío** — Se filtran los contactos con email y URL de adjunto válidos, y se envía un correo por cada uno a razón de 5/minuto.

---

## Ruta del adjunto en el campo personalizado

El campo personalizado elegido en el paso 6 puede indicar el adjunto de cada contacto de dos formas:

- **URL completa**, que empieza por `http://` o `https://` (por ejemplo, `https://cdn.empresa.com/docs/factura_42.pdf`). Se usa tal cual.
- **Nombre de archivo o ruta relativa** (por ejemplo, `factura_42.pdf` o `2026/factura_42.pdf`). La aplicación le antepone una **URL base**: con la base `https://cdn.empresa.com/docs/`, el valor `factura_42.pdf` se convierte en `https://cdn.empresa.com/docs/factura_42.pdf`.

Las dos formas se pueden combinar dentro del mismo grupo.

La URL base se puede indicar de varias maneras:

- En el archivo `.env`, con la variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- En el **modo gráfico**, en el campo **URL base adjuntos** de la primera pantalla. Si está definida en el `.env`, aparece ya rellenada.
- En el **modo consola**, la aplicación la pide solo si algún contacto tiene una ruta relativa y la variable no está en el `.env`.

> La URL base debe ser siempre una **dirección web pública**, nunca una carpeta del ordenador: es Mensagia quien descarga el archivo para adjuntarlo al correo. Puede terminar en `/` o no; la aplicación lo tiene en cuenta.

---

## ⚠ Aviso sobre los contactos del grupo

El grupo se usa como **fuente de contactos**, no como lista de suscripción. La aplicación enviará el correo a **todos los contactos que pertenezcan al grupo**, estén suscritos a él o no.

> La API de Mensagia no proporciona información sobre el estado de suscripción de cada contacto en una agenda. Si deseas limitar el envío a los suscritos, deberás gestionar esa segmentación directamente en Mensagia antes de lanzar la aplicación.

---

## ⚠ Aviso importante sobre el envío

El programa **no envía los correos de forma inmediata**. Por cada contacto elegible crea una configuración de envío individual en la plataforma Mensagia, programada para ejecutarse de forma escalonada:

- El **primer envío** se ejecuta entre **10 y 20 minutos** después de lanzar la aplicación, para dar margen a cancelar si se detecta algún error.
- Los **envíos siguientes** se espacian **12 segundos** entre sí (5 por minuto).

> **Si necesitas detener el envío una vez iniciado**, cerrar la aplicación detiene la creación de nuevas configuraciones, pero las que ya se han creado se enviarán igualmente: deberás eliminar cada una de forma individual desde el portal de Mensagia. No existe un botón de cancelación global. Más adelante podrás reanudar el envío (ver [Reanudar un envío interrumpido](#reanudar-un-envío-interrumpido)).
>
> Usa el modo **Simular** para revisar qué se enviaría sin crear ninguna configuración real.

---

## Simular un envío

El botón **Simular** (en el modo consola, la respuesta `Sim`) hace todas las comprobaciones de un envío real (contactos aptos, URL de los adjuntos y que se puedan descargar), pero **no programa ningún correo** en Mensagia ni modifica el progreso guardado para [reanudar un envío](#reanudar-un-envío-interrumpido).

Cada simulación genera un log con el mismo contenido que el de un envío real: los contactos a los que se enviaría el correo y los descartados, con el motivo. Al terminar, la aplicación muestra la ruta del archivo.

- Los logs se guardan en la carpeta `logs/` de la [carpeta de datos de la aplicación](#archivos-de-la-aplicación).
- Los de las simulaciones se llaman `mensagia_simulation_<fecha_hora>.log`, y los de los envíos reales, `mensagia_send_<fecha_hora>.log`. Si ordenas la carpeta por nombre, quedan separados.
- La primera línea de un log de simulación es `[SIMULATION] This is a simulation: no email was sent.` En él, las líneas `[SEND_OK]` son los correos que se enviarían.

Motivos de descarte (`reason=` en las líneas `[SEND_SKIP]`):

- `no_email`: el contacto no tiene dirección de correo.
- `no_attachment`: el campo personalizado del adjunto está vacío.
- `already_sent`: el contacto ya recibió el correo en un envío anterior interrumpido de la misma campaña.

Las líneas `[SEND_ERROR]` corresponden a contactos aptos cuyo adjunto no se ha podido preparar (por ejemplo, una ruta relativa sin URL base o un archivo que no se puede descargar).

Cuando **ningún contacto del grupo es apto** (o todos recibieron ya el correo en un envío anterior), no se puede enviar, pero sí simular: el log permite averiguar por qué se ha descartado cada contacto. En el modo gráfico, el botón **Enviar** queda desactivado; en el modo consola, la aplicación solo ofrece la simulación.

---

## Reanudar un envío interrumpido

Si un envío se interrumpe a medias (se cierra la aplicación, se corta la conexión, se apaga el ordenador…), la aplicación recuerda a qué contactos ya se les ha programado el correo.

Al volver a preparar **la misma campaña** (mismo grupo, plantilla y campo adjunto, y **exactamente el mismo asunto**), al llegar al resumen la aplicación avisa de que hay un envío anterior incompleto y pregunta qué hacer:

- **Continuar**: solo se envía a los contactos pendientes. Sus correos se programan a continuación de los del envío anterior, sin solaparse con ellos.
- **No continuar**: se descarta el envío anterior y se vuelve a enviar a todos los contactos, incluidos los que ya lo recibieron.

### Posibles duplicados

Si la interrupción se produce justo mientras se programaba un correo, o si Mensagia no llega a responder, la aplicación no puede saber si ese correo quedó programado. En ese caso lo vuelve a programar, pero avisa:

- Al reanudar, el aviso indica el destinatario y la fecha y hora a revisar.
- Al terminar, indica si hay un **posible duplicado** (el correo se ha programado ahora, pero quizá también antes) o un envío **no confirmado**.

La API de Mensagia no permite consultar los envíos programados, así que esta comprobación debe hacerse a mano en el portal, eliminando la programación sobrante.

> El progreso se guarda en el archivo `send_progress.json`, en la [carpeta de datos de la aplicación](#archivos-de-la-aplicación). Cuando un envío termina sin errores, la campaña se borra del archivo. No lo elimines mientras haya un envío pendiente de reanudar.

---

## Memoria de selecciones (modo gráfico)

Tras cada envío o simulación, la aplicación guarda los parámetros elegidos
(plantilla, remitente, grupo, campo adjunto y certificado) en un archivo
`last_selections.json`, en la [carpeta de datos de la aplicación](#archivos-de-la-aplicación).

En la siguiente ejecución, esas opciones quedarán marcadas por defecto.

> Para borrar esta memoria, elimina el archivo `last_selections.json`.
> La aplicación funciona con normalidad si el archivo no existe.

---

## Idiomas de la interfaz

La interfaz detecta automáticamente el idioma del sistema operativo.  
Idiomas disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar los ejecutables

Los ejecutables se generan automáticamente con GitHub Actions (`.github/workflows/build-release.yml`). PyInstaller no puede compilar para otro sistema, así que cada versión se compila en una máquina del sistema correspondiente: Windows, Mac con Apple Silicon y Mac con Intel.

- **Al subir un tag `vX.Y.Z`**, el workflow compila las tres versiones y crea un **borrador de release** con los seis archivos adjuntos. Después se redactan las notas y se publica.
- **A mano**, desde la pestaña **Actions** → **Run workflow**, compila las tres versiones sin crear ninguna release y deja los archivos para descargar en la propia ejecución (apartado **Artifacts**).

> Si la compilación para Mac con Intel falla porque GitHub ya ha retirado esas máquinas, el borrador de release se crea igualmente con los archivos de Windows y de Apple Silicon.

---

## Ejecutar los tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Estructura del proyecto

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entidades y puertos (interfaces)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Lógica de calendarización
│   ├── application/
│   │   └── use_cases/      # Casos de uso
│   └── infrastructure/
│       ├── api/             # Cliente y adaptadores de la API Mensagia
│       ├── config/          # Carga de configuración (.env)
│       ├── logging/         # Escritura de los logs de envío
│       ├── persistence/     # Guardado del progreso de envíos
│       └── ui/
│           ├── console/     # Interfaz de consola
│           ├── gui/         # Interfaz gráfica (customtkinter)
│           └── locales/     # Traducciones
├── tests/
├── main.py                 # Punto de entrada consola
├── main_gui.py             # Punto de entrada gráfico
├── .github/workflows/      # Compilación de los ejecutables (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
