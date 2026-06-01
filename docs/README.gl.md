# Mensagia Attachment Mailer

Aplicación para enviar correos electrónicos con adxuntos personalizados por contacto usando a [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versións: [Español](../README.md) · [Català](README.ca.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisitos

- Windows 10/11 (para o executable)
- Ou Python 3.11+ (para executar dende o código fonte)

---

## Uso do executable (clientes sen Python)

1. Descarga `mensagia-mailer-gui.exe` (ou `mensagia-mailer-console.exe`)
2. Crea un ficheiro `.env` na **mesma carpeta** que o `.exe` co teu token:

```
MENSAGIA_API_TOKEN=o_teu_token_api_aqui
```

> Podes obter o teu token API en [mensagia.com](https://mensagia.com) → Usuarios.
> Se non existe o ficheiro `.env`, a aplicación pedirache o token ao arrancar.

3. Executa o `.exe`.

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
5. **Grupo** — Móstrase a lista de grupos da axenda.
6. **Campo adxunto** — Elíxese que campo personalizado contén a URL do adxunto.
7. **Certificado** — O usuario decide se certificar os envíos.
8. **Envío** — Fíltrase os contactos con email e URL de adxunto válidos, e envíase un correo por cada un a razón de 5/minuto.

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
