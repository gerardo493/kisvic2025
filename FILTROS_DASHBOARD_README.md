# Sistema de Filtros para Dashboard de Facturación

## Descripción
Se ha implementado un sistema de filtros avanzado para el panel de control del sistema de facturación que permite visualizar las métricas financieras filtradas por año, mes o día específico.

## Funcionalidades Implementadas

### 1. Filtros de Visualización
- **Filtro por Año**: Muestra datos de un año específico
- **Filtro por Mes**: Muestra datos de un mes específico (1-12)
- **Filtro por Día**: Muestra datos de un día específico del mes (1-31)
- **Vista Completa**: Muestra todos los datos sin filtros

### 2. Métricas Filtradas
Las siguientes métricas se actualizan dinámicamente según el filtro aplicado:
- **Cuentas por Cobrar**: Total en USD y Bs
- **Pagos Recibidos**: Total en USD y Bs
- **Facturado**: Total facturado en USD
- **Promedio por Factura**: Promedio en USD

### 3. Características Técnicas
- **Actualización en Tiempo Real**: Los datos se actualizan sin recargar la página
- **Interfaz Intuitiva**: Selectores desplegables fáciles de usar
- **Información Contextual**: Muestra cuántas facturas coinciden con el filtro
- **Validación de Datos**: Solo permite filtros con datos válidos

## Archivos Modificados

### Backend
1. **`filtros_dashboard.py`** (NUEVO)
   - Función `obtener_estadisticas_filtradas()`: Calcula métricas con filtros
   - Función `obtener_opciones_filtro()`: Obtiene opciones disponibles para filtros

2. **`app.py`**
   - Importación del módulo de filtros
   - Ruta `/api/dashboard-filtros`: API para obtener métricas filtradas
   - Ruta `/api/opciones-filtro`: API para obtener opciones de filtro

### Frontend
3. **`templates/index.html`**
   - Interfaz de filtros agregada al dashboard
   - IDs únicos para elementos actualizables
   - JavaScript para manejo de filtros y actualización AJAX

## Uso del Sistema

### Para el Usuario Final
1. **Acceder al Dashboard**: Ir a la página principal del sistema
2. **Seleccionar Tipo de Filtro**: Elegir entre "Año", "Mes" o "Día"
3. **Seleccionar Valor**: Elegir el valor específico del filtro
4. **Aplicar Filtro**: Hacer clic en "Aplicar Filtro"
5. **Ver Resultados**: Las métricas se actualizarán automáticamente
6. **Limpiar Filtro**: Hacer clic en "Limpiar" para volver a la vista completa

### Para Desarrolladores

#### API Endpoints
```python
# Obtener métricas filtradas
GET /api/dashboard-filtros?tipo=año&valor=2024

# Obtener opciones de filtro
GET /api/opciones-filtro
```

#### Estructura de Respuesta
```json
{
    "success": true,
    "data": {
        "total_cobrar_usd": 15000.00,
        "total_cobrar_bs": 540000.00,
        "total_pagos_recibidos_usd": 5000.00,
        "total_pagos_recibidos_bs": 180000.00,
        "total_facturado_usd": 20000.00,
        "promedio_factura_usd": 200.00,
        "cantidad_facturas": 100,
        "filtro_aplicado": {
            "tipo": "año",
            "valor": "2024"
        }
    }
}
```

## Beneficios

### Para el Negocio
- **Análisis Temporal**: Visualizar tendencias por períodos específicos
- **Toma de Decisiones**: Datos más precisos para decisiones financieras
- **Reportes Granulares**: Información detallada por año, mes o día
- **Eficiencia**: Acceso rápido a datos específicos sin navegación compleja

### Para el Usuario
- **Interfaz Intuitiva**: Fácil de usar con selectores desplegables
- **Actualización Instantánea**: No requiere recargar la página
- **Información Clara**: Muestra cuántas facturas coinciden con el filtro
- **Flexibilidad**: Puede cambiar filtros fácilmente

## Consideraciones Técnicas

### Rendimiento
- Los filtros se aplican en el backend para optimizar el rendimiento
- Solo se cargan los datos necesarios según el filtro aplicado
- Las opciones de filtro se cargan una sola vez al inicializar

### Compatibilidad
- Compatible con la estructura existente de datos
- No afecta otras funcionalidades del sistema
- Mantiene la funcionalidad original del dashboard

### Escalabilidad
- Fácil agregar nuevos tipos de filtros
- Estructura modular para futuras mejoras
- API RESTful para integración con otros sistemas

## Próximas Mejoras Sugeridas

1. **Filtros Combinados**: Permitir filtros por año Y mes simultáneamente
2. **Rangos de Fechas**: Filtros por rango de fechas personalizado
3. **Filtros por Cliente**: Filtrar por cliente específico
4. **Exportación**: Exportar datos filtrados a PDF/Excel
5. **Gráficos**: Visualizaciones gráficas de los datos filtrados
6. **Filtros Guardados**: Guardar filtros frecuentemente usados

## Soporte y Mantenimiento

Para cualquier problema o mejora relacionada con los filtros del dashboard:
1. Verificar que los archivos estén correctamente implementados
2. Revisar la consola del navegador para errores JavaScript
3. Verificar que las APIs estén respondiendo correctamente
4. Consultar los logs del servidor para errores del backend
