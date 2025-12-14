import time

# Variables globales: Se definen al importar y están disponibles para la función chatbot
now = time.ctime()

def chatbot(user_input):
    """
    Función principal del chatbot basada en reglas.
    """
    user_input = user_input.lower()

    # SALUDOS EN ESPAÑOL
    if any(word in user_input for word in ["hola", "holi", "holis", "buenos", "buenas", "saludos"]):
        return "¡Hola! Soy un asistente educativo. ¿En qué puedo ayudarte?"
    
    if "hi" in user_input or "hello" in user_input:
        return "Hi there! I'm a chatbot here to assist you."
    
    if "what is your name" in user_input or "cómo te llamas" in user_input:
        return "Soy un asistente educativo. Puedes llamarme EduBot."
    
    if "where are you from" in user_input:
        return "Soy del mundo digital, ¡siempre listo para ayudar!"
    
    if "how are you" in user_input or "cómo estás" in user_input:
        return "¡Muy bien! Listo para ayudarte con tus preguntas educativas."
    
    if "do you have any hobbies" in user_input or "interests" in user_input:
        return "¡Me encanta aprender y enseñar! Mi hobby es ayudar a estudiantes como tú."
    
    # --- REGLAS EDUCATIVAS ---
    
    # Matemáticas: Suma
    if "qué es la suma" in user_input or "explicame la suma" in user_input or "qué es sumar" in user_input:
        return "La suma es la operación matemática de **adición**, que consiste en combinar o añadir dos números o cantidades para obtener una cantidad final o total. Ejemplo: 2 + 3 = 5."
    
    # Ciencias: Fotosíntesis
    if "qué es la fotosíntesis" in user_input or "explicame fotosíntesis" in user_input:
        return "La **fotosíntesis** es el proceso que usan las plantas, algas y algunas bacterias para transformar la luz solar, el agua y el dióxido de carbono en azúcares (alimento) y oxígeno."
    
    # Historia: Revolución Francesa
    if "revolución francesa" in user_input or "causas de la revolución" in user_input:
        return "La Revolución Francesa (1789) fue un periodo de gran agitación política y social. Sus causas principales incluyen la desigualdad social, la crisis económica y las ideas de la Ilustración."

    # Matemáticas básicas
    if "cuánto es 2+2" in user_input or "cuanto es 2+2" in user_input:
        return "2 + 2 = 4"
    
    if "cuánto es 5*5" in user_input or "cuanto es 5x5" in user_input:
        return "5 × 5 = 25"
    
    # Ciencia: Mitosis
    if "qué es la mitosis" in user_input or "explica mitosis" in user_input:
        return "La **mitosis** es el proceso de división celular en el que una célula madre se divide en dos células hijas idénticas, cada una con el mismo número de cromosomas que la célula madre."
    
    # Geografía
    if "capital de francia" in user_input or "cuál es la capital de francia" in user_input:
        return "La capital de Francia es París."
    
    if "capital de españa" in user_input:
        return "La capital de España es Madrid."
    
    # Historia
    if "quién fue einstein" in user_input or "quien fue einstein" in user_input:
        return "Albert Einstein fue un físico alemán de origen judío, nacionalizado después suizo, austriaco y estadounidense. Es considerado el científico más importante, conocido y popular del siglo XX."
    
    if "quién fue newton" in user_input:
        return "Isaac Newton fue un físico, teólogo, inventor, alquimista y matemático inglés. Es autor de los Philosophiæ naturalis principia mathematica, más conocidos como los Principia, donde describe la ley de la gravitación universal y estableció las bases de la mecánica clásica."
    
    # DESPEDIDAS
    if "adiós" in user_input or "chao" in user_input or "hasta luego" in user_input or "bye" in user_input:
        return "¡Adiós! Que tengas un excelente día de aprendizaje."
    
    # Si no se reconoce
    return "Lo siento, no entendí tu pregunta. ¿Podrías reformularla? Estoy aquí para ayudarte con temas educativos."
# ----------------------------------------------------------------------
# Código de ejecución interactiva - SOLO SE EJECUTA SI EL SCRIPT SE CORRE DIRECTAMENTE
# ----------------------------------------------------------------------

if __name__ == "__main__":
    
    # Este print inicial estaba fuera del bloque y causaba problemas al importar.
    print("Chatbot: Hi! I'm a simple chatbot, I'm here to assist you!") 

    # Este loop 'while True' con 'input()' causaba el error Aborted!
    while True:
        user_input = input("Me: ")
        if user_input.lower() == 'bye':
            print("Chatbot: Goodbye! Have a great day!")
            break

        response = chatbot(user_input)
        print("Chatbot:", response)