<!-- agent-standards v1.0.0 · fuente: poc-almagentic-core/agent-standards/constitution.base.md -->
# Constitución de desarrollo

Principios no negociables. Toda spec, plan y tarea generada con Spec Kit debe cumplirlos; si una spec los contradice, la constitución gana y el conflicto se señala en la spec.

## I. Seguridad por defecto (NO NEGOCIABLE)

- Ningún secreto en el código, la configuración versionada, los logs ni los mensajes de error.
- Toda entrada externa se valida con un esquema explícito antes de usarse.
- Los errores devuelven mensajes genéricos al cliente; el detalle solo va al log.
- Dependencias nuevas: solo de registros públicos oficiales, con versión fijada y licencia compatible.

## II. Spec primero

- No hay implementación sin spec aprobada en `specs/` y un issue que la origine.
- Cada requisito tiene criterios de aceptación verificables.
- Lo que no está en la spec no se construye.

## III. Tests como contrato

- Cada criterio de aceptación tiene al menos un test automatizado.
- Los tests se escriben antes o junto con el código, nunca después del PR.
- Un test que falla no se desactiva: se arregla el código o se cambia la spec con aprobación humana.

## IV. Trazabilidad

- Issue → spec → rama → commits → PR → release forman una cadena enlazada.
- Cada commit referencia su issue; cada PR enlaza issue y spec.
- Todo cambio hecho por un agente es identificable como tal (identidad de bot).

## V. Control humano

- Un humano aprueba cada PR y cada promoción a un entorno.
- Los agentes operan con mínimo privilegio y credenciales de vida corta.
- Los ficheros que gobiernan a los agentes solo los cambia un humano.

## VI. Simplicidad

- La solución más simple que cumple la spec.
- Sin abstracciones especulativas ni dependencias "por si acaso".

## Gobierno

- Esta constitución se versiona en `poc-almagentic-core` y se copia a cada repo de aplicación.
- Cambiarla requiere un PR en core aprobado por un humano y una nueva versión de `agent-standards`.
