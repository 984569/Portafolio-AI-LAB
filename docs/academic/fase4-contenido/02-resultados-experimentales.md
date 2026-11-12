# Resultados experimentales

La comparación de Portfolio AI Lab cubre dos decisiones metodológicas distintas. La primera fue seleccionar una tasa de aprendizaje por algoritmo mediante dos ventanas de desarrollo anteriores a 2022. La segunda fue evaluar las políticas congeladas de PPO y DDPG en 2022–2023 y contrastarlas con equal-weight y Markowitz. Las cuatro estrategias compartieron el universo, la frecuencia de rebalanceo, el capital inicial y el costo proporcional. El conjunto final de 2024 permanece bloqueado. Los valores de este apartado corresponden a simulaciones sobre precios históricos, en USD cuando se indica. [Protocolo experimental](../../../experiments/stage3-protocol.json) · [Resultados de cada corrida](../../evidence/stage3/historical-study.json)

## Muestra y procedencia

El panel congelado contiene los diez instrumentos AAPL, MSFT, JPM, JNJ, XOM, PG, KO, WMT, SPY y GLD. Comprende 2.516 sesiones comunes, con 25.160 observaciones de cierre ajustado, entre el 2 de enero de 2015 y el 31 de diciembre de 2024. Yahoo Finance suministró precios diarios en USD por su interfaz pública de gráficos. El registro conserva la fecha de recuperación del 10 de noviembre de 2026, los parámetros de consulta, las respuestas JSON y los campos de dividendos y desdoblamientos. El panel usa XNYS como calendario común para las sesiones estadounidenses. [Manifiesto y procedencia](../../evidence/stage2/historical-validation.json) · [Registro de descarga](../../evidence/stage2/pipeline-progress.json)

El control verificó por instrumento el calendario, la cobertura, los duplicados, la validez numérica y la coherencia de los factores de ajuste. El informe registra cero sesiones faltantes, cero duplicados y cero celdas de precios inválidas para los diez instrumentos. El procesamiento rechaza datos incompletos y conserva los eventos corporativos para auditoría. Los retornos usan el cierre ajustado del proveedor, por lo que se evita contabilizar los dividendos por segunda vez. La verificación de eventos fue estructural y numérica, sin reconciliación independiente con emisores. El panel es una revisión histórica del proveedor y la selección fija del universo introduce una posible limitación de supervivencia o selección. [Informe de calidad](../../evidence/stage2/data-quality.json)

**Tabla 1. Particiones cronológicas del panel**

| Partición | Primera sesión | Última sesión | Sesiones | Uso registrado |
|---|---|---|---:|---|
| Desarrollo y entrenamiento | 2015-01-02 | 2021-12-31 | 1.763 | Ajuste por ventana y entrenamiento de las políticas para validación |
| Validación independiente | 2022-01-03 | 2023-12-29 | 501 | Evaluación común de las cuatro estrategias en 500 intervalos |
| Prueba final reservada | 2024-01-02 | 2024-12-31 | 252 | Ingestión y control de calidad. Bloqueada para ajuste, selección y evaluación de desempeño |

Nota. El SHA-256 del panel empleado es `bfc0b8e79e60e0c5dfaff18c52af7a113734a4c2be7fd4c849949deec3d4ebd0`. El informe del estudio y el informe histórico registran el mismo identificador. [Particiones y verificación](../../evidence/stage2/historical-validation.json) · [Registro del estudio](../../evidence/stage3/historical-study.json)

## Condiciones experimentales

Las cuatro estrategias partieron de 10.000 USD simulados en efectivo, con rebalanceo diario, exposición compradora, suma de pesos igual a uno y ausencia de apalancamiento. La ventana informativa común fue de 60 sesiones y la tasa libre de riesgo anual se fijó en 0 %. Los objetivos de cada rebalanceo se determinaron con información disponible hasta el cierre de la sesión anterior. La simulación utilizó el cierre ajustado de la sesión de rebalanceo para contabilizar la asignación y el cierre siguiente para valorarla. Se aplicaron diez puntos básicos sobre el volumen negociado en cada rebalanceo, con ajuste autofinanciado de los pesos y sin liquidación terminal. Estas son convenciones contables de una simulación con posiciones fraccionarias. [Protocolo](../../../experiments/stage3-protocol.json) · [Implementación contable](../../../packages/portfolio_core/accounting.py)

