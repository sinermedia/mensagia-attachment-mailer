# Mensagia Attachment Mailer

Aplicación para enviar correos electrónicos con adxuntos personalizados por contacto usando a [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versións: [Español](../README.md) · [Català](README.ca.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisitos

- Windows 10/11 (para o executable)
- Ou Python 3.11+ (para executar dende o código fonte)

---

## Uso do executable (clientes sen Python)

1. Descarga o executable dende a [páxina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) (`mensagia-mailer-gui.exe` para modo gráfico, ou `mensagia-mailer-console.exe` para modo consola)
2. Crea un ficheiro `.env` na **mesma carpeta** que o `.exe` co teu token:

```
MENSAGIA_API_TOKEN=o_teu_token_api_aqui
```

> Podes obter o teu token API en [mensagia.com](https://mensagia.com) → Usuarios.
> Se non existe o ficheiro `.env`, a aplicación pedirache o token ao arrancar.

3. Executa o `.exe`.

> **Aviso de Windows SmartScreen:** a primeira vez que executes o ficheiro, Windows pode mostrar un aviso de seguridade. Fai clic en **"Máis información"** e logo en **"Executar de todos modos"**. Só é necesario facelo unha vez por cada versión descargada.

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

> O progreso gárdase no ficheiro `send_progress.json`, no mesmo cartafol que o `.env` ou o `.exe`. Cando un envío remata sen erros, a campaña bórrase do ficheiro. Non o elimines mentres haxa un envío pendente de retomar.

---

## Memoria de seleccións (modo gráfico)

Tras cada envío ou simulación, a aplicación garda os parámetros escollidos
(modelo, remitente, grupo, campo adxunto e certificado) nun ficheiro
`last_selections.json`, na mesma carpeta que o `.env` ou o `.exe`.

Na seguinte execución, esas opcións quedarán marcadas por defecto.

> Para borrar esta memoria, elimina o ficheiro `last_selections.json`.
> A aplicación funciona con normalidade se o ficheiro non existe.

---

## Idiomas da interface

A interface detecta automaticamente o idioma do sistema operativo.  
Idiomas dispoñibles: **Español, Català, Galego, Euskera, English**.

---

## Xerar o executable

Require as dependencias de desenvolvemento:

```bash
pip install -r requirements-dev.txt
```

Executa o script de compilación:

```bash
build.bat
```

Os ficheiros `.exe` xéranse na carpeta `dist/`.

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
├── build.bat               # Script de compilación a .exe
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
