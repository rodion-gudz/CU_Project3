**Ответь на вопросы:**

1. Какие графики лучше всего подходят для визуализации погодных данных? Объяснии свой выбор.
2. Как можно улучшить пользовательский опыт с помощью интерактивных графиков?

**Ответы:**

1. В коде используется линейный график (Scatter в plotly) для отображения прогноза погоды (температура, осадки) на несколько дней вперед. Линейные графики позволяют легко увидеть тенденции в изменении температуры и других параметров, таких как интенсивность осадков, по временной оси

Линейный график четко показывает ежедневные изменения параметров на протяжении прогнозируемого периода (3, 5, или 7 дней). Линии помогают визуализировать тенденции в данных, такие как потепление или похолодание, а также периоды с интенсивными осадками 

2. **Переключение временных интервалов**. С помощью `dcc.RadioItems` в интерфейсе пользователь может выбирать временной интервал прогноза (например, 3, 5 или 7 дней), с помощью `dcc.Dropdown` можно **выбирать между отображением максимальной и минимальной температуры, а также интенсивности осадков**

Эти элементы делают использование сервиса более удобным и позволяют пользователю гибко настраивать отображение данных в зависимости от своих потребностей
