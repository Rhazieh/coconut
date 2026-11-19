<p align="center">
  <img src="assets/icons/coconut.svg" width="92" height="92" alt="Logo de Coconut"/>
</p>

<h1 align="center">Coconut</h1>

<p align="center">
  <strong>Visor de Markdown rápido, minimalista y 100% local, diseñado para leer durante horas sin fatiga visual en Linux.</strong>
</p>

<p align="center">
  <a href="https://github.com/Rhazieh/coconut/actions/workflows/ci.yml"><img src="https://github.com/Rhazieh/coconut/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/Licencia-MIT-D4A373?style=flat-square" alt="Licencia MIT"/></a>
  <img src="https://img.shields.io/badge/Linux-Wayland%20%26%20X11-2E2C29?style=flat-square" alt="Wayland y X11"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/UI-PyQt6%20%2B%20QtWebEngine-41CD52?style=flat-square" alt="PyQt6"/>
</p>

<p align="center">
  <a href="README.md">English</a> &nbsp;|&nbsp; <strong>Español</strong>
</p>

---

## ¿Por qué Coconut (`coco`)?

Casi todas las aplicaciones para abrir Markdown en Linux o en la web son **editores primero**: dividen la pantalla mostrando el código `**crudo**` junto a la vista previa, no permiten pantalla completa limpia, cobran suscripciones por funciones básicas o te obligan a subir archivos locales privados a servidores de terceros.

Solo quería hacer doble clic en un `.md` (o tirar `coco apuntes.md`) y **leerlo limpio, rápido y sin conexión**, sin ver código fuente ni cansar la vista después de horas estudiando apuntes o documentación técnica.

Como un coco real —**cáscara oscura por fuera (`#191817`), pulpa crema suave por dentro (`#DCD7CE` / `#F3ECDC`)**— nació mediante un **flujo de desarrollo asistido por IA**, combinando criterios concretos de ergonomía tipográfica, calibración anti-halación e integración nativa con Linux Wayland/X11 y Freedesktop.

---

## Capturas de pantalla

| Noche cálida (`warm-dark`, predeterminada) | Sepia papel (`sepia`) |
| :---: | :---: |
| ![Coconut Noche cálida](docs/screenshots/coconut-warm-dark.png) | ![Coconut Sepia papel](docs/screenshots/coconut-sepia.png) |

---

## Diseño ergonómico y comodidad visual

