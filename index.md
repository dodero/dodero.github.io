---
layout: default
title: Materiales docentes
---

<header>
  <h1>Materiales docentes</h1>
  <p class="intro">Slides, apuntes y recursos publicados desde repositorios seleccionados.</p>
  <div class="toolbar" role="search">
    <label>
      <span class="sr-only">Buscar materiales</span>
      <input id="query" type="search" placeholder="Buscar por título, etiqueta o repositorio" autocomplete="off">
    </label>
    <label>
      <span class="sr-only">Filtrar por etiqueta</span>
      <select id="tag-filter">
        <option value="">Todas las etiquetas</option>
      </select>
    </label>
  </div>
  <p id="summary" class="summary">{{ site.data.catalog.materials.size }} materiales</p>
</header>

<section id="materials" class="grid" aria-live="polite">
  {% if site.data.catalog.materials and site.data.catalog.materials.size > 0 %}
    {% for material in site.data.catalog.materials %}
      <article class="card" data-search="{{ material.title | escape }} {{ material.description | escape }} {{ material.repo | escape }} {{ material.subject | escape }} {{ material.degree | escape }} {{ material.event | escape }} {{ material.year | escape }} {{ material.tags | join: ' ' | escape }}" data-tags="{{ material.tags | join: ',' | escape }}">
        <div class="card-heading">
          <div class="card-icon" aria-hidden="true">{{ material.icon | default: '📄' | escape }}</div>
          <h2>{{ material.title | escape }}</h2>
        </div>
        <p>{{ material.description | escape }}</p>
        <div class="meta">
          {% if material.subject %}<div><strong>Asignatura:</strong> {{ material.subject | escape }}</div>{% endif %}
          {% if material.degree %}<div><strong>Titulación:</strong> {{ material.degree | escape }}</div>{% endif %}
          {% if material.event %}<div><strong>Evento:</strong> {{ material.event | escape }}</div>{% endif %}
          {% if material.year %}<div><strong>Año:</strong> {{ material.year | escape }}</div>{% endif %}
        </div>
        <div class="tags">
          {% for tag in material.tags %}<span class="tag">#{{ tag | escape }}</span>{% endfor %}
        </div>
        <div class="links">
          {% if material.html %}<a href="{{ material.html | relative_url }}">HTML</a>{% endif %}
          {% if material.pdf %}<a href="{{ material.pdf | relative_url }}">PDF</a>{% endif %}
          {% if material.source %}<a href="{{ material.source | relative_url }}">Source</a>{% endif %}
        </div>
      </article>
    {% endfor %}
  {% else %}
    <p class="empty">Todavía no hay materiales publicados.</p>
  {% endif %}
</section>
