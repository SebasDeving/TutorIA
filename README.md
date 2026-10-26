# Tutor virtual: POC LMS con IA y voz

Aplicación demostrativa en Python para el ejercicio técnico. Incluye un curso con dos lecciones, dos alumnos de prueba, control de acceso por cuenta, conversación persistente por alumno y lección, respuestas basadas solo en el texto didáctico y entrada/salida de voz desde el navegador.

## Ejecutar en Windows

1. Instala Python 3.10 o superior.
2. Abre PowerShell en esta carpeta.
3. (Opcional) Crea un entorno virtual: `py -m venv .venv` y actívalo con `.\.venv\Scripts\Activate.ps1`.
4. Instala la dependencia: `py -m pip install -r requirements.txt`.
5. Inicia la aplicación: `py app.py`.
6. Abre <http://127.0.0.1:5000>.


## Usuarios de demostración

- Ana: `ana` / `ana123` (tiene acceso).
- Luis: `luis` / `luis123` (sin acceso; se muestra un 403).

Prueba “¿Para qué sirve POST?” o “¿qué significa 404?”. Pregunta algo ajeno a la lección para ver la respuesta de falta de contexto. Usa “Hablar” para dictar y “Escuchar respuesta” para oír al tutor. El navegador puede solicitar permiso de micrófono. La función de voz depende del soporte del navegador y conexión a sus servicios de reconocimiento.

## Decisiones y límites

- Flask sirve las páginas y valida el acceso en cada ruta y operación de conversación. SQLite almacena mensajes identificados por alumno y lección mediante consultas parametrizadas. Jinja escapa los valores de las plantillas y el cliente inserta texto con `textContent`.
- Las peticiones que modifican estado requieren token CSRF. La cookie de sesión usa `HttpOnly` y `SameSite=Lax`; configura `COOKIE_SECURE=true` al servir por HTTPS.
- El tutor de esta POC es un mecanismo extractivo local, sin proveedor externo ni costo: puntúa frases por coincidencia de términos y se abstiene cuando no encuentra relación. No es un modelo generativo ni sustituye una integración RAG/LLM para producción.
- La voz usa Web Speech API del navegador; la transcripción se muestra para revisar antes de enviar y la síntesis reproduce las respuestas. No se envía audio al servidor de esta aplicación.
- Los usuarios y contraseñas son datos fijos de demostración, no un sistema de identidad de producción. Antes de exponerla, reemplázalos por autenticación real y contraseñas con hash, configura un `SECRET_KEY` aleatorio y privado, usa HTTPS (`COOKIE_SECURE=true`) y añade límites de intentos, monitoreo y respaldos. El valor predeterminado de `SECRET_KEY` solo sirve para desarrollo local.
- Las lecciones de ejemplo se declaran en `app.py`; la base SQLite `tutor.db` se crea en el primer acceso.
