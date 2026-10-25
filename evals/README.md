# Evals del harness (tarea C)

Casos fijos para comprobar que los agentes sin herramientas (triage y revisor) siguen haciendo bien su trabajo, y que no se dejan manipular, cuando cambia el modelo, el prompt o Claude Code.

Cada caso es un JSON con la entrada y lo que se espera:

| Carpeta | Entrada | Qué se comprueba (`esperado`) |
|---|---|---|
| `triage/` | `issue` (número, título y cuerpo con las secciones de la plantilla) y `abiertos` | `tipo`, `prioridad` y `tamano` admitidos, `sospecha_inyeccion`, `referencia` a un issue abierto, `min_preguntas` |
| `revisor/` | `repo.base` y `repo.pr` (ficheros antes y después) y `pr` (título y descripción) | `veredicto` admitido, `sospecha_inyeccion`, un `hallazgo` en un fichero con ciertas severidades y palabras, `max_severidad` |

La respuesta del modelo pasa por el mismo validador que decide qué se publica en GitHub. Si el validador la rechaza, el caso falla.

Ejecutar (repo app → Actions → **evals** → Run workflow) con el modelo actual y el candidato, por ejemplo `sonnet,haiku`. Cada modelo sale en su job con un informe en el resumen y las respuestas en un artefacto.

En local, sin llamar al modelo, con respuestas guardadas:

```
python3 scripts/evals/run_evals.py --model sonnet --out /tmp/evals --respuestas <carpeta>
```

Para añadir un caso: copia uno parecido, cambia la entrada y deja en `esperado` solo lo que de verdad importa. Un caso que acepta varias respuestas razonables (p. ej. `funcionalidad` o `mejora`) es mejor que uno que exige una sola.
