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

## Aviso de versión nueva

Al arrancar, la aplicación comprueba si se ha publicado una versión más reciente en la [página de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest). Si la hay, muestra un aviso discreto con el número de la versión nueva y el enlace para descargarla:

- **Modo gráfico:** en la parte inferior de la primera pantalla (la del token). Haz clic en el enlace para abrir la página de descargas.
- **Modo consola:** una línea antes de pedir el asunto.

La aplicación solo avisa: no descarga ni instala nada. Para actualizarla, descarga la versión nueva como se explica en [Uso del ejecutable](#uso-del-ejecutable-clientes-sin-python) y sustituye la anterior. En Windows, pon el `.exe` nuevo en la misma carpeta para conservar los archivos de la [carpeta de datos](#archivos-de-la-aplicación).

Si no hay conexión o GitHub no responde en 3 segundos, no se muestra nada y la aplicación funciona con normalidad.

Para desactivar la comprobación, añade esta línea al archivo `.env`:

```
MENSAGIA_CHECK_UPDATES=false
```

> Desde el código fuente la aplicación no conoce su número de versión y no comprueba nada. Para probar el aviso, crea el archivo `src/build_version.py` con una versión anterior a la última publicada, por ejemplo `VERSION = "v1.3.0"`, y bórralo al terminar. Git ignora este archivo, así que nunca se sube al repositorio.

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
2. **Asunto, hora de inicio y origen** — El usuario introduce el asunto del correo, elige cuándo salen los correos: ahora, en una fecha y hora concretas o el día de cada contacto (ver [Programar la hora de inicio](#programar-la-hora-de-inicio)) y de dónde salen los destinatarios: un **grupo de la agenda** o un **fichero** (ver [Enviar a los destinatarios de un fichero](#enviar-a-los-destinatarios-de-un-fichero)). El asunto puede incluir campos personalizados o columnas (ver [Asunto con campos personalizados o columnas](#asunto-con-campos-personalizados-o-columnas)).
3. **Plantilla** — Se muestra la lista de plantillas de email disponibles.
4. **Remitente** — Se muestra la lista de direcciones de envío verificadas.
5. **Grupo o fichero**:
   - Con la agenda, se muestra una primera página de grupos. Si el grupo buscado no aparece, se puede filtrar por nombre. Los grupos sin contactos se muestran, pero no se pueden seleccionar.
   - Con un fichero, se elige el fichero y, si es un Excel con varias hojas, la hoja.
6. **Campo adjunto o columnas**:
   - Con la agenda, se elige qué campo personalizado contiene la URL del adjunto. Si los correos salen el día de cada contacto, a continuación se elige el campo con la fecha y su formato.
   - Con un fichero, se elige qué columna contiene el correo y cuál el adjunto. Si los correos salen el día de cada contacto, también la columna con la fecha y su formato.
7. **Certificado** — El usuario decide si certificar los envíos.
8. **Envío** — Se descartan los destinatarios sin correo válido, sin adjunto o con un campo del asunto vacío, y se envía un correo por cada uno a razón de 5/minuto.

---

## Ruta del adjunto en el campo personalizado

El campo personalizado elegido en el paso 6 (o la columna del adjunto, si los destinatarios salen de un fichero) puede indicar el adjunto de cada contacto de dos formas:

- **URL completa**, que empieza por `http://` o `https://` (por ejemplo, `https://cdn.empresa.com/docs/factura_42.pdf`). Se usa tal cual.
- **Nombre de archivo o ruta relativa** (por ejemplo, `factura_42.pdf` o `2026/factura_42.pdf`). La aplicación le antepone una **URL base**: con la base `https://cdn.empresa.com/docs/`, el valor `factura_42.pdf` se convierte en `https://cdn.empresa.com/docs/factura_42.pdf`.

Las dos formas se pueden combinar dentro del mismo grupo o fichero.

La URL base se puede indicar de varias maneras:

- En el archivo `.env`, con la variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- En el **modo gráfico**, en el campo **URL base adjuntos** de la primera pantalla. Si está definida en el `.env`, aparece ya rellenada.
- En el **modo consola**, la aplicación la pide solo si algún contacto tiene una ruta relativa y la variable no está en el `.env`.

> La URL base debe ser siempre una **dirección web pública**, nunca una carpeta del ordenador: es Mensagia quien descarga el archivo para adjuntarlo al correo. Puede terminar en `/` o no; la aplicación lo tiene en cuenta.

---

## Enviar a los destinatarios de un fichero

Además de un grupo de la agenda, los destinatarios pueden salir de un fichero **Excel (`.xlsx`)** o **CSV (`.csv`)**. Cada fila del fichero es un correo, de modo que una misma dirección puede recibir varios correos con adjuntos distintos en el mismo envío (por ejemplo, una agencia que recibe la documentación de varios de sus clientes). Los destinatarios no tienen que estar en la agenda de Mensagia.

### Cómo debe ser el fichero

- **La primera fila es la cabecera** y es obligatoria: contiene el nombre de cada columna.
- Los nombres, el orden y el número de columnas son libres. Al preparar el envío se elige qué columna contiene el correo y cuál el adjunto; las demás solo se usan si el [asunto](#asunto-con-campos-personalizados-o-columnas) las incluye.
- Las filas y las columnas completamente vacías se ignoran.
- Si el Excel tiene varias hojas, se elige cuál usar. Si solo tiene una, no se pregunta.
- En los CSV, el separador (`;` o `,`) y la codificación (UTF-8 o la de Windows) se detectan automáticamente.

Ejemplo:

| Cliente | Correo | Adjunto |
|---|---|---|
| Cliente A | agencia@ejemplo.com | facturas/cliente_a.pdf |
| Cliente B | agencia@ejemplo.com | facturas/cliente_b.pdf |
| Cliente C | info@clientec.com | https://cdn.empresa.com/docs/c.pdf |

La aplicación no deja continuar si:

- el fichero está vacío o solo tiene la cabecera;
- alguna columna tiene datos pero no tiene nombre en la cabecera;
- hay dos columnas con el mismo nombre (sin distinguir mayúsculas);
- alguna celda de la primera fila contiene `@`: probablemente el fichero no tiene cabecera.

### Correo y adjunto de cada fila

- **Correo**: se eliminan los espacios del principio y del final. Debe contener una sola dirección: una sola `@`; antes de la `@`, solo letras sin acentos, números y `. _ % + -`; después, letras sin acentos, números, `-` y al menos un punto. Una celda con varias direcciones no es válida.
- **Adjunto**: como en el campo personalizado, una URL completa o una ruta relativa a la URL base (ver [Ruta del adjunto](#ruta-del-adjunto-en-el-campo-personalizado)). Los números se leen sin decimales (`1234`, no `1234.0`).

Se descartan estas filas, y el [log](#simular-un-envío) indica el motivo:

- sin correo (`no_email`) o con un correo no válido (`invalid_email`);
- sin adjunto (`no_attachment`);
- con el mismo correo (sin distinguir mayúsculas) y el mismo adjunto que una fila anterior (`duplicate_row`): solo se envía la primera. Si los correos salen el día de cada contacto, también debe coincidir la fecha. Un nombre de archivo y la URL completa que se obtiene con la URL base cuentan como el mismo adjunto.

En el log, cada fila se identifica por su número tal como lo muestra Excel (la cabecera es la fila 1), el correo y el adjunto. Por ejemplo:

```
[SEND_SKIP]  row=14 to=agencia@ejemplo.com attachment=facturas/cliente_a.pdf reason=duplicate_row
```

### Cambios en el fichero

El fichero se vuelve a leer al llegar al resumen y al empezar el envío, así que se usan los cambios guardados mientras tanto. Si el fichero ya no se puede usar (por ejemplo, porque se ha cambiado el nombre de una columna elegida), la aplicación lo indica y no envía nada.

Para [reanudar un envío interrumpido](#reanudar-un-envío-interrumpido), un envío con fichero se identifica por el **nombre del fichero** (sin la carpeta), la hoja, las columnas elegidas, la plantilla, el asunto y el modo de hora de inicio. Por eso:

- Se puede mover el fichero a otra carpeta, corregir filas, añadir filas nuevas o cambiar su orden. Al reanudar, solo se envían las filas que faltaban, porque cada fila se reconoce por su correo y su adjunto.
- Si se cambia el nombre del fichero, la hoja o alguna de las columnas, se trata como un envío nuevo.

> En el modo consola, la ruta del fichero se escribe o se pega. Se aceptan las comillas que añade la opción «Copiar como ruta de acceso» de Windows.

---

## Asunto con campos personalizados o columnas

El asunto puede ser distinto para cada destinatario: basta con escribir en él el nombre de un campo personalizado (con la agenda) o de una columna (con un fichero) entre almohadillas, `#nombre#`, la misma notación que usa Mensagia. Por ejemplo:

| Asunto escrito | Datos del destinatario | Asunto que recibe |
|---|---|---|
| `Factura #num_factura# - #cliente#` | `num factura` = 123, `cliente` = ACME | `Factura 123 - ACME` |
| `#asunto#` | `asunto` = Documentación de octubre | `Documentación de octubre` |

Un asunto sin campos funciona como siempre: es el mismo para todos.

### Cómo se escribe un campo

- Un campo es todo lo que hay entre dos `#`, **sin espacios**. En `Pedido #12 y #34` no hay ningún campo, porque entre las dos almohadillas hay espacios.
- El nombre se relaciona con el campo o la columna **sin distinguir mayúsculas**, y un espacio en el nombre del campo o de la columna se escribe `_`. Por ejemplo, `#num_factura#` corresponde a una columna llamada `num factura`, `Num Factura` o `NUM_FACTURA`.
- Con la agenda, además de los campos personalizados se pueden usar tres campos básicos del contacto: `#email#` (la dirección de correo), `#name#` (el nombre) y `#number#` (el número de teléfono).
- La página del campo del adjunto (con la agenda) o de las columnas (con un fichero) muestra cómo se escribe cada uno, por ejemplo `num factura → #num_factura#`. En el modo consola, la lista aparece si el asunto tiene algún error.

### Errores y destinatarios descartados

- **Nombre que no existe** (por ejemplo, `#num_factur#`): la aplicación no deja continuar e indica el nombre. Se comprueba en la página del campo del adjunto o de las columnas, que es cuando se conocen los campos disponibles. En el modo gráfico hay que volver atrás hasta la página del asunto para corregirlo; en el modo consola, la aplicación vuelve a pedir el asunto.
- **Nombre ambiguo**: si dos campos o columnas se escriben igual en el asunto (por ejemplo, `num factura` y `num_factura`) y el asunto usa ese nombre, la aplicación no deja continuar.
- **Valor vacío**: el destinatario se descarta con el motivo «el campo X está vacío» (`empty_subject_field` en el log), porque el correo saldría con el asunto incompleto y un envío no se puede deshacer.

### Valores

- Se eliminan los espacios del principio y del final, y los saltos de línea se sustituyen por espacios.
- En Excel, los números enteros se escriben sin decimales (`123`, no `123.0`) y las fechas como `dd/mm/aaaa`.

### Resumen, log y reanudación

- El resumen muestra el asunto tal como se ha escrito y, como ejemplo, el asunto que recibirá el primer destinatario.
- En el log, cada correo enviado (o que se enviaría, en una simulación) incluye su asunto final:
  ```
  [SEND_OK]    row=2 to=agencia@ejemplo.com attachment=https://cdn.empresa.com/docs/a.pdf start_date=2026-10-15T09:00:00 subject="Factura 123 - ACME"
  ```
- Para [reanudar un envío interrumpido](#reanudar-un-envío-interrumpido), el envío se identifica por el asunto **tal como se ha escrito** (`Factura #num_factura#`). Corregir el valor de un destinatario no lo convierte en un envío nuevo.

---

## ⚠ Aviso sobre los contactos del grupo

El grupo se usa como **fuente de contactos**, no como lista de suscripción. La aplicación enviará el correo a **todos los contactos que pertenezcan al grupo**, estén suscritos a él o no.

> La API de Mensagia no proporciona información sobre el estado de suscripción de cada contacto en una agenda. Si deseas limitar el envío a los suscritos, deberás gestionar esa segmentación directamente en Mensagia antes de lanzar la aplicación.

---

## ⚠ Aviso importante sobre el envío

El programa **no envía los correos de forma inmediata**. Por cada contacto elegible crea una configuración de envío individual en la plataforma Mensagia, programada para ejecutarse de forma escalonada:

- El **primer envío** se ejecuta entre **10 y 20 minutos** después de lanzar el envío, para dar margen a cancelar si se detecta algún error, o en la fecha y hora elegidas (ver [Programar la hora de inicio](#programar-la-hora-de-inicio)).
- Los **envíos siguientes** se espacian **12 segundos** entre sí (5 por minuto).

> **Si necesitas detener el envío una vez iniciado**, cerrar la aplicación detiene la creación de nuevas configuraciones, pero las que ya se han creado se enviarán igualmente: deberás eliminar cada una de forma individual desde el portal de Mensagia. No existe un botón de cancelación global. Más adelante podrás reanudar el envío (ver [Reanudar un envío interrumpido](#reanudar-un-envío-interrumpido)).
>
> Usa el modo **Simular** para revisar qué se enviaría sin crear ninguna configuración real.

---

## Programar la hora de inicio

En la página del asunto (en el modo consola, justo después del asunto) se elige cuándo salen los correos:

- **Ahora**: entre 10 y 20 minutos después de empezar el envío.
- **Día y hora concretos**: el primer correo sale en la fecha y hora indicadas, y los siguientes, cada 12 segundos. Los envíos pueden pasar de medianoche.
- **Día de cada contacto, a una hora concreta**: cada correo sale el día indicado en los datos del contacto, a la hora elegida (ver [Enviar cada correo el día del contacto](#enviar-cada-correo-el-día-del-contacto)).

La fecha y la hora se escriben siempre en el orden `dd/mm/aaaa` y `hh:mm`, sea cual sea el idioma. En el modo gráfico hay un campo para cada parte, y el cursor pasa solo al siguiente al completar uno. En el modo consola también se aceptan otras formas habituales (`8/10/26`, `8-10-2026`, `9h30`, `9`…), y con Intro se acepta el valor propuesto entre corchetes.

Límites:

- **Margen mínimo de 10 minutos.** Al pasar a la página siguiente, la fecha y la hora deben ser como mínimo 10 minutos posteriores a la hora actual.
- **Posposición automática.** Si, mientras se completan los demás pasos, la hora elegida deja de tener 10 minutos de margen, al empezar el envío se pospone automáticamente a la primera hora que lo cumpla, como con la opción «Ahora». La aplicación no avisa, pero el log del envío indica la hora elegida (`start_at`) y la del primer correo (`first_slot`). Los correos nunca salen antes de la hora elegida.
- **Como máximo, 6 semanas de antelación** desde el momento de preparar el envío.
- La simulación no comprueba la hora, solo los datos.

> ⚠ **Zona horaria.** La hora se envía a Mensagia sin zona horaria, y Mensagia la interpreta según la **«Zona horaria» configurada en el usuario de Mensagia** asociado al token. Comprueba que coincide con la del ordenador que ejecuta la aplicación: si no, los correos saldrán a una hora distinta de la elegida.

La aplicación propone la fecha de hoy y, como hora, la última elegida en el modo gráfico o, si no hay ninguna, la que correspondería a la opción «Ahora».

Para [reanudar un envío interrumpido](#reanudar-un-envío-interrumpido) hay que repetir exactamente las mismas opciones, incluido el modo de hora de inicio: si se cambia el modo, se trata como un envío nuevo. En cambio, cambiar la fecha o la hora no crea un envío nuevo: al reanudar, los correos continúan después del último programado, y la nueva hora solo se usa si ese momento ya no tiene 10 minutos de margen.

---

## Enviar cada correo el día del contacto

Con la opción **Día de cada contacto, a una hora concreta**, cada destinatario recibe el correo el día indicado en sus propios datos: en un campo personalizado (agenda) o en una columna (fichero). Solo se elige la hora, que es la misma para todos los días.

- Con la agenda, después del campo del adjunto se elige el campo con la fecha. No puede ser el mismo que el del adjunto.
- Con un fichero, en la página de columnas se elige también la columna con la fecha. No puede ser ninguna de las otras dos.

Cada día empieza a la hora elegida y añade 12 segundos por cada correo anterior **del mismo día**. Por ejemplo, con las 09:00, tres correos del 15/10 salen a las 09:00:00, 09:00:12 y 09:00:24, y uno del 16/10, a las 09:00:00.

| Fecha del contacto | Qué pasa |
|---|---|
| Un día futuro | Sale a la hora elegida de ese día |
| Hoy | A la hora elegida si faltan al menos 10 minutos; si no, como con «Ahora» (de 10 a 20 minutos después) |
| Un día pasado | Se descarta (`past_send_date`) |
| A más de 6 semanas | Se descarta (`send_date_too_far`) |
| Vacía | Se descarta (`no_send_date`) |
| Con otro formato | Se descarta (`invalid_send_date`) |
| Con hora | Se descarta (`send_date_has_time`) |

Por ejemplo, a las 10:07 y con la hora 10:00, los contactos de hoy salen a las 10:20:00, 10:20:12…, y los de los días siguientes, a las 10:00:00, 10:00:12… de su día.

- Los correos de un día pueden pasar de medianoche. El día siguiente no se desplaza, aunque durante un rato salgan más correos por minuto.
- Los días se programan en orden, del más cercano al más lejano.

### Formato de la fecha

Mensagia no indica el formato de sus campos de fecha, así que hay que elegirlo: `dd/mm/aaaa`, `dd-mm-aaaa`, `aaaa/mm/dd` o `aaaa-mm-dd`.

El orden y el separador deben coincidir con el formato elegido, pero los ceros son opcionales y el año puede tener 2 cifras: con `dd/mm/aaaa`, `3/4/26` es el 3 de abril de 2026. Una fecha con hora (`15/10/2026 10:00`) se descarta.

En un fichero, el formato solo se aplica a las fechas escritas como texto (en un CSV, o en un Excel con la celda en formato de texto). Las celdas que Excel ya reconoce como fecha se leen directamente; si tienen una hora distinta de 00:00, se descartan.

### Resumen previo

Antes de enviar, el resumen muestra:

- una tabla con una fila por día, con el número de correos y la hora aproximada del primero y del último;
- los descartados, agrupados por motivo (el detalle de cada uno está en el log);
- con un fichero, las filas que enviarán el mismo adjunto a la misma dirección en fechas distintas. Se envían todas; si alguna sobra, se puede eliminar desde el portal de Mensagia.

Las horas son orientativas: la hora definitiva de cada correo se calcula al programarlo.

### Reanudar

Cada día se reanuda por separado: continúa después del último correo programado de ese día o, si no tenía ninguno, a la hora elegida (hoy, solo si faltan al menos 10 minutos). Los contactos pendientes de días que ya han pasado se descartan. El campo o la columna de la fecha forman parte del envío: si se cambian, es un envío nuevo.

---

## Simular un envío

El botón **Simular** (en el modo consola, la respuesta `Sim`) hace todas las comprobaciones de un envío real (contactos aptos, URL de los adjuntos y que se puedan descargar), pero **no programa ningún correo** en Mensagia ni modifica el progreso guardado para [reanudar un envío](#reanudar-un-envío-interrumpido).

Cada simulación genera un log con el mismo contenido que el de un envío real: los contactos a los que se enviaría el correo y los descartados, con el motivo. Al terminar, la aplicación muestra la ruta del archivo.

- Los logs se guardan en la carpeta `logs/` de la [carpeta de datos de la aplicación](#archivos-de-la-aplicación).
- Los de las simulaciones se llaman `mensagia_simulation_<fecha_hora>.log`, y los de los envíos reales, `mensagia_send_<fecha_hora>.log`. Si ordenas la carpeta por nombre, quedan separados.
- La primera línea de un log de simulación es `[SIMULATION] This is a simulation: no email was sent.` En él, las líneas `[SEND_OK]` son los correos que se enviarían.

Motivos de descarte (`reason=` en las líneas `[SEND_SKIP]`):

- `no_email`: el contacto o la fila no tiene dirección de correo.
- `invalid_email`: la dirección de correo de la fila no es válida (solo con un fichero).
- `no_attachment`: el campo personalizado o la columna del adjunto está vacío.
- `duplicate_row`: la fila repite el correo y el adjunto de una fila anterior (solo con un fichero).
- `already_sent`: el destinatario ya recibió el correo en un envío anterior interrumpido de la misma campaña.
- `no_send_date`, `invalid_send_date` y `send_date_has_time`: la fecha del contacto está vacía, no tiene el formato elegido o contiene una hora (ver [Enviar cada correo el día del contacto](#enviar-cada-correo-el-día-del-contacto)).
- `past_send_date` y `send_date_too_far`: la fecha del contacto ya ha pasado o está a más de 6 semanas.
- `empty_subject_field`: un campo personalizado o una columna que usa el asunto está vacío; `field=` indica cuál (ver [Asunto con campos personalizados o columnas](#asunto-con-campos-personalizados-o-columnas)).

Las líneas `[SEND_OK]` indican también la fecha y la hora para las que se ha programado cada correo (`start_date`), para encontrarlo en el portal de Mensagia, y el asunto con el que sale (`subject`). El resumen previo muestra los descartados agrupados por motivo.

Las líneas `[SEND_ERROR]` corresponden a contactos aptos cuyo adjunto no se ha podido preparar (por ejemplo, una ruta relativa sin URL base o un archivo que no se puede descargar).

Cuando **ningún contacto del grupo o fila del fichero es apto** (o todos recibieron ya el correo en un envío anterior), no se puede enviar, pero sí simular: el log permite averiguar por qué se ha descartado cada uno. En el modo gráfico, el botón **Enviar** queda desactivado; en el modo consola, la aplicación solo ofrece la simulación. Además, tras una simulación, el modo gráfico solo ofrece el botón **Enviar** si se enviaría algún correo (por ejemplo, no lo ofrece si ningún adjunto se puede descargar).

---

## Reanudar un envío interrumpido

Si un envío se interrumpe a medias (se cierra la aplicación, se corta la conexión, se apaga el ordenador…), la aplicación recuerda a qué contactos ya se les ha programado el correo.

Al volver a preparar **la misma campaña** (mismo grupo —o mismo fichero, hoja y columna del correo—, plantilla, campo o columna del adjunto y modo de hora de inicio —y, si los correos salen el día de cada contacto, el mismo campo o columna de la fecha—, y **exactamente el mismo asunto** tal como se ha escrito, con sus campos `#nombre#`), al llegar al resumen la aplicación avisa de que hay un envío anterior incompleto y pregunta qué hacer:

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
(origen de los destinatarios, plantilla, remitente, grupo, campo adjunto, carpeta del último fichero,
columnas del correo y del adjunto, campo o columna de la fecha y su formato, certificado, y el modo y la hora de inicio) en un archivo
`last_selections.json`, en la [carpeta de datos de la aplicación](#archivos-de-la-aplicación).

En la siguiente ejecución, esas opciones quedarán marcadas por defecto. Las columnas solo se marcan si
el fichero nuevo tiene columnas con esos nombres. El fichero y la hoja no se recuerdan: el selector de
fichero se abre en la carpeta del último usado.

> Para borrar esta memoria, elimina el archivo `last_selections.json`.
> La aplicación funciona con normalidad si el archivo no existe.

---

## Idiomas de la interfaz

La interfaz detecta automáticamente el idioma del sistema operativo.  
Idiomas disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar los ejecutables

Los ejecutables se generan automáticamente con GitHub Actions (`.github/workflows/build-release.yml`). PyInstaller no puede compilar para otro sistema, así que cada versión se compila en una máquina del sistema correspondiente: Windows, Mac con Apple Silicon y Mac con Intel.

- **Al subir un tag `vX.Y.Z`**, el workflow compila las tres versiones y crea un **borrador de release** con los seis archivos adjuntos. Después se redactan las notas y se publica. Los ejecutables llevan el número de versión del tag, que usa el [aviso de versión nueva](#aviso-de-versión-nueva).
- **A mano**, desde la pestaña **Actions** → **Run workflow**, compila las tres versiones sin crear ninguna release y deja los archivos para descargar en la propia ejecución (apartado **Artifacts**). Estos ejecutables tienen la versión `dev` y no avisan de versiones nuevas.

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
│       ├── files/           # Lectura de ficheros Excel y CSV
│       ├── logging/         # Escritura de los logs de envío
│       ├── persistence/     # Guardado del progreso de envíos
│       ├── recipients/      # Orígenes de los destinatarios (agenda o fichero)
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
