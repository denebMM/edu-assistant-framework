# wrapper.py: Adaptador para el AV basado en reglas. Expone API JSON estandarizada.
# Integra el código original del GitHub sin modificarlo.

from fastapi import FastAPI, Request  # Framework para API REST
app = FastAPI()  # Inicializa la app

# Importa la función principal del AV original
from Code import chatbot  # Asume que Code.py está en la misma carpeta y es importable



@app.get("/")
async def root():
    return {"message": "Rule-based AV funcionando", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rule_based_av"}


# Endpoint: Recibe JSON estandarizado del Supervisor y devuelve JSON estandarizado
@app.post("/query")
async def handle_query(request: Request):
    """
    Maneja una query educativa:
    - Recibe JSON: {"query": "string", "context": {"topic": "string"}} (estandarizado)
    - Llama al AV original (regla-based).
    - Devuelve JSON: {"task": "string", "output_data": {"response": "string", "status": "string", "metadata": "object"}}
    - Para hacerlo educativo: Agrega reglas en chatbot.py, e.g., if "suma" in user_input: return "Explicación de suma...".
      Por ahora, usa las reglas originales.
    """
    data = await request.json()  # Parsea input JSON
    query = data.get("query")  # Query principal
    context = data.get("context", {})  # Contexto opcional (e.g., tema educativo)
    
    if not query:
        return {"error": "No se proporcionó una query válida."}
    
    # Llama al AV original (regla-based)
    response_text = chatbot(query)  # Llama a la función chatbot del archivo original
    
    # Estandariza la salida JSON (universal para todos los AVs)
    return {
        "task": "explain_basic",  # Tipo de tarea (expande: "quiz", "adapt", etc.)
        "output_data": {
            "response": response_text,  # Respuesta del AV
            "status": "success",  # Estado
            "metadata": {"topic": context.get("topic", "general")}  # Metadata educativa
        }
    }