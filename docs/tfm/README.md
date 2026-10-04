# Memoria del TFM

Documento Word de la POC para el Trabajo Fin de Máster. Es un documento vivo: se actualiza al cerrar cada tarea.

| Fichero | Qué es |
|---|---|
| `tfm.md` | Contenido (fuente de verdad). Se edita aquí |
| `build_tfm.js` | Genera el `.docx` con portada, índice, cabecera y pie |
| `figuras/src/*.architecture.json` | Especificaciones de los diagramas (archify, tipo *architecture* con posiciones fijas para que quepan en A4; validadas con el perfil *showcase*) |
| `figuras/build_figuras.sh` | Valida cada diagrama, genera su HTML interactivo y exporta el PNG que usa el `.docx` |
| `TFM-ALM-agentico.docx` | Documento generado (entregable) |

```bash
docs/tfm/figuras/build_figuras.sh   # requiere archify (ver cabecera del script), Playwright y Pillow
node docs/tfm/build_tfm.js
```

Al abrir el `.docx` en Word, actualizar el índice: clic derecho → Actualizar campos.

Requisitos de la entrega: archivo DOC de 15 a 45 páginas con claridad en el problema, proceso de diseño y desarrollo, iteraciones con modelos, pruebas y resultados, y documentación técnica reproducible. El registro de iteraciones resume toda la conversación del proyecto omitiendo información sensible (tokens, claves, identificadores internos, correos, usuarios del sistema y enlaces de sesión).


Estilo de redacción: todo el texto de `tfm.md` se escribe y se revisa con la *skill* humanizer (sin rayas como conector, sin contrastes del tipo «no es X, sino Y», sin negritas de etiqueta ni cierres que repiten la idea). Solo se reescribe la prosa; el código, los comandos, las rutas, los datos y las referencias se mantienen.
