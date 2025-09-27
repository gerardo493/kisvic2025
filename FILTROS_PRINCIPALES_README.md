# Sistema de Filtros Principales con Menús Anidados

## Descripción
Se ha implementado un sistema de filtros principales ubicado en la esquina superior derecha de las tarjetas de métricas, con menús desplegables anidados para opciones avanzadas de filtrado.

## Funcionalidades Implementadas

### 1. Filtros Principales
- **Ubicación**: Esquina superior derecha de cada tarjeta
- **Diseño**: Botón compacto con icono de filtro
- **Estilo**: Fondo semitransparente con efecto blur
- **Responsive**: Se adapta al tamaño de la tarjeta

### 2. Opciones de Filtro Básicas
- **Todos**: Muestra todos los datos sin filtro
- **Hoy**: Muestra datos del día actual
- **Separador visual**: Línea divisoria entre opciones básicas y avanzadas

### 3. Menús Anidados Avanzados

#### Esta Semana
- **Trigger**: Opción "Esta Semana" en el menú principal
- **Opciones**: Semana 1, Semana 2, Semana 3... hasta Semana 52
- **Funcionalidad**: Filtra datos por número de semana del año
- **Animación**: Despliegue lateral suave

#### Este Mes
- **Trigger**: Opción "Este Mes" en el menú principal
- **Opciones**: Enero, Febrero, Marzo... hasta Diciembre
- **Funcionalidad**: Filtra datos por mes específico
- **Animación**: Despliegue lateral suave

## Características Técnicas

### Backend
1. **`filtros_dashboard.py`** - Función `obtener_metricas_tarjeta()` actualizada:
   - Soporte para filtros por semana (`semana`)
   - Soporte para filtros por mes específico (`mes_especifico`)
   - Cálculo de número de semana usando `isocalendar()`

2. **`app.py`** - Ruta `/api/tarjeta-filtro`:
   - Parámetros: `tarjeta`, `tipo`, `valor`
   - Soporte para nuevos tipos de filtro
   - Respuesta JSON con datos filtrados

### Frontend
3. **`templates/index.html`** - Interfaz actualizada:
   - Filtros principales en esquina superior derecha
   - Menús desplegables con Bootstrap
   - Menús anidados con CSS personalizado
   - IDs únicos para cada tarjeta

4. **JavaScript Avanzado**:
   - Manejo de eventos para menús anidados
   - Actualización dinámica del texto del botón
   - Animaciones CSS con JavaScript
   - Cierre automático de menús

## Estructura de la Interfaz

### Diseño del Filtro Principal
```html
<!-- Filtro principal en esquina superior derecha -->
<div class="filtro-principal position-absolute" style="top: 10px; right: 10px;">
    <div class="dropdown">
        <button class="btn btn-sm btn-outline-light dropdown-toggle filtro-btn" data-tarjeta="cobranza">
            <i class="fas fa-filter me-1"></i>
            <span class="filtro-texto">Todos</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end filtro-menu">
            <!-- Opciones básicas y menús anidados -->
        </ul>
    </div>
</div>
```

### Estructura de Menús Anidados
```html
<li class="dropdown-submenu">
    <a class="dropdown-item dropdown-toggle" href="#" data-bs-toggle="dropdown">Esta Semana</a>
    <ul class="dropdown-menu submenu">
        <li><a class="dropdown-item submenu-item" href="#" data-tipo="semana" data-valor="1">Semana 1</a></li>
        <!-- Más opciones de semana -->
    </ul>
</li>
```

## Estilos CSS Implementados

### Filtro Principal
```css
.filtro-btn {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: #333;
    font-size: 0.75rem;
    padding: 4px 8px;
    border-radius: 6px;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}
```

### Menús Anidados
```css
.dropdown-submenu {
    position: relative;
}

.submenu {
    position: absolute;
    top: 0;
    left: 100%;
    min-width: 150px;
    background: white;
    border-radius: 6px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    display: none;
    z-index: 1000;
}
```

### Animaciones
```css
.dropdown-menu {
    animation: slideDown 0.3s ease-out;
}

.submenu {
    animation: slideRight 0.2s ease-out;
}
```

## Flujo de Funcionamiento

### 1. Interacción del Usuario
- Usuario hace clic en el botón de filtro
- Se despliega el menú principal
- Usuario navega a opciones anidadas (Esta Semana/Este Mes)
- Se despliega el submenú correspondiente

### 2. Selección de Filtro
- Usuario selecciona una opción específica
- Se actualiza el texto del botón
- Se cierra el menú desplegable
- Se activa la función de filtrado

### 3. Procesamiento
- Se determina el tipo de filtro (hoy/semana/mes_especifico)
- Se obtiene el valor específico (número de semana/mes)
- Se hace petición AJAX a la API
- Se aplican animaciones de carga

### 4. Actualización Visual
- Se ejecuta animación de fade out
- Se actualizan los valores numéricos
- Se ejecuta animación de fade in
- Se remueve el efecto de carga

## API Endpoints

