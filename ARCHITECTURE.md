# 🏗️ Arquitectura del Dashboard

## Estructura General

```
Dashboard
├── FiltersBar (Filtros y búsqueda)
├── StatsGrid (8 KPIs principales)
│   ├── StatsCard (Cuentas por Cobrar)
│   ├── StatsCard (Pagos Recibidos)
│   ├── StatsCard (Total Clientes)
│   ├── StatsCard (Productos en Inventario)
│   ├── StatsCard (Facturado)
│   ├── StatsCard (Promedio por Factura)
│   ├── StatsCard (Facturas del Mes)
│   └── BcvRateCard (Tasa BCV)
├── QuickActions (Acciones rápidas)
└── TablesGrid
    ├── InvoicesTable (Últimas Facturas)
    └── LowStockTable (Productos con Bajo Stock)
```

## Flujo de Datos

```
1. Dashboard carga datos mock/API
2. FiltersBar aplica filtros
3. Datos filtrados se pasan a componentes
4. StatsCard muestra KPIs calculados
5. Tables muestran datos filtrados
6. Usuario interactúa con filtros/acciones
7. Estado se actualiza reactivamente
```

## Componentes Principales

### StatsCard
- **Props**: title, value, trend, icon, currency, tooltip
- **Funcionalidad**: Muestra KPI con formateo, tendencia y tooltip
- **Accesibilidad**: ARIA roles, navegación por teclado

### FiltersBar
- **Props**: filters, onFiltersChange, onReset, onExport
- **Funcionalidad**: Filtros avanzados, búsqueda, exportación
- **Estado**: Filtros locales sincronizados con URL

### BcvRateCard
- **Props**: rate, onUpdate, loading
- **Funcionalidad**: Muestra tasa BCV, actualización manual
- **Validación**: Detecta tasas obsoletas (>24h)

### InvoicesTable
- **Props**: data, onView, onDownload, onResend
- **Funcionalidad**: Tabla con TanStack Table, paginación, ordenamiento
- **Acciones**: Ver, descargar, reenviar facturas

### LowStockTable
- **Props**: data, onView, onEdit, onRestock
- **Funcionalidad**: Productos con stock bajo, alertas visuales
- **Filtros**: Solo productos con stock <= punto_pedido

## Estado de la Aplicación

```typescript
interface AppState {
  // Datos
  stats: Stats | null;
  invoices: Invoice[];
  products: Product[];
  bcvRate: BcvRate | null;
  
  // Filtros
  filters: DashboardFilters;
  
  // Carga
  loading: LoadingState;
}
```

## Hooks Personalizados

### useFilters
- Maneja estado de filtros
- Sincronización con URL
- Validación de filtros

### useStats
- Carga estadísticas
- Cálculo de KPIs
- Actualización automática

### useTable
- Configuración de tablas
- Paginación y ordenamiento
- Filtros por columna

## Utilidades

### format.ts
- `formatCurrency()`: Formateo de monedas
- `formatDate()`: Formateo de fechas
- `formatNumber()`: Formateo de números
- `getStatusColor()`: Colores de estado

### filters.ts
- `filterInvoices()`: Filtrado de facturas
- `filterProducts()`: Filtrado de productos
- `exportToCSV()`: Exportación de datos
- `getDateRange()`: Rangos de fechas

## Responsive Design

### Breakpoints
- `sm`: 640px (1 columna)
- `md`: 768px (2 columnas)
- `lg`: 1024px (3 columnas)
- `xl`: 1280px (4 columnas)

### Grid System
```css
.grid-responsive {
  grid-template-columns: 
    repeat(auto-fit, minmax(280px, 1fr));
}
```

## Accesibilidad

### ARIA Roles
- `region`: Tarjetas de estadísticas
- `table`: Tablas de datos
- `button`: Botones de acción
- `search`: Campo de búsqueda

### Navegación por Teclado
- `Tab`: Navegación secuencial
- `Enter/Space`: Activación de elementos
- `Escape`: Cerrar modales/tooltips
- `Arrow Keys`: Navegación en tablas

### Contraste
- Todos los colores cumplen WCAG 2.1 AA
- Ratios mínimos: 4.5:1 (normal), 3:1 (large)

## Performance

### Optimizaciones
- **Lazy Loading**: Componentes cargados bajo demanda
- **Memoización**: React.memo en componentes pesados
- **Debouncing**: Búsqueda con delay de 300ms
- **Virtualización**: Tablas grandes con react-window

### Bundle Size
- **Tree Shaking**: Solo imports necesarios
- **Code Splitting**: Rutas separadas
- **Compression**: Gzip/Brotli en producción

## Testing

### Estrategia
- **Unit Tests**: Componentes individuales
- **Integration Tests**: Flujos completos
- **E2E Tests**: Casos de uso reales
- **Accessibility Tests**: axe-core

### Cobertura
- **Objetivo**: 80%+ cobertura
- **Componentes**: 100% cobertura
- **Utilidades**: 100% cobertura
- **Hooks**: 90%+ cobertura

## Deploy

### Build Process
1. TypeScript compilation
2. Tailwind CSS processing
3. Asset optimization
4. Bundle splitting
5. Source maps generation

### Environments
- **Development**: Hot reload, source maps
- **Staging**: Production build, testing
- **Production**: Optimized, minified

## Monitoreo

### Métricas
- **Performance**: Core Web Vitals
- **Accessibility**: Lighthouse scores
- **Errors**: Error boundaries, logging
- **Usage**: Analytics, heatmaps

### Alertas
- **Errors**: >1% error rate
- **Performance**: LCP >2.5s
- **Accessibility**: Score <90

---

**Arquitectura escalable y mantenible para el Sistema de Facturación** 🏗️

