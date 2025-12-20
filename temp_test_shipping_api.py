import requests
import json

# Probar el endpoint de métodos de envío
base_url = "http://localhost:5000"  # Ajusta si es diferente

# Test 1: San Martín de Porres (funciona en web)
print("=" * 60)
print("TEST 1: San Martín de Porres")
print("=" * 60)
response = requests.get(f"{base_url}/orders/api/metodos-envio/San%20Martín%20de%20Porres")
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
print()

# Test 2: Lurín (no funciona en manager pero sí en web)
print("=" * 60)
print("TEST 2: Lurín")
print("=" * 60)
response = requests.get(f"{base_url}/orders/api/metodos-envio/Lurín")
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
print()

# Test 3: Lurín sin tilde
print("=" * 60)
print("TEST 3: Lurin (sin tilde)")
print("=" * 60)
response = requests.get(f"{base_url}/orders/api/metodos-envio/Lurin")
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
