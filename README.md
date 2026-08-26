Proyecto

El sistema de Control de Entregas por Drones es una plataforma de logística urbana donde tres microservicios independientes gestionan el ciclo completo de envío automatizado de paquetes: el Servicio de Pedidos registra las solicitudes, destinos y el peso de cada paquete; el Servicio de Drones administra la flota controlando el estado, porcentaje de batería y la capacidad de carga útil de cada unidad; y el Servicio Despachador actúa como orquestador inteligente evaluando qué dron disponible cumple con los requisitos para asignar el viaje. Todo esto se visualiza en un frontend interactivo en forma de panel de control que permite simular la creación de envíos, la asignación en tiempo real y la liberación del dron tras la entrega, representando un proyecto web con microservicios accesible, visualmente atractivo y fácil de defender ante los profesores en un plazo de 3 a 4 meses.

Además, se desarrollará una plataforma que permita solicitar pedidos de drones para trasladar paquetes. Para eso se ingresará el peso del paquete, distancia a recorrer (punto A al punto B), fecha de entrega, categoría del paquete (frágil, estándar), importancia (si es urgente pagar más). También se especificará qué es el paquete.

Límites del sistema (qué está dentro y qué fuera)
Alcances funcionales y no funcionales
Objetivos específicos y medibles (funcionalidades, métricas de calidad, criterios de aceptación)
Límites
Dentro:
Inicio de sesión de usuario (creación de cuentas y autenticación) 
Usuario: hacer pedidos, ver estado de pedidos, realizar el pago
Operador: ver flota de drones y estado, manejar las solicitudes de pedidos, modificar página web
Formulario de solicitud de pedidos (usuario): peso, categoría, importancia, destino, origen
Calculadora de tarifas (operador): calcula el costo del envío según la distancia, el peso del paquete y los recargos 
Administración de drones (operador): modelo del dron, capacidad de carga, batería, estado operativo
Mapa Interactivo (usuario): Integración de un mapa 2D (usando librerías gratuitas como Leaflet.js o OpenStreetMap) para marcar el Punto A (Origen) y Punto B (Destino).  
Arquitectura de Microservicios: Tres servicios independientes (Pedidos, Drones, Despachador) comunicados por API REST (JSON).
Bases de Datos Locales: Persistencia de datos para cada servicio (utilizando PostgreSQL, MySQL o SQLite).
Entorno de Ejecución: Despliegue y ejecución local unificada mediante Docker / Docker Compose.



Fuera: app móvil nativa, chat en tiempo real, notificaciones push, nube, pasarelas de pago reales, rastreo GPS en tiempo real, rutas 3D y evasión de obstáculos   

Alcances
Funcionales:
1. Módulo de Autenticación y Usuarios
Gestión de Cuentas: Registro e inicio de sesión de usuarios mediante credenciales seguras.
Roles y Permisos:
Cliente: Acceso al formulario de solicitud, cotizador, calendario personal y rastreo simulado de envíos.
Operador: Acceso a la gestión de la flota, control de estados de drones y panel de monitoreo global de despachos.
2. Módulo de Solicitud de Envíos y Cotización (Cliente)
Alta de Envíos: Formulario para registrar una solicitud especificando:
Descripción/Detalle del paquete (qué se transporta).
Peso del paquete.
Fecha programada de entrega.
Categoría del paquete (Frágil, Estándar).
Nivel de urgencia / Importancia (Normal, Urgente).
Selección Geográfica en Mapa: Marcación interactiva del Punto A (Origen) y Punto B (Destino) sobre el mapa.
Cotizador de Tarifas: Cálculo automático del valor del envío antes de confirmar, aplicando la fórmula interna de distancia, peso base y recargos opcionales (fragilidad o urgencia).
Calendario de Entregas: Vista de agenda interactiva para consultar los envíos agendados por fecha.
3. Módulo de Gestión de Flota de Drones (Operador)
Registro de Unidades: Alta y edición de drones especificando modelo y capacidad máxima de carga útil.
Telemetría Simulada: Control en tiempo real del porcentaje de batería y estado operacional (Disponible, En Camino, Cargando).
Mantenimiento Operativo: Posibilidad de cambiar el estado de un dron manualmente para recargar batería o simular mantenimiento.
4. Módulo Orquestador de Despacho (Lógica de Negocio)
Actualización Automática de Estados: Cambio simultáneo en la base de datos de Pedidos (EN_CAMINO) y Drones (EN_MISION).
Gestión de Rechazos: Emisión de alertas claras cuando ningún dron cumple los requisitos físicos para el pedido.
5. Visualizador Interactivo en Frontend
Confirmación de Entrega: Botón de simulación para marcar el paquete como ENTREGADO, liberando automáticamente el dron de vuelta a estado DISPONIBLE.
No funcionales:
1. Arquitectura y Desacoplamiento
Arquitectura de Microservicios: División del sistema en 3 servicios independientes (Pedidos, Drones y Despachador).
Bases de Datos Aisladas: Cada microservicio gestiona su propia base de datos (o archivo de persistencia) sin consultas directas cruzadas entre tablas de otros servicios.
Comunicación Estándar: Integración exclusiva a través de peticiones HTTP/REST estructuradas en formato JSON.
2. Rendimiento y Eficiencia
Tiempo de Respuesta: Los endpoints de la API deben responder en menos de 1.5 segundos en entorno local.
Cálculo Inmediato: La cotización del envío debe mostrarse instantáneamente al seleccionar los puntos en el mapa y cargar el peso.
3. Usabilidad e Interfaz (UX/UI)
Diseño Limpio y Adaptativo (Responsive): Interfaz web orientada a paneles de control (dashboards) logísticos, accesible desde navegadores modernos (Chrome, Firefox, Edge).
Feedback Visual: Uso de estados por colores (Verde: Disponible/Entregado, Amarillo: En Misión/En Camino, Rojo: Sin Batería/Rechazado).
4. Portabilidad y Despliegue
Contenerización: Toda la solución (frontend, microservicios y bases de datos) se ejecutará mediante Docker Compose, permitiendo levantar el proyecto completo con un único comando durante las presentaciones.
5. Mantenibilidad y Calidad de Código
Manejo Homogéneo de Errores: Respuestas de error estandarizadas indicando código HTTP (400, 404, 500), timestamp y mensaje descriptivo.
Código Estructurado: Separación clara de rutas, controladores y modelos dentro de



