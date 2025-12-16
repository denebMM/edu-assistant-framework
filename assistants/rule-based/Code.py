import time
import re
import random

# Variables globales
now = time.ctime()

def chatbot(user_input):
    """
    Función principal del chatbot basada en reglas - VERSIÓN MEJORADA
    """
    user_input = user_input.lower().strip()
    
    # === SALUDOS Y CONVERSACIÓN ===
    if any(word in user_input for word in ["hola", "holi", "holis", "buenos", "buenas", "saludos", "ola"]):
        return "¡Hola! Soy un asistente educativo. ¿En qué puedo ayudarte?"
    
    if "hi" in user_input or "hello" in user_input:
        return "Hi there! I'm a chatbot here to assist you."
    
    if "cómo te llamas" in user_input or "cuál es tu nombre" in user_input:
        return "Soy EduBot, tu asistente educativo. ¡Encantado de conocerte!"
    
    if "qué eres" in user_input or "what are you" in user_input:
        return "Soy un asistente basado en reglas, especializado en temas educativos básicos."
    
    if "cómo estás" in user_input or "how are you" in user_input:
        return "¡Muy bien! Listo para ayudarte con tus preguntas educativas."
    
    # === DETECCIÓN DE OPERACIONES MATEMÁTICAS ===
    # ¡NUEVO Y MEJORADO! Detecta cualquier operación matemática básica
    
    # Patrón para "cuanto es X + Y", "cuánto es 45 + 100", etc.
    if "cuánto es" in user_input or "cuanto es" in user_input:
        # Extraer números y operadores
        text = user_input.replace("cuánto es", "").replace("cuanto es", "").strip()
        
        # Buscar operaciones simples
        suma_match = re.search(r'(\d+)\s*\+\s*(\d+)', text)
        resta_match = re.search(r'(\d+)\s*-\s*(\d+)', text)
        multiplicacion_match = re.search(r'(\d+)\s*x\s*(\d+)', text)
        multiplicacion_match2 = re.search(r'(\d+)\s*\*\s*(\d+)', text)
        division_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
        
        if suma_match:
            a, b = int(suma_match.group(1)), int(suma_match.group(2))
            return f"{a} + {b} = {a + b}"
        elif resta_match:
            a, b = int(resta_match.group(1)), int(resta_match.group(2))
            return f"{a} - {b} = {a - b}"
        elif multiplicacion_match:
            a, b = int(multiplicacion_match.group(1)), int(multiplicacion_match.group(2))
            return f"{a} × {b} = {a * b}"
        elif multiplicacion_match2:
            a, b = int(multiplicacion_match2.group(1)), int(multiplicacion_match2.group(2))
            return f"{a} × {b} = {a * b}"
        elif division_match:
            a, b = int(division_match.group(1)), int(division_match.group(2))
            if b == 0:
                return "Error: No se puede dividir entre cero"
            return f"{a} ÷ {b} = {a / b:.2f}"
    
    # Patrón directo para "X + Y", "X - Y", etc. (sin "cuanto es")
    suma_match = re.search(r'^(\d+)\s*\+\s*(\d+)$', user_input)
    if suma_match:
        a, b = int(suma_match.group(1)), int(suma_match.group(2))
        return f"{a} + {b} = {a + b}"
    
    # Para "suma X y Y"
    if "suma" in user_input or "resta" in user_input or "multiplica" in user_input or "divide" in user_input:
        # Extraer números
        numeros = re.findall(r'\d+', user_input)
        if len(numeros) >= 2:
            a, b = int(numeros[0]), int(numeros[1])
            if "suma" in user_input:
                return f"{a} + {b} = {a + b}"
            elif "resta" in user_input:
                return f"{a} - {b} = {a - b}"
            elif "multiplica" in user_input:
                return f"{a} × {b} = {a * b}"
            elif "divide" in user_input:
                if b == 0:
                    return "Error: No se puede dividir entre cero"
                return f"{a} ÷ {b} = {a / b:.2f}"
    
    # === CHISTES ===
    if any(word in user_input for word in ["chiste", "joke", "hazme reir", "cuéntame un chiste", "dime un chiste"]):
        chistes = [
            "¿Qué le dice un semáforo a otro? ¡No me mires, me estoy cambiando!",
            "¿Por qué el libro de matemáticas está triste? ¡Porque tiene demasiados problemas!",
            "¿Qué hace una abeja en el gimnasio? ¡Zum-ba!",
            "¿Cómo se llama el campeón de buceo japonés? Tokofondo.",
            "¿Qué le dice una iguana a su hermana gemela? ¡Somos iguanitas!",
            "¿Por qué las focas miran siempre hacia arriba? ¡Porque ahí están los focos!",
            "¿Cómo se despiden los químicos? Ácido un placer.",
            "¿Qué hace una abeja reina en el baile? ¡Zumba!"
        ]
        return random.choice(chistes)
    
    # === REGLAS EDUCATIVAS ===
    
    # Matemáticas: Suma
    if "qué es la suma" in user_input or "explicame la suma" in user_input or "qué es sumar" in user_input:
        return "La suma es la operación matemática de **adición**, que consiste en combinar o añadir dos números o cantidades para obtener una cantidad final o total. Ejemplo: 2 + 3 = 5."
    
    # Matemáticas: Resta
    if "qué es la resta" in user_input or "qué es restar" in user_input:
        return "La resta es la operación matemática de **sustracción**, que consiste en quitar una cantidad de otra para encontrar la diferencia. Ejemplo: 5 - 3 = 2."
    
    # Matemáticas: Multiplicación
    if "qué es la multiplicación" in user_input or "qué es multiplicar" in user_input:
        return "La multiplicación es una **suma repetida**. Por ejemplo, 3 × 4 significa sumar 3 cuatro veces: 3 + 3 + 3 + 3 = 12."
    
    # Matemáticas: División
    if "qué es la división" in user_input or "qué es dividir" in user_input:
        return "La división es el **reparto en partes iguales**. Por ejemplo, 10 ÷ 2 = 5 significa que si repartes 10 entre 2, cada uno recibe 5."
    
    # Ciencias: Fotosíntesis
    if "qué es la fotosíntesis" in user_input or "explicame fotosíntesis" in user_input:
        return "La **fotosíntesis** es el proceso que usan las plantas, algas y algunas bacterias para transformar la luz solar, el agua y el dióxido de carbono en azúcares (alimento) y oxígeno."
    
    # Ciencias: Mitosis
    if "qué es la mitosis" in user_input or "explica mitosis" in user_input:
        return "La **mitosis** es el proceso de división celular en el que una célula madre se divide en dos células hijas idénticas, cada una con el mismo número de cromosomas que la célula madre."
    
    # Historia: Revolución Francesa
    if "revolución francesa" in user_input or "causas de la revolución" in user_input:
        return "La Revolución Francesa (1789) fue un periodo de gran agitación política y social. Sus causas principales incluyen la desigualdad social, la crisis económica y las ideas de la Ilustración."

    # Matemáticas básicas específicas (mantener compatibilidad)
    if "2+2" in user_input or "2 + 2" in user_input:
        return "2 + 2 = 4"
    
    if "5*5" in user_input or "5x5" in user_input or "5 × 5" in user_input:
        return "5 × 5 = 25"
    
    # Geografía
    if "capital de francia" in user_input or "cuál es la capital de francia" in user_input:
        return "La capital de Francia es París."
    
    if "capital de españa" in user_input or "cuál es la capital de españa" in user_input:
        return "La capital de España es Madrid."
    
    if "capital de italia" in user_input:
        return "La capital de Italia es Roma."
    
    if "capital de alemania" in user_input:
        return "La capital de Alemania es Berlín."
    
    # Historia: Personajes
    if "quién fue einstein" in user_input or "quien fue einstein" in user_input:
        return "Albert Einstein fue un físico alemán que desarrolló la teoría de la relatividad. Recibió el Premio Nobel de Física en 1921."
    
    if "quién fue newton" in user_input or "quien fue newton" in user_input:
        return "Isaac Newton fue un físico y matemático inglés que formuló las leyes del movimiento y la gravedad. Es uno de los científicos más influyentes de la historia."
    
    if "quién fue galileo" in user_input:
        return "Galileo Galilei fue un astrónomo, físico y matemático italiano considerado el padre de la ciencia moderna."
    
    # Preguntas frecuentes
    if "qué hora es" in user_input:
        return f"Son las {time.strftime('%H:%M')}"
    
    if "qué día es hoy" in user_input:
        return f"Hoy es {time.strftime('%d/%m/%Y')}"
    
    # === DESPEDIDAS ===
    if any(word in user_input for word in ["adiós", "chao", "hasta luego", "bye", "nos vemos", "hasta pronto"]):
        return "¡Adiós! Que tengas un excelente día de aprendizaje. ¡Vuelve cuando quieras!"
    
    if "gracias" in user_input:
        return "¡De nada! Siempre estoy aquí para ayudarte. ¿Algo más en lo que pueda asistirte?"
    
    # === SI NO SE RECONOCE ===
    no_entendi_respuestas = [
        "Lo siento, no entendí tu pregunta. ¿Podrías reformularla?",
        "No tengo una respuesta para eso en mis reglas básicas. ¡Prueba con una operación matemática o un saludo!",
        "Mi conocimiento es limitado. Pregúntame sobre matemáticas básicas, ciencia o geografía.",
        "Esa pregunta está fuera de mi alcance. ¿Quieres hacer una suma, resta o preguntar sobre algún tema educativo básico?"
    ]
    
    return random.choice(no_entendi_respuestas)

# ----------------------------------------------------------------------
# Código de ejecución interactiva - SOLO SE EJECUTA SI EL SCRIPT SE CORRE DIRECTAMENTE
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("🤖 Chatbot Educativo - Basado en Reglas")
    print("==========================================")
    print("Puedes preguntarme sobre:")
    print("- Matemáticas básicas (sumas, restas, etc.)")
    print("- Ciencia (fotosíntesis, mitosis)")
    print("- Geografía (capitales de países)")
    print("- Historia (científicos famosos)")
    print("- ¡Y también te cuento chistes!")
    print("\nEscribe 'bye' para salir.")
    print("=" * 50)
    
    while True:
        user_input = input("\n👤 Tú: ")
        if user_input.lower() == 'bye':
            print("🤖 Chatbot: ¡Hasta luego! Fue un placer ayudarte.")
            break

        response = chatbot(user_input)
        print(f"🤖 Chatbot: {response}")