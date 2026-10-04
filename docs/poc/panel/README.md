# Panel de avance

- `gen_poc.py`: fuente única de las tareas, prerrequisitos y subtareas. Regenera las secciones de tareas de `../README.md` y los datos de `panel.html`.
- `panel.html`: el panel publicado como página en claude.ai.

```bash
python3 docs/poc/panel/gen_poc.py docs/poc/README.md docs/poc/panel/panel.html
```
