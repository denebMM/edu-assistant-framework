# ./assistants/deeppavlov-nlu/wrapper.py - VERSIÓN MEJORADA
from fastapi import FastAPI, Request
from transformers import pipeline
import uvicorn
import re

app = FastAPI(title="Transformers QA Educativo")

try:
    print("🔄 Cargando modelo transformers educativo...")
    # Usar un modelo más robusto y multilingüe
    qa_pipeline = pipeline(
        "question-answering", 
        model="mrm8488/bert-spanish-cased-finetuned-squad",  # Modelo en español
        tokenizer="mrm8488/bert-spanish-cased-finetuned-squad"
    )
    print("✅ Modelo transformers en español cargado correctamente")
except Exception as e:
    print(f"❌ Error al cargar el modelo español: {e}")
    try:
        # Fallback a modelo inglés
        qa_pipeline = pipeline(
            "question-answering", 
            model="distilbert-base-cased-distilled-squad"
        )
        print("✅ Modelo transformers en inglés cargado correctamente")
    except Exception as e2:
        print(f"❌ Error al cargar modelo inglés: {e2}")
        print("⚠️  Usando respuestas predefinidas...")
        qa_pipeline = None

# Base de conocimiento educativo MEJORADA
CONTEXTOS = {
    "es": """
    Albert Einstein fue un físico alemán nacido en 1879. Desarrolló la teoría de la relatividad, que revolucionó la física moderna. Recibió el Premio Nobel de Física en 1921.
    
    La fotosíntesis es el proceso mediante el cual las plantas verdes y otros organismos convierten la energía luminosa en energía química. Durante la fotosíntesis, las plantas absorben dióxido de carbono (CO2) y agua (H2O) para producir glucosa y liberar oxígeno (O2).
    
    La mitosis es el proceso de división celular por el cual una célula madre se divide en dos células hijas genéticamente idénticas. Este proceso es fundamental para el crecimiento y la reparación de tejidos en los organismos multicelulares.
    
    Las matemáticas son la ciencia que estudia las propiedades de los números, las estructuras, el espacio y los cambios. Incluye áreas como aritmética, álgebra, geometría y cálculo.
    
    El álgebra es una rama de las matemáticas que utiliza símbolos y letras para representar números y cantidades en fórmulas y ecuaciones. El álgebra permite resolver problemas que involucran cantidades desconocidas.
    
    La Revolución Francesa fue un período de transformación política y social en Francia que comenzó en 1789 con la toma de la Bastilla. Este evento marcó el fin del Antiguo Régimen y el inicio de la era moderna en Europa.
    
    El agua es una sustancia química cuya molécula está compuesta por dos átomos de hidrógeno y uno de oxígeno (H2O). Es esencial para la vida en la Tierra.
    
    La Tierra es el tercer planeta del sistema solar, el único conocido que alberga vida. Tiene una atmósfera compuesta principalmente de nitrógeno y oxígeno.
    
    Cristóbal Colón fue un explorador y navegante italiano que completó cuatro viajes a través del Océano Atlántico bajo los auspicios de los Reyes Católicos de España. Sus expediciones iniciaron la colonización europea de América.
    """,
    
    "en": """
    Albert Einstein was a German-born physicist born in 1879. He developed the theory of relativity, which revolutionized modern physics. He received the Nobel Prize in Physics in 1921.
    
    Photosynthesis is the process by which green plants and some other organisms convert light energy into chemical energy. During photosynthesis, plants absorb carbon dioxide (CO2) and water (H2O) to produce glucose and release oxygen (O2).
    
    Mitosis is the process of cell division by which a mother cell divides into two genetically identical daughter cells. This process is fundamental for growth and tissue repair in multicellular organisms.
    
    Mathematics is the science that studies the properties of numbers, structures, space, and change. It includes areas such as arithmetic, algebra, geometry, and calculus.
    
    Algebra is a branch of mathematics that uses symbols and letters to represent numbers and quantities in formulas and equations. Algebra allows solving problems involving unknown quantities.
    
    The French Revolution was a period of political and social transformation in France that began in 1789 with the Storming of the Bastille. This event marked the end of the Ancien Régime and the beginning of the modern era in Europe.
    
    Water is a chemical substance whose molecule is composed of two hydrogen atoms and one oxygen atom (H2O). It is essential for life on Earth.
    
    Earth is the third planet from the Sun, the only known planet to harbor life. It has an atmosphere composed mainly of nitrogen and oxygen.
    
    Christopher Columbus was an Italian explorer and navigator who completed four voyages across the Atlantic Ocean under the auspices of the Catholic Monarchs of Spain. His expeditions initiated the European colonization of the Americas.
    """
}

