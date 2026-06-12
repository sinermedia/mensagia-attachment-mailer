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
5. **Grupo** — Se muestra la lista de grupos de la agenda.
6. **Campo adjunto** — Se elige qué campo personalizado contiene la URL del adjunto.
7. **Certificado** — El usuario decide si certificar los envíos.
8. **Envío** — Se filtran los contactos con email y URL de adjunto válidos, y se envía un correo por cada uno a razón de 5/minuto.

---

## ⚠ Aviso sobre los contactos del grupo

El grupo se usa como **fuente de contactos**, no como lista de suscripción. La aplicación enviará el correo a **todos los contactos que pertenezcan al grupo**, estén suscritos a él o no.

> La API de Mensagia no proporciona información sobre el estado de suscripción de cada contacto en una agenda. Si deseas limitar el envío a los suscritos, deberás gestionar esa segmentación directamente en Mensagia antes de lanzar la aplicación.

---

## ⚠ Aviso importante sobre el envío

El programa **no envía los correos de forma inmediata**. Por cada contacto elegible crea una configuración de envío individual en la plataforma Mensagia, programada para ejecutarse de forma escalonada:

- El **primer envío** se ejecuta entre **10 y 20 minutos** después de lanzar la aplicación, para dar margen a cancelar si se detecta algún error.
- Los **envíos siguientes** se espacian **12 segundos** entre sí (5 por minuto).

> **Si necesitas detener el envío una vez iniciado**, deberás eliminar cada configuración de envío de forma individual desde el portal de Mensagia. No existe un botón de cancelación global.
>
> Usa el modo **Simular** para revisar qué se enviaría sin crear ninguna configuración real.

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
