# Memoria del TFM

Documento Word de la POC para el Trabajo Fin de Máster. Es un documento vivo: se actualiza al cerrar cada tarea.

| Fichero | Qué es |
|---|---|
| `tfm.md` | Contenido (fuente de verdad). Se edita aquí |
| `build_tfm.js` | Genera el `.docx` con portada, índice, cabecera y pie |
| `figuras/*.dot` | Diagramas en Graphviz; `*.png` se generan con `dot -Tpng -Gdpi=200` |
| `TFM-ALM-agentico.docx` | Documento generado (entregable) |

```bash
cd docs/tfm/figuras && for f in *.dot; do dot -Tpng -Gdpi=200 "$f" -o "${f%.dot}.png"; done && cd ../../..
node docs/tfm/build_tfm.js
```

Al abrir el `.docx` en Word, actualizar el índice: clic derecho → Actualizar campos.

Requisitos de la entrega: archivo DOC de 15 a 45 páginas con claridad en el problema, proceso de diseño y desarrollo, iteraciones con modelos, pruebas y resultados, y documentación técnica reproducible. El registro de iteraciones resume toda la conversación del proyecto omitiendo información sensible (tokens, claves, identificadores internos, correos, usuarios del sistema y enlaces de sesión).


Estilo de redacción: todo el texto de `tfm.md` se escribe y se revisa con la *skill* humanizer (sin rayas como conector, sin contrastes del tipo «no es X, sino Y», sin negritas de etiqueta ni cierres que repiten la idea). Solo se reescribe la prosa; el código, los comandos, las rutas, los datos y las referencias se mantienen.
