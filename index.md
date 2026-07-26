---
layout: default
title: Materiales docentes
---

<header>
  <h1>Materiales docentes</h1>
  <p class="intro">Apuntes, presentaciones y recursos educativos sobre Informática y Software.</p>

  <div class="search-panel" role="search" aria-label="Buscar y filtrar materiales">
    <label class="search-field">
      <span class="sr-only">Buscar materiales</span>
      <input id="query" type="search" placeholder="Buscar por título, asignatura, tema o curso…" autocomplete="off">
    </label>
    <fieldset class="language-filter">
      <legend>Idioma</legend>
      <button type="button" class="language-option is-active" data-language="" aria-pressed="true">Todos</button>
      <button type="button" class="language-option" data-language="es" aria-pressed="false">Español</button>
      <button type="button" class="language-option" data-language="en" aria-pressed="false">English</button>
    </fieldset>
    <label class="tag-field">
      <span>Etiqueta</span>
      <select id="tag-filter">
        <option value="">Todas las etiquetas</option>
      </select>
    </label>
  </div>
  <p id="summary" class="summary">{{ site.data.catalog.materials | group_by: "group" | size }} materiales</p>
</header>

<section id="materials" class="grid" aria-live="polite">
  {% if site.data.catalog.materials and site.data.catalog.materials.size > 0 %}
    {% assign material_groups = site.data.catalog.materials | group_by: "group" %}
    {% for material_group in material_groups %}
      {% assign primary = material_group.items | first %}
      <article class="card"
        data-search="{% for material in material_group.items %}{{ material.title | escape }} {{ material.description | escape }} {{ material.repo | escape }} {{ material.subject | escape }} {{ material.degree | escape }} {{ material.event | escape }} {{ material.year | escape }} {{ material.tags | join: ' ' | escape }} {% endfor %}"
        data-tags="{{ primary.tags | join: ',' | escape }}"
        data-languages="{% for material in material_group.items %}{{ material.language | escape }},{% endfor %}">
        <div class="card-heading">
          <div class="card-icon" aria-hidden="true">{{ primary.icon | default: '📄' | escape }}</div>
          <div>
            {% if primary.subject %}<p class="card-kicker">{{ primary.subject | escape }}</p>{% elsif primary.event %}<p class="card-kicker">{{ primary.event | escape }}</p>{% endif %}
            <h2><a class="card-title" href="{{ primary.html | relative_url }}">{{ primary.title | escape }}<span class="sr-only"> — abrir versión HTML</span></a></h2>
          </div>
        </div>
        <p class="card-description">{{ primary.description | escape }}</p>
        <div class="meta">
          {% if primary.degree %}<div>{{ primary.degree | escape }}</div>{% endif %}
          {% if primary.year %}<div>Curso {{ primary.year | escape }}</div>{% endif %}
        </div>
        <div class="tags">
          {% for tag in primary.tags %}<span class="tag">#{{ tag | escape }}</span>{% endfor %}
        </div>
        <div class="variants" aria-label="Versiones disponibles">
          {% for material in material_group.items %}
            <div class="variant" data-language="{{ material.language | escape }}" data-title="{{ material.title | escape }}" data-description="{{ material.description | escape }}" data-html="{{ material.html | relative_url }}">
              <span class="variant-language">{% if material.language == "en" %}Download{% else %}Descargar{% endif %}</span>
              <div class="links">
                {% if material.html_zip %}<a class="download-link" href="{{ material.html_zip | relative_url }}" download>HTML (ZIP)</a>{% endif %}
                {% if material.pdf %}<a href="{{ material.pdf | relative_url }}">PDF</a>{% endif %}
                {% if material.source %}<a href="{{ material.source | relative_url }}">Source</a>{% endif %}
              </div>
            </div>
          {% endfor %}
        </div>
      </article>
    {% endfor %}
  {% else %}
    <p class="empty">Todavía no hay materiales publicados.</p>
  {% endif %}
  <p id="no-results" class="empty" hidden>No hay materiales que coincidan con estos filtros. <button type="button" id="clear-filters">Restablecer filtros</button></p>
</section>
