# Plan de publicación de dodero.github.io

## Objetivo

Publicar en `dodero.github.io` materiales HTML y PDF generados desde repositorios seleccionados del usuario `dodero` y de organizaciones de la enterprise `uca`.

## Decisiones de diseño

- La selección de repositorios se mantiene en `config/repositories.json`.
- Cada repositorio declara su `ref`, `builder`, `formats` y lista de `sources`.
- Se admiten los builders `marp`, `mkdocs`, `asciidoctor` y `custom`.
- Los builders JavaScript utilizan `pnpm`.
- Los HTML se sanitizan eliminando todos los comentarios HTML antes de publicarse.
- Los Markdown fuente no se publican salvo que `publish_source` se active explícitamente.
- Jekyll genera la portada, el layout y el estilo; los materiales generados se sirven como contenido estático.
- Cada tarjeta muestra icono, nombre, asignatura o evento, titulación cuando exista, año y tags buscables.
- GitHub Pages publica el artefacto final `_site`.

## Implementado localmente

- Checkout selectivo por repositorio y rama/tag/commit.
- Generación Marp/Marpit de HTML y PDF.
- Catálogo de materiales y búsqueda en la portada Jekyll.
- Workflow de GitHub Actions con deploy bajo demanda.
- Publicación incremental por `repository_dispatch` o selección manual: se reconstruye solo el repositorio indicado y se conserva el resto del artefacto de Pages.
- Soporte para secretos locales ignorados por Git.
- Pruebas locales con:
  - `uca-gii/gii-dss@changes-2026`
  - `uca-gii/construccion@changes-2026`

## Tareas pendientes para activar el despliegue remoto

1. Configurar en GitHub Actions el secreto `PUBLISH_TOKEN` con permiso de lectura únicamente sobre los repositorios fuente seleccionados.
2. Revisar en GitHub Pages que el origen de publicación sea GitHub Actions y que el entorno `github-pages` esté habilitado.
3. Añadir en `config/repositories.json` todos los materiales que deban publicarse.
4. Completar y probar las entradas MKDocs, Asciidoctor y `custom` cuando se incorporen esos repositorios.
5. Ejecutar un `workflow_dispatch` sin repositorio para generar todo el catálogo.
6. Ejecutar un `workflow_dispatch` indicando repositorio y `ref` para verificar el deploy selectivo.
7. Verificar en la URL pública:
   - portada y búsqueda;
   - enlaces HTML;
   - enlaces PDF;
   - recursos gráficos locales;
   - ausencia de comentarios HTML;
   - ausencia de ficheros fuente no autorizados.
8. Documentar cualquier excepción de generación específica de un repositorio.

## Ejecución local posterior

Para usar secretos en local, copiar `config/local-secrets.example.json` a `config/local-secrets.json`, editarlo sin incluirlo en Git y ejecutar los scripts con `--secrets-file` si se desea indicar otra ubicación.

## Criterios de aceptación

- Solo se procesan repositorios declarados en la configuración.
- Se publica exactamente la rama/ref seleccionada.
- Cada material expone únicamente los formatos configurados.
- El HTML público no contiene comentarios `<!-- ... -->`.
- Los secretos nunca aparecen en el repositorio ni en el artefacto publicado.
- Un fallo de generación impide publicar un artefacto incompleto.