Objetivos
1. Arquitectura de Microservicios Backend
Específico: Desarrollar 3 microservicios backend independientes (Pedidos, Drones y Despachador) exponiendo sus respectivos endpoints RESTful para cubrir el ciclo de vida completo del envío.
Medible: Desarrollar e integrar exitosamente al menos 10 endpoints HTTP (distribuidos entre métodos GET, POST y PUT) documentados mediante una colección de Postman o Swagger 3.0.
Alcanzable / Relevante: Demuestra el concepto técnico de microservicios y desacoplamiento de bases de datos exigido por las escuelas técnicas.
Temporal: Completar en los primeros 2 meses de desarrollo.
2. Precisión en la Lógica de Despacho (Reglas de Negocio)
Específico: Implementar en el microservicio Despachador un algoritmo de validación que evalúe capacidad de carga útiles y nivel de energía antes de autorizar un vuelo.
Medible: Lograr una tasa de precisión del 100% en las pruebas de asignación:
$\text{Capacidad Dron} \ge \text{Peso Paquete}$
$\text{Batería Dron} \ge 20\%$
Garantizar que el 100% de los intentos de despacho con sobrepeso o batería insuficiente sean rechazados devolviendo un código HTTP 400 Bad Request.
Alcanzable / Relevante: Asegura la calidad de software y correcto manejo de excepciones en la lógica del sistema.
Temporal: Validado mediante pruebas unitarias/de integración al finalizar el Mes 2.
3. Frontend Interactivo y Experiencia de Usuario
Específico: Diseñar e integrar un Dashboard Web en el frontend que se conecte a los 3 microservicios backend.
Medible: Construir 4 vistas/módulos principales:
Formulario de Cotización y Solicitud (con selector A/B en mapa 2D).
Panel de Control de la Flota de Drones.
Consola de Despacho y Simulador de Vuelo.
Calendario / Agenda de Entregas Programadas.
Alcanzable / Relevante: Otorga un alto valor visual e interactivo para defender el proyecto ante los profesores.
Temporal: Finalizar el desarrollo de la interfaz durante el Mes 3.
4. Rendimiento y Tiempo de Respuesta
Específico: Optimizar las consultas a la base de datos y la comunicación inter-servicios para garantizar fluidez en la interfaz.
Medible: Lograr que el 90% de las peticiones REST (cotización de tarifas, consulta de flota y asignación) respondan en un tiempo menor a 1.5 segundos ($< 1500\text{ ms}$) en pruebas de entorno local.
Alcanzable / Relevante: Garantiza que el sistema se pueda probar fluidamente durante la exposición en vivo sin demoras molestas.
Temporal: Medido y ajustado a principios del Mes 4.
5. Contenerización y Despliegue Unificado
Específico: Empaquetar cada microservicio, el frontend y las bases de datos en contenedores individuales de Docker.
Medible: Generar un archivo docker-compose.yml funcional que permita orquestar y levantar el 100% de la infraestructura con un único comando (docker-compose up) en un tiempo máximo de 3 minutos en la computadora de exposición.
Alcanzable / Relevante: Facilita la portabilidad y evita el clásico problema de "en mi máquina sí funcionaba".




