Documentación del Framework de Interoperabilidad de Asistentes Virtuales Edu-Assistant-Framework
1. Visión General
Objetivo
Crear un framework open-source que permita la interoperabilidad entre múltiples asistentes virtuales heterogéneos, permitiendo:

Usar asistentes existentes sin modificar su código fuente

Orquestar consultas entre diferentes asistentes

Crear un ecosistema extensible para educación

Arquitectura Actual
text
┌─────────────────────────────────────────────────────────────┐
│                    APLICACIÓN CLIENTE                        │
│  (Frontend, App móvil, Sistema educativo, etc.)             │
└──────────────────────────────┬──────────────────────────────┘
                                │
┌──────────────────────────────▼──────────────────────────────┐
│                    ORQUESTADOR CENTRAL                        │
│  • Recibe consultas                                          │
│  • Determina el mejor asistente                              │
│  • Combina múltiples respuestas                              │
│  • Maneja contexto de conversación                           │
└──────────────────────────────┬──────────────────────────────┘
                                │
    ┌───────────┬──────────────┼───────────────┬───────────┐
    │           │              │               │           │
┌───▼───┐ ┌─────▼────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──▼─────┐
│Wrapper│ │  Wrapper  │ │   Wrapper   │ │   Wrapper   │ │Wrapper │
│ OpenAI│ │Dialogflow │ │   Custom    │ │  Wolfram    │ │  ...   │
└───┬───┘ └─────┬────┘ └──────┬──────┘ └──────┬──────┘ └──┬─────┘
    │           │              │               │           │
┌───▼───┐ ┌─────▼────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──▼─────┐
│Asist. │ │ Asistente │ │  Asistente  │ │  Asistente  │ │Asist.  │
│OpenAI │ │Dialogflow │ │   Local     │ │   Alpha     │ │  ...   │
└───────┘ └───────────┘ └─────────────┘ └─────────────┘ └────────┘
2. Diagramas del Sistema
Diagrama de Secuencia - Flujo Normal
Diagrama de Componentes
text
┌─────────────────────────────────────────────────────────────┐
│                    COMPONENTES DEL FRAMEWORK                 │
├─────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  INTERFAZ    │    │  REGISTRO    │    │  DISPATCHER  │  │
│  │   COMÚN      │◄──►│   DE         │◄──►│   DE         │  │
│  │              │    │  CAPACIDADES │    │  CONSULTAS   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         △                           △               △       │
│         │                           │               │       │
│  ┌──────┴──────┐            ┌───────┴──────┐        │       │
│  │  GESTOR DE  │            │  ORQUESTADOR │        │       │
│  │  CONTEXTO   │            │  INTELIGENTE │        │       │
│  └─────────────┘            └──────────────┘        │       │
│         △                                           │       │
│         │                                    ┌──────┴──────┐│
│  ┌──────┴──────┐                            │   ADAPTADOR  ││
│  │  BASE DE    │                            │    COMÚN     ││
│  │  DATOS      │                            └──────┬───────┘│
│  └─────────────┘                                    △       │
│                                              ┌──────┴──────┐│
│                                              │   WRAPPERS   ││
│                                              │  ESPECÍFICOS ││
│                                              └──────────────┘│
└─────────────────────────────────────────────────────────────┘
3. Cómo Funciona Actualmente
Flujo de Procesamiento
Recepción de Consulta: El orquestador recibe una consulta del usuario

Análisis de Intención: Determina qué tipo de asistente es más adecuado

Selección de Asistente: Basado en capacidades registradas

Delegación: Envía la consulta al wrapper correspondiente

Traducción: El wrapper convierte al formato del asistente específico

Ejecución: Se comunica con el asistente real

Post-procesamiento: Se formatea la respuesta al estándar común

Entrega: Se devuelve al cliente

4. Pasos para Insertar un Nuevo Asistente
Paso 1: Crear la Estructura del Wrapper
text
edu-assistant-framework/
└── wrappers/
    └── nuevo_asistente/          # Nombre del nuevo asistente
        ├── __init__.py
        ├── wrapper.py            # Clase principal del wrapper
        ├── config.py             # Configuración específica
        ├── requirements.txt      # Dependencias específicas
        └── README.md             # Documentación específica


        Limitaciones
No soporta streaming

Límite de 60 peticiones por minuto

Solo texto (no imágenes)

5. Protocolo de Comunicación Estandarizado
Formato de Entrada
json
{
  "query": "texto de la consulta",
  "context": {
    "user_id": "identificador único",
    "session_id": "id de sesión",
    "course": "materia o curso",
    "level": "nivel educativo",
    "previous_responses": [],
    "preferences": {}
  },
  "parameters": {
    "max_tokens": 500,
    "temperature": 0.7,
    "preferred_assistants": [],
    "response_format": "text"
  }
}
Formato de Salida
json
{
  "success": true,
  "assistant": "nombre_del_asistente",
  "response": {
    "text": "respuesta en texto",
    "confidence": 0.95,
    "sources": [
      {"title": "Fuente 1", "url": "https://..."},
      {"title": "Fuente 2", "url": "https://..."}
    ],
    "suggestions": ["sugerencia 1", "sugerencia 2"]
  },
  "metadata": {
    "processing_time": 1.23,
    "tokens_used": 150,
    "model": "modelo_usado",
    "cost": 0.001
  },
  "raw_response": {}
}