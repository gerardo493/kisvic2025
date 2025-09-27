# Componente StatsCard Modernizado

## Descripción

El componente `StatsCard` ha sido modernizado para el Sistema de Facturación con un diseño limpio, moderno y responsive. Incluye soporte para dark mode, animaciones suaves y accesibilidad completa.

## Características

### 🎨 Diseño Moderno
- **Contenedores**: Fondo blanco (light) / slate-800 (dark)
- **Bordes**: `rounded-2xl` para esquinas redondeadas
- **Sombras**: `shadow-md hover:shadow-lg` con transiciones suaves
- **Hover**: `hover:scale-105` con `transition-transform duration-200`
- **Padding**: `p-5 flex flex-col gap-2` para espaciado consistente

### 🎯 Iconos y Colores
- **Iconos**: Ubicados arriba a la izquierda en círculos translúcidos
- **Tamaño**: `w-10 h-10 rounded-full` con `flex items-center justify-center`
- **Colores por categoría**:
  - 🔴 **Cuentas por Cobrar**: `bg-red-100 text-red-500`
  - 🟢 **Pagos Recibidos**: `bg-green-100 text-green-500`
  - 🔵 **Facturado**: `bg-blue-100 text-blue-500`
  - 🟡 **Promedio por Factura**: `bg-yellow-100 text-yellow-500`

### 📱 Responsive Design
- **Grid responsive**:
  - `xl`: 4 columnas
  - `lg`: 3 columnas
  - `md`: 2 columnas
  - `sm`: 1 columna

### 🌙 Dark Mode
- Soporte completo con clases `dark:`
- Colores adaptativos para texto y fondos
- Iconos con colores optimizados para ambos modos

### ♿ Accesibilidad
- **Contraste AA**: Cumple estándares de accesibilidad
- **Focus ring**: `focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500`
- **ARIA**: `role="region"` y `aria-label` con nombre de métrica
- **Navegación por teclado**: Soporte completo para Enter y Espacio

### ⚡ Estados de Carga
- **Skeleton loading**: Animación de carga con fondo gris claro
- **Estados**: Loading, error, y datos normales
- **Transiciones**: Suaves entre estados

## Uso

### Ejemplo Básico

```tsx
import StatsCard from '@/components/dashboard/StatsCard';
import { DollarSign } from 'lucide-react';

<StatsCard 
  title="Cuentas por Cobrar"
  value="$18,979.26"
  subtitle="3,333,652.73 Bs"
  trend="+12%"
  trendValue={12}
  icon={DollarSign}
  color="red"
  helpText="Saldo pendiente de cobro"
/>
```

### Con Interacción

```tsx
<StatsCard 
  title="Ver Detalles"
  value="$12,345.67"
  subtitle="Click para ver más"
  icon={DollarSign}
  color="red"
  onClick={() => handleClick()}
/>
```

### Con Estado de Carga

```tsx
<StatsCard 
  title="Cargando..."
  value={0}
  icon={DollarSign}
  color="red"
  loading={true}
/>
```

## Props

| Prop | Tipo | Requerido | Descripción |
|------|------|-----------|-------------|
| `title` | `string` | ✅ | Título de la tarjeta |
| `value` | `number \| string` | ✅ | Valor principal a mostrar |
| `subtitle` | `string` | ❌ | Subtítulo (ej. monto en Bs) |
| `trend` | `'up' \| 'down' \| 'flat'` | ❌ | Dirección de la tendencia |
| `trendValue` | `number` | ❌ | Valor de la tendencia en porcentaje |
| `icon` | `React.ComponentType` | ✅ | Componente de icono de lucide-react |
| `color` | `'red' \| 'green' \| 'blue' \| 'yellow'` | ❌ | Color del tema (default: 'blue') |
| `currency` | `'USD' \| 'BS'` | ❌ | Moneda para formateo |
| `helpText` | `string` | ❌ | Texto de ayuda adicional |
| `tooltip` | `string` | ❌ | Tooltip informativo |
| `onClick` | `() => void` | ❌ | Función de click |
| `loading` | `boolean` | ❌ | Estado de carga (default: false) |

