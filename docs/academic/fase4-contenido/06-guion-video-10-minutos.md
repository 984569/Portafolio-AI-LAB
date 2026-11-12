# Guion de demostración de Portfolio AI Lab

**Curso.** Proyecto de Grado 202016907, Universidad Nacional Abierta y a Distancia.

**Proyecto.** Optimización dinámica de portafolios financieros mediante aprendizaje por refuerzo profundo aplicado a activos líquidos.

**Duración objetivo.** 09:30, con 30 segundos de margen antes del límite de diez minutos.

**Formato.** Demostración de pantalla con las tres cámaras web encendidas, visibles y grabadas desde el saludo hasta el cierre. La distribución define la exposición y no acredita aportes o autoría.

| Expositor | Inicio | Fin | Tiempo |
|---|---:|---:|---:|
| Martín Castrillón Vásquez, investigador principal | 00:00 | 04:15 | 04:15 |
| Eduardo Jesús Daza Cañizares, coinvestigador | 04:15 | 07:00 | 02:45 |
| Eliana Marcela Monsalve López, coinvestigadora | 07:00 | 09:30 | 02:30 |

## Preparación antes de grabar

- Abrir la aplicación local en `http://127.0.0.1:3000/dashboard`. Dejar en pestañas separadas el historial, AI Research Lab, Agent Desk, la tabla de resultados y las evidencias de respaldo. Comprobar que el origen de datos sea histórico y que el prototipo esté en modo PAPER. Los comandos de inicio y los requisitos del snapshot se encuentran en el [manual operativo](../../RUNBOOK.md).
- En la base local predeterminada se comprobó por lectura el experimento histórico **Prueba equal-weight** y los seis entrenamientos finales con evaluación guardada. Los nombres empiezan por **Initial ppo** o **Initial ddpg**, con semillas 7, 42 y 123. Preparar **Initial ppo seed42** y **Initial ddpg seed42**. Evitar el trabajo DDPG semilla 123 marcado como fallido y seleccionar su continuación completada.
- Abrir la [tabla del estudio](02-resultados-experimentales.md) para citar las medias. Preparar la [captura histórica](../../evidence/stage2/dashboard-markowitz-1440.png), la [captura del veto con proveedor de pruebas](../../evidence/stage4/agent-desk-768.png) y la [traza autenticada de NVIDIA](../../evidence/stage4/authenticated-nvidia-lightning.json). El historial de Agent Desk de la base predeterminada estaba vacío al revisar. La prueba autenticada quedó en una base aislada y su traza se muestra como evidencia guardada.
- Ensayar los cambios de pantalla con la cámara en composición de mosaico o tres miniaturas persistentes. Mantener a la vista la pestaña compartida y las tres cámaras, con micrófono activo solo para quien habla. Cerrar pestañas con credenciales, perfiles privados y notificaciones. Confirmar que las cifras sean legibles en el video final y que las transiciones incluyan el cambio de voz sin un corte de cámara.
- La demostración utiliza registros existentes. No pulsar **Entrenar modelo**, **Ejecutar prueba** o **Analizar propuesta** para iniciar una nueva corrida durante este guion. La comparación de modelos guardados puede prepararse antes de grabar. Si una vista local no abre o el proveedor no está disponible, usar la captura o traza correspondiente e identificarla como registro previo. Mantener 2024 bloqueado.

## Martín Castrillón Vásquez

### 00:00 a 00:50 · 50 segundos

**Pantalla y acción.** Mostrar la portada con los nombres y el código del curso durante unos segundos. Cambiar al dashboard y señalar la etiqueta PAPER.

**Locución.**

> Buenos días. Somos Martín Castrillón Vásquez, Eduardo Jesús Daza Cañizares y Eliana Marcela Monsalve López. Presentamos Portfolio AI Lab, prototipo del proyecto de grado de Ingeniería de Sistemas de la UNAD. Investigamos cómo asignar pesos a diez activos líquidos cuando cambian sus retornos y correlaciones. Desarrollamos un agente con PPO y otro con DDPG, y los comparamos mediante backtesting con una cartera equiponderada y con Markowitz. En el dashboard se identifica el modo PAPER. Las operaciones y el capital que mostraremos corresponden a una simulación histórica.

### 00:50 a 01:55 · 1 minuto y 5 segundos

**Pantalla y acción.** Mostrar el diagrama de arquitectura preparado a partir de [Desarrollo de ingeniería](01-desarrollo-ingenieria.md). Seguir con el puntero el flujo de datos, API, trabajador y registro. Regresar al dashboard y abrir **AI Research Lab**.

**Locución.**