### Obtener Métricas Filtradas
```http
GET /api/tarjeta-filtro?tarjeta=cobranza&tipo=semana&valor=15
```

**Parámetros:**
- `tarjeta`: Identificador de la tarjeta (cobranza, pagos, facturado)
- `tipo`: Tipo de filtro (hoy, semana, mes_especifico)
- `valor`: Valor específico del filtro (número de semana o mes)

**Respuesta:**
```json
{
    "success": true,
    "data": {
        "total_cobrar_usd": 12000.00,
        "total_cobrar_bs": 432000.00,
        "cantidad_facturas": 18
    }
}
```

## Tipos de Filtro Soportados

### 1. Filtro "Hoy"
- **Tipo**: `hoy`
- **Valor**: No requerido
- **Funcionalidad**: Muestra datos del día actual
- **Cálculo**: Compara fecha de factura con fecha actual

### 2. Filtro "Semana"
- **Tipo**: `semana`
- **Valor**: Número de semana (1-52)
- **Funcionalidad**: Muestra datos de la semana específica
- **Cálculo**: Usa `isocalendar()[1]` para obtener número de semana

### 3. Filtro "Mes Específico"
- **Tipo**: `mes_especifico`
- **Valor**: Número de mes (1-12)
- **Funcionalidad**: Muestra datos del mes específico
- **Cálculo**: Compara mes de factura con mes seleccionado

## Beneficios de la Implementación

### Para el Usuario
- **Acceso Rápido**: Filtros ubicados directamente en cada tarjeta
- **Navegación Intuitiva**: Menús anidados organizados lógicamente
- **Feedback Visual**: Animaciones que indican el estado de la operación
- **Experiencia Fluida**: Transiciones suaves y atractivas

### Para el Negocio
- **Análisis Granular**: Filtros por semana y mes específico
- **Toma de Decisiones**: Información más precisa y contextual
- **Eficiencia Operativa**: Acceso rápido a datos relevantes
- **Flexibilidad**: Cada usuario puede personalizar su vista

### Para el Desarrollo
- **Arquitectura Escalable**: Fácil agregar nuevos tipos de filtro
- **Código Reutilizable**: Lógica común para todas las tarjetas
- **Mantenimiento Simplificado**: Estructura clara y organizada
- **Rendimiento Optimizado**: Solo se actualiza la tarjeta necesaria

## Características de las Animaciones

### 1. Despliegue de Menús
- **slideDown**: Menú principal se despliega desde arriba
- **slideRight**: Submenús se despliegan desde la izquierda
- **Duración**: 0.2s - 0.3s
- **Easing**: ease-out para movimiento natural

### 2. Interacciones de Botón
- **Hover**: Elevación sutil y cambio de opacidad
- **Focus**: Anillo de enfoque para accesibilidad
- **Click**: Feedback visual inmediato

### 3. Transiciones de Datos
- **Fade Out/In**: Valores desaparecen y aparecen suavemente
- **Efecto de Carga**: Indicador visual durante la petición
- **Pulso**: Efecto hover en las tarjetas

## Consideraciones de Usabilidad

### Accesibilidad
- **Navegación por Teclado**: Soporte completo para navegación con Tab
- **ARIA Labels**: Etiquetas descriptivas para lectores de pantalla
- **Contraste**: Colores con suficiente contraste para legibilidad
- **Tamaño de Click**: Áreas de click suficientemente grandes

### Responsive Design
- **Adaptación**: Filtros se ajustan al tamaño de la tarjeta
- **Touch Friendly**: Optimizado para dispositivos táctiles
- **Z-index**: Menús anidados con z-index apropiado

### Performance
- **Lazy Loading**: Menús se cargan solo cuando se necesitan
- **Debounce**: Evita múltiples peticiones simultáneas
- **Caching**: Datos se cachean para mejor rendimiento

## Próximas Mejoras Sugeridas

### Funcionalidad
1. **Filtros Personalizados**: Rangos de fechas específicos
2. **Filtros Guardados**: Presets de filtros frecuentes
3. **Filtros Combinados**: Múltiples criterios simultáneos
4. **Exportación**: Exportar datos filtrados

### Interfaz
1. **Indicadores de Estado**: Mostrar filtro activo visualmente
2. **Contadores**: Número de registros filtrados
3. **Gráficos**: Visualizaciones de datos filtrados
4. **Temas**: Personalización de colores y estilos

### Técnicas
1. **WebSockets**: Actualizaciones en tiempo real
2. **Service Workers**: Caché offline
3. **Progressive Web App**: Funcionalidad offline
4. **Testing**: Pruebas automatizadas

## Soporte y Mantenimiento

### Debugging
- Verificar consola del navegador para errores JavaScript
- Revisar respuestas de la API en Network tab
- Validar estructura de datos en la respuesta

### Monitoreo
- Tiempo de respuesta de las APIs
- Frecuencia de uso de filtros
- Errores de red y servidor

### Actualizaciones
- Mantener compatibilidad con versiones anteriores
- Documentar cambios en la API
- Probar animaciones en diferentes navegadores