## Iconos Recomendados

### Cuentas por Cobrar
```tsx
import { DollarSign, HandCoins } from 'lucide-react';
```

### Pagos Recibidos
```tsx
import { HandCoins, CreditCard } from 'lucide-react';
```

### Facturado
```tsx
import { Receipt, FileText } from 'lucide-react';
```

### Promedio por Factura
```tsx
import { FileText, TrendingUp } from 'lucide-react';
```

## Estilos CSS

El componente utiliza Tailwind CSS con las siguientes clases principales:

```css
/* Contenedor principal */
.stats-card {
  @apply group relative overflow-hidden transition-all duration-200 
         hover:shadow-lg motion-safe:hover:scale-105 rounded-2xl 
         bg-white dark:bg-slate-800 shadow-md;
}

/* Icono */
.stats-icon {
  @apply w-10 h-10 rounded-full flex items-center justify-center 
         transition-all duration-200;
}

/* Valor principal */
.stats-value {
  @apply text-2xl font-bold text-gray-900 dark:text-gray-100;
}

/* Subtítulo */
.stats-subtitle {
  @apply text-sm text-gray-500 dark:text-gray-400;
}
```

## Grid Responsive

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
  {/* Tarjetas aquí */}
</div>
```

## Ejemplo Completo

```tsx
import React from 'react';
import StatsCard from '@/components/dashboard/StatsCard';
import { 
  DollarSign, 
  HandCoins, 
  Receipt, 
  FileText 
} from 'lucide-react';

const Dashboard = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <StatsCard 
        title="Cuentas por Cobrar"
        value="$18,979.26"
        subtitle="3,333,652.73 Bs"
        trend="up"
        trendValue={12}
        icon={DollarSign}
        color="red"
        helpText="Saldo pendiente de cobro"
      />
      
      <StatsCard 
        title="Pagos Recibidos"
        value="$45,230.50"
        subtitle="7,945,678.90 Bs"
        trend="up"
        trendValue={8}
        icon={HandCoins}
        color="green"
        helpText="Este mes"
      />
      
      <StatsCard 
        title="Facturado"
        value="$67,890.75"
        subtitle="Total USD"
        trend="up"
        trendValue={15}
        icon={Receipt}
        color="blue"
        helpText="Total facturado"
      />
      
      <StatsCard 
        title="Promedio por Factura"
        value="$1,234.56"
        subtitle="Promedio USD"
        trend="up"
        trendValue={3}
        icon={FileText}
        color="yellow"
        helpText="Ticket promedio"
      />
    </div>
  );
};
```

## Notas de Implementación

1. **Dependencias**: Asegúrate de tener `lucide-react` instalado
2. **Tailwind**: Configura Tailwind CSS con soporte para dark mode
3. **TypeScript**: El componente está completamente tipado
4. **Accesibilidad**: Incluye todas las etiquetas ARIA necesarias
5. **Performance**: Optimizado con React.memo si es necesario

## Migración desde el Sistema Anterior

Para migrar desde el sistema anterior:

1. Reemplaza las tarjetas existentes con `<StatsCard>`
2. Mapea los colores según la categoría:
   - Cuentas por Cobrar → `color="red"`
   - Pagos Recibidos → `color="green"`
   - Facturado → `color="blue"`
   - Promedio por Factura → `color="yellow"`
3. Actualiza el grid para usar las clases responsive
4. Mantén los mismos datos y funcionalidades

## Troubleshooting

### Problemas Comunes

1. **Iconos no aparecen**: Verifica que `lucide-react` esté instalado
2. **Colores no aplican**: Revisa la configuración de Tailwind CSS
3. **Dark mode no funciona**: Asegúrate de tener `dark:` configurado en Tailwind
4. **Responsive no funciona**: Verifica las clases de grid de Tailwind

### Debug

```tsx
// Verificar props
console.log('StatsCard props:', { title, value, color, loading });

// Verificar clases CSS
const element = document.querySelector('.stats-card');
console.log('Computed styles:', window.getComputedStyle(element));
```