Equal-weight asignó un objetivo de 10 % a cada activo. El benchmark basado en Markowitz (1952) recalculó las medias y covarianzas de la ventana histórica y resolvió un problema de media-varianza con aversión al riesgo de 5. El optimizador empleó SLSQP, una regularización de covarianza de `1e-8`, restricciones de posiciones largas y normalización a suma uno. En la validación histórica su mecanismo de contingencia hacia pesos iguales se activó cero veces. Las políticas PPO (Schulman et al., 2017) y DDPG (Lillicrap et al., 2015) utilizaron el mismo entorno Gymnasium. La observación de 610 valores incorpora 600 retornos logarítmicos rezagados y diez pesos objetivo previos. La acción continua de diez dimensiones se proyecta al símplex. La transformación por activo se ajusta sobre la partición de entrenamiento correspondiente y se congela para la inferencia. [Validación del benchmark](../../evidence/stage2/historical-validation.json) · [Protocolo PPO y DDPG](../../RL-RESEARCH.md)

La recompensa usada fue el retorno logarítmico neto, con costos incluidos en la valoración. El coeficiente de la penalización de riesgo se fijó en cero. Por tanto, la penalización explícita de volatilidad contemplada en el diseño de Fase 3 y el análisis de sensibilidad a costos quedan como verificaciones pendientes. Los modelos se evaluaron con inferencia determinista, sin actualización de parámetros ni ruido exploratorio. El documento de Fase 3 contempló también 2022–2023 para seleccionar configuraciones. El protocolo ejecutado restringió esa selección a períodos anteriores y destinó 2022–2023 a medir las configuraciones congeladas. [Protocolo ejecutado](../../../experiments/stage3-protocol.json) · [Registro de selección](../../evidence/stage3/historical-study.json)

## Selección temporal walk-forward

La evaluación de desarrollo empleó ventanas de entrenamiento expansivas. En el primer pliegue se ajustaron los modelos hasta 2018-12-31 y se evaluaron del 2019-01-02 al 2019-12-31. En el segundo, se ajustaron hasta 2020-12-31 y se evaluaron del 2021-01-04 al 2021-12-31. Los dos pliegues tuvieron 251 intervalos evaluados cada uno. Se probaron dos tasas por algoritmo con semilla 42 y 2.048 pasos por combinación. El criterio preespecificado fue el promedio simple de Sharpe de ambos pliegues, con desempate lexicográfico si procedía. Las ocho corridas cubren los dos algoritmos, las dos tasas de cada uno y los dos pliegues. [Registro de pliegues y selección](../../evidence/stage3/historical-study.json)

**Tabla 2. Selección de tasa de aprendizaje en el período de desarrollo**

| Algoritmo | Tasa | Sharpe 2019 | Sharpe 2021 | Media | Selección |
|---|---:|---:|---:|---:|---|
| PPO | 0,0003 | 1,4523 | 0,7680 | 1,1102 | Alternativa |
| PPO | 0,0001 | 2,4068 | 1,8294 | 2,1181 | Seleccionada |
| DDPG | 0,0003 | −0,5529 | −1,2978 | −0,9254 | Alternativa |
| DDPG | 0,0010 | −0,0343 | −0,7074 | −0,3709 | Seleccionada |

Nota. La tasa DDPG seleccionada fue la mejor entre las dos ensayadas bajo el criterio registrado, con media de Sharpe negativa. La malla acotada y el uso de una sola semilla de desarrollo limitan el alcance de la selección. El rendimiento de los pliegues caracteriza a las corridas de 2.048 pasos y no es directamente atribuible a los modelos posteriores con presupuestos de entrenamiento mayores. [Valores y configuraciones de origen](../../evidence/stage3/historical-study.json)