> El flujo comienza con un snapshot histórico verificado. La API en FastAPI valida la solicitud y registra el trabajo en SQLite. El motor cuantitativo y el entorno Gymnasium comparten la contabilidad del portafolio, de modo que las comisiones se calculan con la misma convención en las cuatro estrategias. El entrenamiento se ejecuta en un proceso aparte y la interfaz Next.js consulta el avance y los resultados mediante la API. Esta separación permite abrir un experimento y rastrear su configuración, sus datos y el modelo utilizado. Ahora voy a mostrar un entrenamiento final que ya quedó guardado, para que se vea el paso entre el trabajo y su evaluación.

### 01:55 a 03:10 · 1 minuto y 15 segundos

**Pantalla y acción.** En el registro de entrenamientos, localizar **Initial ppo seed42** y pulsar **Abrir**. Expandir **Configuración, checkpoints y manifiesto**. Señalar semilla, pasos y checkpoint. Luego abrir **Initial ddpg seed42** y mostrar su evaluación guardada.

**Locución.**

> Aquí está el trabajo final de PPO con semilla cuarenta y dos. PPO actualiza la política con un criterio que acota el cambio entre la política anterior y la nueva. DDPG emplea un actor y un crítico para el espacio de acciones continuas. Ambos producen propuestas de pesos que el entorno convierte a asignaciones largas y sin apalancamiento. Guardamos el modelo, el normalizador ajustado en entrenamiento y un manifiesto de configuración. En DDPG también se conserva el búfer para reanudar. En el estudio final ejecutamos dieciséis mil trescientos ochenta y cuatro pasos por semilla para PPO y ocho mil ciento noventa y dos para DDPG. Las curvas abiertas corresponden a sus evaluaciones guardadas en dos mil veintidós y dos mil veintitrés.

### 03:10 a 04:15 · 1 minuto y 5 segundos

**Pantalla y acción.** Señalar **Validación 2022–2023**. Mostrar la sección de asignaciones y métricas adicionales. Volver al panel principal y mostrar el selector de **Partición de evaluación** y el aviso de 2024.

**Locución.**

> La selección de tasas se hizo en dos ventanas walk-forward, con resultados anteriores a dos mil veintidós. Elegida la tasa por algoritmo, se ajustaron las políticas finales con datos de dos mil quince a dos mil veintiuno y se evaluaron congeladas en el siguiente tramo. Usamos tres semillas por algoritmo y conservamos las tres. En el panel se puede inspeccionar la curva y los pesos de una corrida concreta. La media que presentaremos enseguida se calcula con el artefacto experimental, no leyendo una sola curva. El conjunto de dos mil veinticuatro sigue bloqueado y no intervino en el ajuste ni en la comparación. Eduardo va a mostrar el origen de las series, cómo se simularon las decisiones y qué resultados produjo la evaluación.

## Eduardo Jesús Daza Cañizares

### 04:15 a 05:10 · 55 segundos

**Pantalla y acción.** Mostrar **Origen de datos → HISTÓRICO** y el informe de calidad. Resaltar los diez activos, las tres particiones y las 2.516 sesiones.

**Locución.**

> Los diez instrumentos incluyen acciones estadounidenses y fondos cotizados. El snapshot de Yahoo Finance contiene dos mil quinientas dieciséis sesiones entre dos mil quince y dos mil veinticuatro. Las sesiones están alineadas en un calendario común. El pipeline valida cobertura, duplicados y precios inválidos, y guarda la procedencia del archivo. Hay mil setecientas sesenta y tres sesiones de entrenamiento, quinientas una de validación y doscientas cincuenta y dos reservadas. Los ajustes del proveedor son retrospectivos. El control de calidad comprueba consistencia, pero la fuente no reconstruye la versión exacta que existía en cada fecha.

### 05:10 a 06:00 · 50 segundos

**Pantalla y acción.** En **Experimentos guardados**, pulsar **Ver** junto a **Prueba equal-weight**. Señalar la curva de capital, el retorno y la fuente. Mostrar la [captura de Markowitz](../../evidence/stage2/dashboard-markowitz-1440.png) como registro de la prueba de interfaz.

**Locución.**

> En Gymnasium, el agente observa retornos pasados y la asignación conocida. El entorno calcula el efecto del rebalanceo y la comisión antes de valorar la cartera en el siguiente cierre. Las referencias se ejecutan con la misma contabilidad. La estrategia equiponderada reparte el capital entre los diez activos. Markowitz estima retornos y covarianzas en una ventana móvil, y resuelve la asignación sin ventas en corto. En la pantalla vemos la curva equiponderada. La captura siguiente conserva el resultado de la referencia Markowitz bajo la configuración histórica.