- **Una sola fuente en toda la app:** Toda la interfaz y el documento usan exclusivamente [**Atkinson Hyperlegible Next**](https://github.com/googlefonts/atkinson-hyperlegible-next) (Braille Institute), incluida localmente bajo licencia SIL OFL 1.1. Su diferenciación extrema entre glifos ambiguos (`1`/`l`/`I`, `0`/`O`), altura x amplia y aperturas abiertas reduce el cansancio mental al leer texto largo mezclado con rutas y comandos (`Noto Color Emoji` solo actúa como respaldo para emojis).
- **Contraste calibrado contra la halación:** El blanco puro `#FFFFFF` sobre negro `#000000` (`21:1`) produce halo luminoso y fatiga visual. Coconut usa por defecto **Noche cálida** (`#DCD7CE` sobre `#191817`, contraste `~12.4:1` WCAG AAA) con acentos ámbar cálidos (`#D4A373`) evitando el azul saturado.
- **Tres paletas con un atajo (`Ctrl+T`):**

  | Paleta | Fondo | Texto | Acento | Ideal para |
  | :--- | :--- | :--- | :--- | :--- |
  | **Noche cálida** (`warm-dark`) | `#191817` | `#DCD7CE` | `#D4A373` | Noche y ambientes con poca luz |
  | **Sepia papel** (`sepia`) | `#F3ECDC` | `#352F28` | `#9A5B25` | Luz interior cálida |
  | **Piedra suave** (`soft-light`) | `#F4F3EE` | `#2A2926` | `#3E6B89` | Luz diurna intensa |

- **Medida y escala óptimas:** Ancho adaptable de `68ch` (`~65–72` caracteres por línea en cualquier tamaño), interlineado `1.72` y tamaño de texto persistente de `12` a `36 px` (`Ctrl++` / `Ctrl+-` / `Ctrl + rueda`).
- **Cero ruido visual y archivos por carpeta:** Sin barras de menú ni editor; una barra lateral colapsable reúne el **Índice** con *scrollspy* (oculto en documentos cortos), los **archivos `.md` abiertos agrupados por carpeta desplegable** (persistentes entre reinicios hasta que los cerrás manualmente) y un discreto engranaje de **Ajustes** abajo a la izquierda (`Ctrl+,`).
- **Google Translate con clic derecho:** Seleccioná cualquier fragmento al leer, hacé clic derecho y abrilo directamente en Google Translate con tu par de idiomas configurado (`Auto → ES`, `EN → ES`, `ES → EN` o entre 27 idiomas comunes — solo al hacer clic, sin tráfico en segundo plano).
- **Pantalla completa y atajos editables:** Botón dedicado arriba a la derecha (`F11`) y editor visual de atajos dentro de Ajustes.

---

## Compatibilidad en Linux

Coconut funciona de forma nativa en **Wayland y X11** (Qt6 selecciona `wayland` o `xcb` automáticamente según la sesión):

- **Servidores gráficos:** Wayland (`wayland-egl`) y X11 (`xcb`).
- **Entornos y gestores de ventanas:** KDE Plasma 6/5, GNOME, Hyprland, Sway, XFCE, Cinnamon, LXQt y cualquier entorno compatible con estándares Freedesktop (`XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `xdg-mime`).
- **Idioma de la interfaz:** Detecta automáticamente español o inglés desde la configuración regional del sistema (o cambialo en vivo desde Ajustes / `~/.config/coconut/settings.json`).

---

## Instalación

### 1. Dependencias del sistema

Instalá PyQt6 WebEngine y la librería en C `libcmark-gfm` (o `python3-markdown` como respaldo):

- **Debian / Ubuntu (Debian 12/13, Ubuntu 24.04+):**
  ```bash
  sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine python3-pyqt6.qtwebchannel cmark-gfm
  ```
- **Fedora:**
  ```bash
  sudo dnf install python3-pyqt6 python3-pyqt6-webengine cmark-gfm-libs
  ```
- **Arch Linux:**
  ```bash
  sudo pacman -S python-pyqt6 python-pyqt6-webengine cmark-gfm
  ```

### 2. Instalar Coconut (por usuario, sin `sudo`)

```bash
git clone https://github.com/Rhazieh/coconut.git
cd coconut
./install.sh
```

Instala el comando `coco` (junto al alias `coconut`) y registra Coconut como visor predeterminado para `.md`. Si preferís no modificar tu programa predeterminado:

```bash
./install.sh --no-default
```

### Desinstalar

```bash
./uninstall.sh          # conserva ~/.config/coconut/settings.json
./uninstall.sh --purge  # elimina también la configuración
```

---

## Uso y atajos de teclado

Abrilo desde el menú de aplicaciones (**Coconut**), haciendo doble clic en cualquier `.md` desde Dolphin/Archivos, arrastrando archivos a la ventana o desde terminal:

```bash
coco ruta/al/archivo.md   # abre el archivo (reutiliza la instancia activa vía IPC)
coco                      # abre la pantalla de inicio o restaura la sesión previa
coco --standalone f.md    # fuerza un proceso independiente
coco --version            # muestra la versión
```

| Atajo *(editable)* | Acción |
| :--- | :--- |
| `Ctrl+O` | Abrir archivos (selección múltiple) |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Aumentar / reducir / restablecer tamaño (`18 px`) |
| `Ctrl + Rueda` | Ajustar tamaño de texto suavemente |
| `Ctrl+T` | Cambiar paleta (`Noche cálida` → `Sepia papel` → `Piedra suave`) |
| `Ctrl+B` | Mostrar u ocultar panel lateral |
| `Ctrl+F` | Buscar dentro del texto (`Enter` / `Shift+Enter`, `Esc` cierra) |
| `Ctrl+,` | Abrir Ajustes (opciones, traductor, atajos, créditos) |
| `j` / `k` | Desplazamiento vertical suave |
| `F11` (o botón superior derecho) | Pantalla completa |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Cambiar al archivo abierto siguiente / anterior |
| `Alt+←` / `Alt+→` (o botones laterales del mouse) | Navegar entre `.md` locales enlazados |
| `Ctrl+R` / `F5` | Recargar manualmente (también recarga sola al guardar cambios) |
| `Ctrl+W` / `Ctrl+Q` | Cerrar archivo actual / salir (conserva la sesión) |

---

## Arquitectura y seguridad

- **Renderizado veloz:** Invoca directamente a `libcmark-gfm` del sistema mediante `ctypes` (~11–13 ms en documentos de más de 5.000 palabras), con respaldo automático en `python-markdown`.
- **Sanitización y CSP estricta:** Filtra `<script>`, `<iframe>`, `<object>`, `<embed>`, `<svg>`, manejadores `on*` y URIs `javascript:` / `data:` inseguros antes de insertar en el DOM; aplica `Content-Security-Policy` estricta sin scripts en línea.
- **Arranque sin parpadeo blanco y recarga en vivo:** Configura el color de fondo en `QMainWindow` y `QWebEnginePage` antes de cargar el HTML, monitorea cambios con `QFileSystemWatcher` (preservando la posición de lectura incluso ante guardados atómicos) y usa un socket local `QLocalServer` para abrir nuevas ventanas al instante.

---

## Parte de una suite local para Linux

Coconut es la primera herramienta de una colección personal de utilidades Linux de código abierto, livianas y sin dependencia de terceros o servicios en la nube — con un lector minimalista de EPUB como próximo proyecto planeado.

---

## Licencia y agradecimientos

- **Código:** [Licencia MIT](LICENSE) — Copyright © 2026 Maximiliano Cano (`Rhazieh`).
- **Fuente incluida:** [Atkinson Hyperlegible Next](https://github.com/googlefonts/atkinson-hyperlegible-next) bajo licencia [SIL Open Font License 1.1](THIRD_PARTY_LICENSES/OFL-1.1.txt).