## Entrenamiento y puntos de restauración

Los seis modelos destinados a validar se ajustaron sobre las 1.763 sesiones de 2015–2021 con semillas 7, 42 y 123 para cada algoritmo. El estudio se ejecutó en CPU, con un hilo de PyTorch y un proceso de entrenamiento simultáneo. Los manifiestos declaran Gymnasium 1.4.0, Stable-Baselines3 2.9.2, PyTorch 2.15.0+cpu y NumPy 2.4.6. Los límites fueron 600 segundos y 2.048 MB por trabajo. [Manifiestos de corrida](../../evidence/stage3/historical-study.json)

**Tabla 3. Hiperparámetros de los modelos para validación**

| Parámetro | PPO | DDPG |
|---|---|---|
| Arquitectura MLP | Dos capas de 64 unidades | Dos capas de 64 unidades |
| Tasa seleccionada | 0,0001 | 0,0010 |
| Descuento gamma | 0,99 | 0,99 |
| Tamaño de lote | 64 | 64 |
| Presupuesto por semilla | 16.384 pasos | 8.192 pasos |
| Configuración propia | Rollout 256, cinco épocas, GAE 0,95, clipping 0,20, coeficiente de entropía 0, coeficiente de valor 0,50 y norma máxima de gradiente 0,50 | Búfer 20.000, aprendizaje tras 256 pasos, tau 0,005, frecuencia de entrenamiento 1, un paso de gradiente por actualización y desviación del ruido 0,10 |
| Cadencia de guardado | Cada 4.096 pasos, cuatro puntos por semilla | Cada 4.096 pasos, dos puntos por semilla |

Nota. Se consignan los hiperparámetros activos del algoritmo en cada ejecución. El estudio compara las configuraciones registradas, con presupuestos de pasos diferentes. [Configuraciones y checkpoints](../../evidence/stage3/historical-study.json)

**Tabla 4. Tiempos y memoria de los seis entrenamientos para validación**

| Algoritmo | Semilla | Tiempo de entrenamiento (s) | Pico de RSS muestreado (MiB) |
|---|---:|---:|---:|
| PPO | 7 | 34,13 | 358,98 |
| PPO | 42 | 34,03 | 359,26 |
| PPO | 123 | 35,64 | 359,70 |
| DDPG | 7 | 64,08 | 449,76 |
| DDPG | 42 | 50,73 | 448,25 |
| DDPG | 123 | 154,89 | 444,40 |

Nota. El pico es el máximo observado en muestras de memoria residente del intérprete de entrenamiento. Un primer supervisor registró el proceso lanzador de Windows en vez del intérprete, por lo que se usan las muestras internas y se omiten aquellas lecturas del lanzador. La ejecución inicial de DDPG con semilla 123 se interrumpió tras el paso registrado 2.080 y antes de guardar un punto de restauración. La continuación reutilizó 13 trabajos verificados y repitió esa semilla con la configuración original. La tabla incluye la corrida completada. El estudio principal suma 14 trabajos completados, ocho de selección y seis para validación, además de dos pruebas breves independientes de 256 pasos. [Trazas del estudio](../../evidence/stage3/historical-study.json)

Cada trabajo conserva la configuración, la procedencia del panel, el estado del normalizador y las huellas SHA-256 de los archivos del modelo. DDPG conserva también el búfer de repetición. Como comprobación operativa separada, la API restauró un punto de PPO y uno de DDPG y continuó de 256 a 512 pasos. Esto comprueba carga y continuidad de entrenamiento, con reinicio de episodio y flujo aleatorio según el protocolo de reanudación. [Restauración por API](../../evidence/stage3/api-checkpoints.json) · [Convenciones de reanudación](../../STAGE3-CONTRACTS.md)

## Comparación en validación 2022–2023

