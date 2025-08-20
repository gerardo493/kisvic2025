import json

# Leer el archivo de facturas
with open('facturas_json/facturas.json', 'r', encoding='utf-8') as f:
    facturas = json.load(f)

print(f"Total facturas: {len(facturas)}")

# Verificar si hay claves vacías
empty_keys = [k for k in facturas.keys() if not k or str(k).strip() == '']
print(f"Claves vacías: {len(empty_keys)}")

if empty_keys:
    print("Claves problemáticas:")
    for k in empty_keys:
        print(f"  - {repr(k)}")
else:
    print("No hay claves problemáticas")

# Mostrar primeras 5 claves
print("\nPrimeras 5 claves:")
for i, k in enumerate(list(facturas.keys())[:5]):
    print(f"  {i+1}. {repr(k)}")
