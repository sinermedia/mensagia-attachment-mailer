# Mensagia Attachment Mailer

Aplicación para enviar correos electrónicos con adjuntos personalizados por contacto usando la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versiones: [Català](docs/README.ca.md) · [Galego](docs/README.gl.md) · [Euskera](docs/README.eu.md) · [English](docs/README.en.md)

---

## Requisitos

- Windows 10/11 (para el ejecutable)
- O Python 3.11+ (para ejecutar desde el código fuente)

---

## Uso del ejecutable (clientes sin Python)

1. Descarga el ejecutable desde la [página de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) (`mensagia-mailer-gui.exe` para modo gráfico, o `mensagia-mailer-console.exe` para modo consola)
2. Crea un archivo `.env` en la **misma carpeta** que el `.exe` con tu token:

```
MENSAGIA_API_TOKEN=tu_token_api_aqui
```

> Puedes obtener tu token API en [mensagia.com](https://mensagia.com) → Usuarios.
> Si no existe el archivo `.env`, la aplicación te pedirá el token al arrancar.

3. Ejecuta el `.exe`.

> **Aviso de Windows SmartScreen:** la primera vez que ejecutes el archivo, Windows puede mostrar una advertencia de seguridad. Haz clic en **"Más información"** y luego en **"Ejecutar de todos modos"**. Solo es necesario hacerlo una vez por cada versión descargada.

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

> El progreso se guarda en el archivo `send_progress.json`, en la misma carpeta que el `.env` o el `.exe`. Cuando un envío termina sin errores, la campaña se borra del archivo. No lo elimines mientras haya un envío pendiente de reanudar.

---

## Memoria de selecciones (modo gráfico)

Tras cada envío o simulación, la aplicación guarda los parámetros elegidos
(plantilla, remitente, grupo, campo adjunto y certificado) en un archivo
`last_selections.json`, en la misma carpeta que el `.env` o el `.exe`.

En la siguiente ejecución, esas opciones quedarán marcadas por defecto.

> Para borrar esta memoria, elimina el archivo `last_selections.json`.
> La aplicación funciona con normalidad si el archivo no existe.

---

## Idiomas de la interfaz

La interfaz detecta automáticamente el idioma del sistema operativo.  
Idiomas disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar el ejecutable

Requiere las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

Ejecuta el script de compilación:

```bash
build.bat
```

Los archivos `.exe` se generan en la carpeta `dist/`.

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
├── build.bat               # Script de compilación a .exe
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