El rendimiento diario neto es la razón entre valores consecutivos de la cartera menos uno. El retorno acumulado es la variación del capital entre el inicio y el final de la simulación. La rentabilidad anualizada compuesta (CAGR) aplica el exponente 252/500 a la razón final sobre inicial. La volatilidad anualizada utiliza la desviación estándar muestral de los retornos diarios y el factor raíz de 252. El Sharpe emplea el exceso de rendimiento diario medio sobre la tasa libre de riesgo diaria, dividido por la volatilidad diaria y multiplicado por raíz de 252. El máximo drawdown es la magnitud positiva de la mayor caída respecto de un máximo previo. El costo total es la suma de cargos en USD simulados. La rotación total es la suma del volumen negociado en cada rebalanceo como múltiplo del capital previo al rebalanceo. [Cálculo de métricas](../../../packages/portfolio_core/accounting.py) · [Estadísticas de investigación](../../../packages/portfolio_evaluation/statistics.py)

**Tabla 5. Resultados netos de las cuatro estrategias en 500 intervalos**

| Estrategia | Retorno acumulado | CAGR | Volatilidad anual | Sharpe | Máx. drawdown | Capital final (USD) | Costos (USD) | Rotación total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Equal-weight | +14,49 % | +7,06 % | 14,27 % | 0,5492 | 14,70 % | 11.448,86 | 50,82 | 5,05 |
| Markowitz | −31,00 % | −17,06 % | 24,50 % | −0,6403 | 37,76 % | 6.900,21 | 1.260,41 | 161,02 |
| PPO, media de tres semillas | −13,94 % | −7,29 % | 14,88 % | −0,4340 | 23,00 % | 8.606,07 | 3.008,48 | 342,38 |
| DDPG, media de tres semillas | −42,56 % | −24,39 % | 16,69 % | −1,6116 | 44,38 % | 5.744,44 | 3.830,52 | 537,94 |

Nota. Las medias de PPO y DDPG son medias aritméticas de cada métrica calculada por separado sobre las tres semillas, no métricas de una cartera agregada. Los retornos, el Sharpe, la volatilidad, el drawdown, el capital final y los costos de los dos benchmarks coinciden con los objetos de métricas de la validación histórica previa. Los valores de las tablas se calcularon y redondearon a partir de los artefactos originales. [Registro de métricas y semillas](../../evidence/stage3/historical-study.json) · [Validación histórica de benchmarks](../../evidence/stage2/historical-validation.json)

**Tabla 6. Resultados individuales de las políticas PPO y DDPG**

| Estrategia | Semilla | Retorno acumulado | CAGR | Volatilidad anual | Sharpe | Máx. drawdown | Capital final (USD) | Costos (USD) | Rotación total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PPO | 7 | −13,42 % | −7,00 % | 15,00 % | −0,4090 | 22,45 % | 8.658,15 | 3.030,37 | 344,60 |
| PPO | 42 | −16,27 % | −8,56 % | 15,12 % | −0,5165 | 26,02 % | 8.372,78 | 3.025,35 | 357,58 |
| PPO | 123 | −12,13 % | −6,31 % | 14,51 % | −0,3766 | 20,53 % | 8.787,29 | 2.969,71 | 324,95 |
| DDPG | 7 | −45,98 % | −26,68 % | 15,08 % | −1,9812 | 47,49 % | 5.401,83 | 3.702,82 | 514,09 |
| DDPG | 42 | −40,32 % | −22,91 % | 16,47 % | −1,4964 | 42,84 % | 5.967,51 | 4.184,58 | 596,49 |
| DDPG | 123 | −41,36 % | −23,59 % | 18,53 % | −1,3572 | 42,82 % | 5.863,99 | 3.604,16 | 503,24 |

Nota. La desviación estándar muestral entre semillas fue de 2,12 puntos porcentuales en el retorno acumulado de PPO y 3,01 en DDPG. Para Sharpe fue de 0,0732 y 0,3276, respectivamente. Las semillas comparten el mismo camino de precios y reflejan sensibilidad a la inicialización. [Estadísticas por semilla](../../evidence/stage3/historical-study.json)

## Reproducibilidad y alcance de la evidencia

