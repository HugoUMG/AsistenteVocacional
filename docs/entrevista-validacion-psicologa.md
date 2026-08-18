# Guía de entrevista con la psicóloga (validación del sistema)

Preguntas organizadas por bloque. El objetivo es validar: (1) el instrumento
Holland/O*NET tal como se usa, (2) el examen psicométrico propio de 100
ítems, (3) las 4 preguntas fijas y el chat adaptativo, (4) el dashboard y la
forma en que se presenta el resultado al alumno, (5) límites éticos y de uso
responsable.

## 1. Sobre el enfoque general

1. ¿El flujo de tres modos (solo chat, solo Holland, Holland y luego chat)
   tiene sentido desde su experiencia con orientación vocacional real, o
   sobra/falta algún modo?
2. ¿Con qué edad y grado escolar (13-17 años, según el psicométrico) se
   siente cómoda validando este instrumento? ¿Hay un piso de edad por debajo
   del cual no lo recomendaría?
3. ¿Qué tan cómoda está con que el motor de recomendación sea un modelo de
   lenguaje (Gemini) conversando con el alumno, en vez de un test cerrado
   tradicional?
4. ¿Falta algún constructo vocacional relevante que hoy el sistema no mide
   (valores, contexto familiar, situación económica, disponibilidad de la
   carrera en su departamento)?

## 2. Sobre Holland / RIASEC (O*NET)

5. ¿Está de acuerdo en que el RIASEC (intereses) y el examen de 100 ítems
   (personalidad + razonamiento) son instrumentos complementarios y no
   redundantes, o considera que falta un tercer instrumento?
6. El sistema mide que Holland **no mueve el ranking final** de carreras
   (documentado en `experiments/holland-en-chat.md` y
   `experiments/holland-estructura.md`), solo personaliza la conversación.
   ¿Le parece aceptable que el resultado de Holland no tenga peso directo en
   la recomendación, o esperaría que sí lo tuviera?
7. Las ocupaciones que muestra O*NET son del mercado laboral de EE. UU., no
   un catálogo guatemalteco. ¿Cómo debería explicarse eso al alumno para que
   no lo confunda con "estas son mis opciones"?
8. ¿Hay algo del Interest Profiler que, en su experiencia clínica/educativa,
   suela generar interpretaciones erróneas en adolescentes (por ejemplo,
   sobre-identificarse con el código de 3 letras)?

## 3. Sobre el examen psicométrico de 100 ítems

9. ¿Reconoce el banco de ítems (personalidad, razonamiento lógico, verbal,
   numérico) como equivalente a instrumentos que usted ya utiliza, o le
   parece un banco ad hoc que necesita revisión?
10. El baremo actual es **ilustrativo** (una tabla de anclas interpolada, no
    una muestra normativa real) y así se lo dice al alumno en el pie de
    resultados. ¿Tiene acceso a un baremo real para adolescentes
    guatemaltecos, o a uno que pueda recomendar?
11. El índice de "coherencia" compara 6 pares de ítems del mismo rasgo y
    marca alerta si divergen ≥3 puntos en la escala Likert. El propio equipo
    documentó que **una sola divergencia no es concluyente** (puede ser
    honesta). ¿Le parece un umbral razonable o preferiría otro criterio?
12. La alerta de deseabilidad social exige el máximo en los 8 ítems
    especiales para dispararse (bajó de 21% a 0.7% de falsos positivos en
    simulación al subir el umbral). ¿Coincide con ese criterio o lo
    consideraría demasiado laxo/estricto?
13. ¿La distinción entre "tendencia central" (responder neutral a casi todo)
    y "coherencia" tiene sentido para usted como dos señales distintas, o las
    fusionaría en una sola alerta?
14. ¿Los ítems de razonamiento (lógico/verbal/numérico) le parecen apropiados
    en dificultad y redacción para el rango de edad del sistema?
15. ¿Qué tan importante es, en su opinión, que el resultado del psicométrico
    algún día pueda cruzarse con la recomendación vocacional (hoy no se
    puede: se guarda solo con `session_id`, sin ligar al mismo alumno)?

## 4. Sobre las 4 preguntas fijas y el chat adaptativo

16. ¿Las 4 preguntas fijas del chat (intereses declarados) capturan lo que
    usted preguntaría primero en una sesión de orientación real?
17. ¿Qué riesgo ve en que un modelo de lenguaje formule preguntas
    "adaptativas" de seguimiento sin supervisión humana en tiempo real?
18. ¿Hay temas sensibles (salud mental, presión familiar, situación
    económica) que el chat debería evitar profundizar, o derivar a una
    persona en vez de seguir preguntando?

## 5. Sobre el dashboard y la comunicación del resultado

19. ¿La forma de presentar el resultado (carreras más afines, por
    institución, con gráficas) comunica bien la incertidumbre, o puede leerse
    como una respuesta más determinista de lo que realmente es?
20. ¿Qué lenguaje o advertencia recomendaría agregar para que el alumno no
    interprete la recomendación como una decisión ya tomada por el sistema?
21. ¿Cómo debería presentarse la limitación del baremo ilustrativo y la
    falta de validación normativa para que un adolescente (o sus padres) la
    entienda sin sentir que el resultado "no vale nada"?

## 6. Ética, límites y uso responsable

22. ¿Qué garantías necesitaría ver (consentimiento, manejo de datos,
    supervisión de un orientador humano) para avalar el uso de este sistema
    con estudiantes reales, aunque sea en fase de prueba?
23. ¿En qué casos el sistema debería recomendar explícitamente hablar con un
    orientador o psicólogo humano en vez de conformarse con el resultado
    digital?
24. ¿Ve algún riesgo de que el alumno reciba una recomendación y la tome como
    diagnóstico clínico o vocacional definitivo, dado que viene de una IA?
25. Desde su rol, ¿qué haría falta documentar o declarar como limitación en
    la tesis para que el uso de estos instrumentos sea éticamente honesto?