def detectar_idioma(pregunta: str) -> str:
    """Detección mejorada de idioma"""
    pregunta = pregunta.lower()
    
    # Palabras específicas en español
    es_palabras = ["qué", "cómo", "dónde", "cuándo", "por qué", "quién", "explica", "define", "cuál"]
    
    # Palabras específicas en inglés
    en_palabras = ["what", "how", "where", "when", "why", "who", "explain", "define", "which"]
    
    es_count = sum(1 for palabra in es_palabras if palabra in pregunta)
    en_count = sum(1 for palabra in en_palabras if palabra in pregunta)
    
    # También contar palabras comunes
    es_commons = ["el", "la", "los", "las", "de", "en", "y", "es", "son"]
    en_commons = ["the", "a", "an", "and", "is", "are", "of", "in"]
    
    es_count += sum(1 for palabra in es_commons if palabra in pregunta.split())
    en_count += sum(1 for palabra in en_commons if palabra in pregunta.split())
    
    return "es" if es_count > en_count else "en"

def mejorar_respuesta(pregunta: str, respuesta: str, contexto: str, idioma: str) -> str:
    """Mejora respuestas muy cortas o incompletas"""
    respuesta = respuesta.strip()
    
    # Si la respuesta es muy corta (menos de 10 caracteres)
    if len(respuesta) < 10:
        # Buscar oraciones completas en el contexto que contengan la respuesta
        oraciones = re.split(r'[.!?]+', contexto)
        for oracion in oraciones:
            if respuesta.lower() in oracion.lower() and len(oracion) > 20:
                respuesta = oracion.strip() + "."
                break
    
    # Si todavía es corta, usar respuesta predefinida según el tema
    if len(respuesta) < 15:
        pregunta_lower = pregunta.lower()
        
        if "einstein" in pregunta_lower:
            if idioma == "es":
                return "Albert Einstein fue un físico alemán que desarrolló la teoría de la relatividad y recibió el Premio Nobel de Física en 1921."
            else:
                return "Albert Einstein was a German physicist who developed the theory of relativity and received the Nobel Prize in Physics in 1921."
        
        elif "álgebra" in pregunta_lower or "algebra" in pregunta_lower:
            if idioma == "es":
                return "El álgebra es una rama de las matemáticas que utiliza símbolos y letras para representar números en ecuaciones y fórmulas."
            else:
                return "Algebra is a branch of mathematics that uses symbols and letters to represent numbers in equations and formulas."
        
        elif "h2o" in pregunta_lower or "agua" in pregunta_lower or "water" in pregunta_lower:
            if idioma == "es":
                return "H2O es la fórmula química del agua, compuesta por dos átomos de hidrógeno y uno de oxígeno."
            else:
                return "H2O is the chemical formula for water, composed of two hydrogen atoms and one oxygen atom."
    
    return respuesta

@app.get("/")
async def root():
    return {
        "message": "Transformers QA Educativo funcionando",
        "status": "ok" if qa_pipeline else "degraded"
    }

@app.post("/query")
async def handle_query(request: Request):
    try:
        data = await request.json()
        pregunta = data.get("query", "").strip()
        
        print(f"🔍 Pregunta recibida: '{pregunta}'")
        
        if not pregunta:
            return {"response": "Por favor, envía una pregunta"}
        
        idioma = detectar_idioma(pregunta)
        print(f"🌐 Idioma detectado: {idioma}")
        
        contexto = CONTEXTOS.get(idioma, CONTEXTOS["en"])
        
        # Si no hay pipeline, usar respuestas básicas
        if qa_pipeline is None:
            print("⚠️  Usando respuestas predefinidas (pipeline no disponible)")
            # ... (código existente para respuestas básicas) ...
            return {"response": f"Recibí: '{pregunta}'. Estoy en modo básico."}
        
        # Usar transformers
        print("🔧 Usando pipeline de QA...")
        resultado = qa_pipeline(
            question=pregunta,
            context=contexto,
            max_answer_len=150,
            max_question_len=100
        )
        
        print(f"📊 Resultado del pipeline: {resultado}")
        
        # Extraer respuesta
        respuesta = ""
        if isinstance(resultado, dict):
            respuesta = resultado.get("answer", "").strip()
            score = resultado.get("score", 0)
            print(f"📈 Score de confianza: {score:.4f}")
            
            # Si el score es muy bajo, la respuesta probablemente sea incorrecta
            if score < 0.1:
                print("⚠️  Score bajo, respuesta podría ser incorrecta")
        
        print(f"✅ Respuesta cruda extraída: '{respuesta}'")
        
        # Mejorar la respuesta si es necesario
        respuesta = mejorar_respuesta(pregunta, respuesta, contexto, idioma)
        print(f"✨ Respuesta mejorada: '{respuesta}'")
        
        if not respuesta or len(respuesta) < 2:
            if idioma == "es":
                respuesta = "No encontré información específica sobre ese tema en mi base de conocimiento."
            else:
                respuesta = "I didn't find specific information about that topic in my knowledge base."
        
        return {
            "response": respuesta,
            "language": idioma,
            "model": "transformers"
        }
        
    except Exception as e:
        print(f"❌ Error en handle_query: {e}")
        import traceback
        traceback.print_exc()
        return {"response": f"Error procesando la pregunta. Por favor, intenta con otra formulación.", "error": True}

@app.get("/health")
async def health():
    return {
        "status": "healthy" if qa_pipeline is not None else "degraded",
        "service": "transformers_qa"
    }