Cada benchmark reprodujo sus resultados en dos repeticiones idénticas. Para las políticas se rehicieron dos corridas breves con la misma semilla 42, datos, versiones y presupuesto de 256 pasos. Coincidieron exactamente los tensores de política, el normalizador, los 500 vectores de acción y asignaciones de validación, los 501 valores de la curva patrimonial y las métricas finales. El artefacto identifica 13 tensores para PPO y 24 para DDPG, junto con sus huellas de referencia y repetición. La comprobación se limita a las corridas breves realizadas en el mismo entorno de CPU. El reporte del estudio permite rastrear además los identificadores, huellas y métricas de los seis entrenamientos con mayor presupuesto. [Prueba de reproducibilidad](../../evidence/stage3/reproducibility.json) · [Artefactos del estudio](../../evidence/stage3/historical-study.json)

## Discusión

Equal-weight presentó el mayor retorno acumulado, el mayor Sharpe y la menor pérdida máxima del período observado. PPO mejoró el retorno neto, el Sharpe y el drawdown frente a Markowitz en este ejercicio, mientras DDPG registró los resultados menos favorables en esas tres métricas. Las seis políticas aprendidas terminaron con retornos acumulados negativos. El signo negativo se mantiene en el informe porque mide el desempeño del protocolo que se ejecutó bajo condiciones comunes.

La rotación permite examinar una explicación de los costos. Equal-weight sostuvo un objetivo fijo y requirió menos ajustes frente a la deriva de precios. Las políticas aprendidas generaron objetivos más variables. A diez puntos básicos, los costos medios de PPO y DDPG ascendieron a 3.008,48 y 3.830,52 USD, respectivamente. Este registro muestra un mecanismo de fricción asociado al volumen, con el efecto de los costos ya incorporado al retorno neto. Para estimar cuánto cambiaría el orden de las estrategias con otras comisiones o restricciones de rebalanceo se requiere un estudio de sensibilidad independiente. [Métricas de rotación y costos](../../evidence/stage3/historical-study.json)

El estudio incluyó un bootstrap pareado exploratorio con la semilla 42, 500 retornos diarios por comparación, bloques de 20 sesiones y 1.000 remuestreos. Los intervalos del 95 % para la diferencia de retornos medios netos anualizados frente a equal-weight fueron de −20,78 a −10,73 puntos porcentuales para PPO y de −45,68 a −19,86 para DDPG. La estadística corresponde a una diferencia de medias diarias anualizadas, distinta de la diferencia entre CAGR. Estos intervalos dependen de las políticas y fechas concretas, no incorporan la incertidumbre de otros regímenes y carecen de corrección por comparaciones múltiples. La evaluación confirmatoria requeriría un protocolo fijado antes del acceso a 2024. [Registro del bootstrap](../../evidence/stage3/historical-study.json)

Los retornos demuestran la capacidad de comparar configuraciones en una simulación común. La conclusión sobre desempeño se restringe a diez instrumentos seleccionados, dos pliegues de desarrollo, tres semillas por algoritmo y una ventana de validación. La simulación de precios ajustados y costos proporcionales deja fuera impacto de mercado, ejecuciones parciales, latencias y deslizamiento específico por activo. El Agent Desk conserva por separado su evidencia de propuestas y decisiones exploratorias. Esa evidencia corresponde a una fecha y a una asignación hipotética desde efectivo, sin curva de desempeño. [Histórico del estudio](../../evidence/stage3/historical-study.json) · [Evidencia del Agent Desk](../../evidence/stage4/historical-agent-runs.json)

## Referencias de los métodos

- Lillicrap, T. P., Hunt, J. J., Pritzel, A., Heess, N., Erez, T., Tassa, Y., Silver, D., & Wierstra, D. (2015). *Continuous control with deep reinforcement learning* [Prepublicación]. arXiv. [Registro](https://arxiv.org/abs/1509.02971).
- Markowitz, H. (1952). Portfolio selection. *The Journal of Finance, 7*(1), 77–91. [DOI editorial](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x).
- Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). *Proximal policy optimization algorithms* [Prepublicación]. arXiv. [Registro](https://arxiv.org/abs/1707.06347).
