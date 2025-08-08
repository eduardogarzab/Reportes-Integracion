#!/usr/bin/env python3
"""
Clasificador simple para probar un enunciado a la vez.
Funciones separadas para cada tipo de clasificación.
Usando OpenRouter con GPT.
"""

import requests
import json
import argparse
from dataclasses import dataclass
from typing import List

@dataclass
class ClassificationResult:
    """Resultado de la clasificación."""
    classification: str
    confidence: float
    reason: str
    service_type: str
    description: str
    examples: List[str]

class OpenRouterClassifier:
    """
    Clasificador de servicios en la nube usando OpenRouter con GPT.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': 'https://github.com/your-repo',
            'X-Title': 'Cloud Service Classifier'
        }
        
        # Definir el prompt del sistema para clasificación
        self.system_prompt = """
        Eres un experto en servicios en la nube. Tu tarea es clasificar el texto proporcionado en una de estas categorías:

        1. **IaaS (Infrastructure as a Service)**: Servicios que proporcionan infraestructura virtualizada como servidores, almacenamiento, redes, etc.
           Ejemplos: AWS EC2, Azure Virtual Machines, Google Compute Engine, DigitalOcean

        2. **SaaS (Software as a Service)**: Aplicaciones completas accesibles a través de la web.
           Ejemplos: Salesforce, Microsoft 365, Google Workspace, Slack, Zoom

        3. **PaaS (Platform as a Service)**: Plataformas de desarrollo que incluyen herramientas, middleware y servicios de base de datos.
           Ejemplos: Heroku, Google App Engine, Azure App Service, Firebase

        4. **FaaS (Function as a Service)**: Servicios serverless que ejecutan código en respuesta a eventos.
           Ejemplos: AWS Lambda, Azure Functions, Google Cloud Functions

        Responde ÚNICAMENTE en formato JSON con esta estructura exacta:
        {
            "classification": "IaaS|SaaS|PaaS|FaaS",
            "confidence": 0.95,
            "reason": "Explicación de por qué se clasificó así",
            "service_type": "Nombre completo del tipo de servicio",
            "description": "Descripción detallada del tipo de servicio",
            "examples": ["Ejemplo 1", "Ejemplo 2", "Ejemplo 3"]
        }

        Si el texto no está relacionado con servicios en la nube, responde con:
        {
            "classification": "Unknown",
            "confidence": 0.0,
            "reason": "El texto no está relacionado con servicios en la nube",
            "service_type": "Desconocido",
            "description": "No aplica",
            "examples": []
        }
        """
    
    def classify_text(self, text: str) -> ClassificationResult:
        """
        Clasifica el texto usando OpenRouter con GPT.
        
        Args:
            text (str): Texto a clasificar
            
        Returns:
            ClassificationResult: Resultado de la clasificación
        """
        if not text or not text.strip():
            return ClassificationResult(
                classification="Unknown",
                confidence=0.0,
                reason="Texto vacío o nulo",
                service_type="Desconocido",
                description="No aplica",
                examples=[]
            )
        
        # Crear el prompt completo
        user_prompt = f"Clasifica este texto: {text}"
        
        # Preparar la solicitud
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            # Realizar la solicitud a la API
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extraer el texto de la respuesta
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    
                    # Intentar parsear el JSON de la respuesta
                    try:
                        # Limpiar el texto de la respuesta para extraer solo el JSON
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start != -1 and json_end != 0:
                            json_text = response_text[json_start:json_end]
                            parsed_result = json.loads(json_text)
                            
                            return ClassificationResult(
                                classification=parsed_result.get('classification', 'Unknown'),
                                confidence=parsed_result.get('confidence', 0.0),
                                reason=parsed_result.get('reason', 'No se pudo determinar'),
                                service_type=parsed_result.get('service_type', 'Desconocido'),
                                description=parsed_result.get('description', 'No disponible'),
                                examples=parsed_result.get('examples', [])
                            )
                        else:
                            # Si no se encuentra JSON, usar clasificación de respaldo
                            return self._fallback_classification(text, response_text)
                            
                    except json.JSONDecodeError:
                        # Si falla el parsing JSON, usar clasificación de respaldo
                        return self._fallback_classification(text, response_text)
                else:
                    return ClassificationResult(
                        classification="Unknown",
                        confidence=0.0,
                        reason="No se recibió respuesta válida de la API",
                        service_type="Desconocido",
                        description="Error en la API",
                        examples=[]
                    )
            else:
                return ClassificationResult(
                    classification="Unknown",
                    confidence=0.0,
                    reason=f"Error en la API: {response.status_code}",
                    service_type="Desconocido",
                    description="Error de conexión",
                    examples=[]
                )
                
        except requests.exceptions.RequestException as e:
            return ClassificationResult(
                classification="Unknown",
                confidence=0.0,
                reason=f"Error de conexión: {str(e)}",
                service_type="Desconocido",
                description="Error de red",
                examples=[]
            )
    
    def _fallback_classification(self, original_text: str, gpt_response: str) -> ClassificationResult:
        """
        Clasificación de respaldo basada en palabras clave si falla el parsing JSON.
        """
        text_lower = original_text.lower()
        
        # Palabras clave para cada tipo de servicio
        keywords = {
            'IaaS': ['virtual machine', 'vm', 'server', 'compute', 'storage', 'network', 'infrastructure', 'ec2', 'azure vm'],
            'SaaS': ['application', 'software', 'crm', 'erp', 'office', 'productivity', 'collaboration', 'salesforce', 'microsoft 365'],
            'PaaS': ['platform', 'development', 'runtime', 'middleware', 'database', 'heroku', 'firebase', 'app engine'],
            'FaaS': ['serverless', 'function', 'lambda', 'event-driven', 'trigger', 'azure functions', 'cloud functions']
        }
        
        scores = {}
        for service_type, words in keywords.items():
            score = sum(1 for word in words if word in text_lower)
            scores[service_type] = score
        
        if max(scores.values()) > 0:
            best_match = max(scores.items(), key=lambda x: x[1])
            return ClassificationResult(
                classification=best_match[0],
                confidence=0.5,  # Confianza baja para clasificación de respaldo
                reason=f"Clasificación de respaldo basada en palabras clave: {gpt_response[:100]}...",
                service_type=best_match[0],
                description="Clasificación automática de respaldo",
                examples=[]
            )
        else:
            return ClassificationResult(
                classification="Unknown",
                confidence=0.0,
                reason="No se pudo clasificar el texto",
                service_type="Desconocido",
                description="Texto no relacionado con servicios en la nube",
                examples=[]
            )

# API Key de OpenRouter
API_KEY = "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"

def clasificar_iaas(texto):
    """Clasifica si el texto corresponde a IaaS."""
    classifier = OpenRouterClassifier(API_KEY)
    resultado = classifier.classify_text(texto)
    
    print(f"📝 Texto: {texto}")
    print(f"🏷️  Clasificación: {resultado.classification}")
    print(f"📊 Confianza: {resultado.confidence}")
    print(f"💡 Razón: {resultado.reason}")
    print(f"📋 Tipo: {resultado.service_type}")
    print(f"📖 Descripción: {resultado.description}")
    print("-" * 60)

def clasificar_saas(texto):
    """Clasifica si el texto corresponde a SaaS."""
    classifier = OpenRouterClassifier(API_KEY)
    resultado = classifier.classify_text(texto)
    
    print(f"📝 Texto: {texto}")
    print(f"🏷️  Clasificación: {resultado.classification}")
    print(f"📊 Confianza: {resultado.confidence}")
    print(f"💡 Razón: {resultado.reason}")
    print(f"📋 Tipo: {resultado.service_type}")
    print(f"📖 Descripción: {resultado.description}")
    print("-" * 60)

def clasificar_paas(texto):
    """Clasifica si el texto corresponde a PaaS."""
    classifier = OpenRouterClassifier(API_KEY)
    resultado = classifier.classify_text(texto)
    
    print(f"📝 Texto: {texto}")
    print(f"🏷️  Clasificación: {resultado.classification}")
    print(f"📊 Confianza: {resultado.confidence}")
    print(f"💡 Razón: {resultado.reason}")
    print(f"📋 Tipo: {resultado.service_type}")
    print(f"📖 Descripción: {resultado.description}")
    print("-" * 60)

def clasificar_faas(texto):
    """Clasifica si el texto corresponde a FaaS."""
    classifier = OpenRouterClassifier(API_KEY)
    resultado = classifier.classify_text(texto)
    
    print(f"📝 Texto: {texto}")
    print(f"🏷️  Clasificación: {resultado.classification}")
    print(f"📊 Confianza: {resultado.confidence}")
    print(f"💡 Razón: {resultado.reason}")
    print(f"📋 Tipo: {resultado.service_type}")
    print(f"📖 Descripción: {resultado.description}")
    print("-" * 60)

def clasificar_general(texto):
    """Clasifica el texto en cualquier categoría."""
    classifier = OpenRouterClassifier(API_KEY)
    resultado = classifier.classify_text(texto)
    
    print(f"📝 Texto: {texto}")
    print(f"🏷️  Clasificación: {resultado.classification}")
    print(f"📊 Confianza: {resultado.confidence}")
    print(f"💡 Razón: {resultado.reason}")
    print(f"📋 Tipo: {resultado.service_type}")
    print(f"📖 Descripción: {resultado.description}")
    print("-" * 60)

def main():
    """Función principal con argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Clasificador de servicios en la nube usando OpenRouter GPT')
    parser.add_argument('--texto', '-t', type=str, help='Texto a clasificar')
    parser.add_argument('--tipo', '-c', choices=['iaas', 'saas', 'paas', 'faas', 'general'], 
                       default='general', help='Tipo de clasificación específica')
    parser.add_argument('--ejemplos', '-e', action='store_true', help='Ejecutar ejemplos predefinidos')
    
    args = parser.parse_args()
    
    print("🚀 CLASIFICADOR DE SERVICIOS EN LA NUBE")
    print("Powered by OpenRouter GPT")
    print("=" * 60)
    
    if args.ejemplos:
        # Ejecutar ejemplos predefinidos
        print("\n1️⃣ Probando IaaS:")
        clasificar_iaas("Necesito servidores para mi aplicación web")
        
        print("\n2️⃣ Probando SaaS:")
        clasificar_saas("Busco una herramienta CRM para gestionar clientes")
        
        print("\n3️⃣ Probando PaaS:")
        clasificar_paas("Quiero una plataforma para desplegar mi aplicación")
        
        print("\n4️⃣ Probando FaaS:")
        clasificar_faas("Necesito ejecutar código cuando lleguen nuevos datos")
        
        print("\n5️⃣ Probando clasificación general:")
        clasificar_general("Quiero almacenar archivos en la nube")
    
    elif args.texto:
        # Clasificar el texto proporcionado
        if args.tipo == 'iaas':
            clasificar_iaas(args.texto)
        elif args.tipo == 'saas':
            clasificar_saas(args.texto)
        elif args.tipo == 'paas':
            clasificar_paas(args.texto)
        elif args.tipo == 'faas':
            clasificar_faas(args.texto)
        else:
            clasificar_general(args.texto)
    
    else:
        # Mostrar ayuda si no se proporcionan argumentos
        parser.print_help()
        print("\nEjemplos de uso:")
        print("  python simple_classifier.py --texto 'Necesito servidores' --tipo iaas")
        print("  python simple_classifier.py --texto 'Busco CRM' --tipo saas")
        print("  python simple_classifier.py --texto 'Quiero plataforma' --tipo paas")
        print("  python simple_classifier.py --texto 'Ejecutar código' --tipo faas")
        print("  python simple_classifier.py --texto 'Cualquier texto'")
        print("  python simple_classifier.py --ejemplos")

if __name__ == "__main__":
    main()

