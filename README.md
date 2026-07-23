# Publicación de materiales

Este repositorio publica en `dodero.github.io` HTML y PDF generados desde los repositorios declarados en [`config/repositories.json`](config/repositories.json). Jekyll genera la portada, el layout y el estilo del sitio; los materiales generados se conservan como contenido estático.

Cada entrada permite seleccionar:

* `ref`: rama, tag o commit que se publica;
* `builder`: `marp`, `mkdocs`, `asciidoctor` o `custom`;
* `formats`: `html`, `pdf` o ambos;
* `sources`: materiales concretos que deben generarse;
* `publish_source`: publicación opcional del Markdown fuente, desactivada por defecto.

También puede declarar `icon`, `subject`, `degree`, `event`, `year` y `tags`. Los tags se normalizan sin el prefijo `#` en el catálogo y se muestran como `#tag` en las tarjetas; la búsqueda los incluye.

Para un material asociado a un evento en lugar de una asignatura se puede usar, por ejemplo, `event: "Cursos de verano de la UCA"`, `year: "2026"` y omitir `subject` y `degree`.

El workflow `.github/workflows/publish.yml` permite publicar todos los repositorios o seleccionar uno y sobrescribir su rama mediante `workflow_dispatch`. También acepta `repository_dispatch` con `repository` y `ref` en el payload.

Las publicaciones selectivas son incrementales: se recupera el último artefacto de Pages y solo se regeneran los materiales del repositorio seleccionado; el resto del catálogo y sus ficheros permanecen intactos. El artefacto se conserva 90 días. Si no existe un artefacto anterior disponible, la ejecución selectiva realiza automáticamente una generación completa.

Para que un repositorio fuente dispare la publicación al hacer push, puede incluir un workflow como este (requiere un secreto `SITE_DISPATCH_TOKEN` con permiso de escritura sobre `dodero/dodero.github.io`):

```yaml
name: Notify dodero.github.io

on:
  push:
    branches: [changes-2026]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Request publication
        env:
          GH_TOKEN: ${{ secrets.SITE_DISPATCH_TOKEN }}
        run: |
          gh api repos/dodero/dodero.github.io/dispatches \
            --method POST \
            -f event_type=publish-material \
            -f 'client_payload[repository]=${{ github.repository }}' \
            -f 'client_payload[ref]=${{ github.ref_name }}'
```

El payload debe incluir siempre `client_payload.repository` con el formato `owner/repositorio`; `client_payload.ref` es opcional y, si se omite, se usa la rama definida en `config/repositories.json`.

Los repositorios privados necesitan un secreto `PUBLISH_TOKEN` con permiso de lectura únicamente sobre los repositorios fuente seleccionados. Todo material copiado a GitHub Pages es público.

Para ejecuciones locales, copia [`config/local-secrets.example.json`](config/local-secrets.example.json) a `config/local-secrets.json` y sustituye los valores. `config/local-secrets.json`, `.secrets/` y los ficheros `.env` están ignorados por Git. En GitHub Actions los secretos deben seguir configurándose en `Settings → Secrets and variables → Actions`; un fichero local no existe en el runner remoto.

Los secretos locales se cargan con `--secrets-file` o, por defecto, desde `config/local-secrets.json` y `.secrets/publish.json`. No se copian a `dist` ni a `_site`.

El HTML se sanitiza antes de publicarse: se eliminan todos los comentarios HTML y la ejecución falla si queda alguno.

Los builders JavaScript utilizan `pnpm`; el workflow no usa `npm`.

El workflow ejecuta `bundle exec jekyll build` después de generar el catálogo y los materiales, y publica el directorio `_site` en GitHub Pages.

## Prueba local

```bash
python3 scripts/checkout_sources.py --repository uca-gii/gii-dss --ref changes-2026
python3 scripts/publish.py --repository uca-gii/gii-dss --ref changes-2026 --browser-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Para añadir más materiales solo hay que ampliar `sources` en la configuración. Los adaptadores de MKDocs y Asciidoctor permiten declarar sus comandos específicos cuando el repositorio no usa una convención estándar.