### 06:00 a 07:00 · 1 minuto

**Pantalla y acción.** Mostrar la tabla del [estudio experimental](02-resultados-experimentales.md). Apuntar a las columnas de retorno neto, Sharpe, volatilidad, drawdown y costos. Mantener la tabla visible durante la transición.

**Locución.**

> La validación usa quinientos intervalos en dos mil veintidós y dos mil veintitrés, diez mil dólares simulados de capital inicial y diez puntos básicos de comisión. El equiponderado obtuvo catorce coma cuarenta y nueve por ciento. Markowitz obtuvo menos treinta y uno por ciento. La media de tres semillas fue menos trece coma noventa y cuatro por ciento en PPO y menos cuarenta y dos coma cincuenta y seis por ciento en DDPG. La referencia equiponderada también tuvo el mayor Sharpe. Los modelos aprendidos registraron más rotación y mayores costos. El resultado describe este protocolo y este tramo de mercado. No establece que los algoritmos tengan el mismo comportamiento en otros períodos. Eliana cierra con la evidencia de integración y seguridad.

## Eliana Marcela Monsalve López

### 07:00 a 07:45 · 45 segundos

**Pantalla y acción.** Mostrar la tabla de incrementos de [Desarrollo de ingeniería](01-desarrollo-ingenieria.md) y el resumen de [Pruebas y validación](03-pruebas-validacion-trl5.md). Cambiar a Agent Desk.

**Locución.**

> Scrum se planteó como metodología de desarrollo del proyecto. La evidencia técnica permite seguir incrementos verificables en datos, simulación, modelos e interfaz. Las responsabilidades de implementación asistida por Codex se registraron por separado de los aportes académicos. Para comprobar el prototipo, combinamos pruebas unitarias de contabilidad, pruebas de API y recorridos de navegador sobre datos históricos. También se verificaron la reanudación de checkpoints y la persistencia. El informe registra cuatrocientas noventa y nueve pruebas Python aprobadas y trece casos de navegador acumulados.

### 07:45 a 08:45 · 1 minuto

**Pantalla y acción.** Abrir **AI Agent Desk** y señalar fecha, estrategia y controles. Mostrar la [traza NVIDIA guardada](../../evidence/stage4/authenticated-nvidia-lightning.json) con los eventos Analyst y Judge, la ruta y el resultado `watch`. Cambiar al [registro del veto](../../evidence/stage4/historical-agent-runs.json) o la [captura E2E](../../evidence/stage4/agent-desk-768.png) con etiqueta de proveedor simulado. Si se usa la captura, evitar leer de ella el valor 75,03 %, que corresponde al registro JSON.

**Locución.**

> Agent Desk es una extensión separada del estudio cuantitativo. El Analyst recibe un resumen histórico y el Judge devuelve un veredicto estructurado. El motor de riesgos revisa la propuesta con reglas determinísticas y conserva cada decisión. En la prueba autenticada, la ruta gratuita de NVIDIA validó ambas respuestas, y la propuesta equiponderada quedó en observación. Esta es su traza guardada. En una prueba distinta, con inferencia simulada y datos históricos reales, el Judge aprobó una propuesta Markowitz. El motor la vetó porque una posición superó el límite del treinta y cinco por ciento. El sistema conserva el motivo y nunca envía una orden.

### 08:45 a 09:30 · 45 segundos

**Pantalla y acción.** Mostrar una diapositiva de cierre con las cuatro conclusiones en frases cortas y el estado de validación. Conservar las tres cámaras visibles hasta terminar.

**Locución.**

> El prototipo integra el flujo desde la preparación de datos hasta la comparación y la auditoría. En la validación disponible, las políticas aprendidas no superaron a la cartera equiponderada. Las pruebas locales y la simulación histórica respaldan la integración. Para sustentar el nivel TRL cinco aún corresponde documentar la aceptación en un entorno relevante y la reproducción por un operador independiente. El período reservado de dos mil veinticuatro permanece bloqueado. Gracias por acompañarnos en la demostración.

## Control final de grabación

Los tiempos incluyen navegación y pausas. Ensayar una vez con el cronómetro visible para el equipo, ajustar silencios y transiciones, y exportar la versión completa. Verificar duración real menor o igual a diez minutos, audio inteligible, tres cámaras visibles, números legibles y ausencia de secretos. El enlace debe comprobarse desde una sesión con los permisos que tendrá el tutor. Registrar el vínculo solo después de grabar y publicar el video con la autorización del equipo. La exigencia de duración y cámaras se toma de la guía oficial de Fase 4, pp. 3–4.
