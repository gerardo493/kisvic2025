import React from 'react';
import StatsCard from '@/components/dashboard/StatsCard';
import { 
  DollarSign, 
  HandCoins, 
  Receipt, 
  FileText,
  Users,
  Package,
  Calendar,
  TrendingUp
} from 'lucide-react';

/**
 * Ejemplo de uso del componente StatsCard modernizado
 * Demuestra todas las variantes de colores y funcionalidades
 */
const StatsCardExample: React.FC = () => {
  return (
    <div className="p-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          Ejemplo de Tarjetas StatsCard Modernas
        </h1>
        
        {/* Grid principal con las 4 tarjetas principales */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12">
          {/* Cuentas por Cobrar - Rojo */}
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

          {/* Pagos Recibidos - Verde */}
          <StatsCard 
            title="Pagos Recibidos"
            value="$45,230.50"
            subtitle="7,945,678.90 Bs"
            trend="+8%"
            trendValue={8}
            icon={HandCoins}
            color="green"
            helpText="Este mes"
          />

          {/* Facturado - Azul */}
          <StatsCard 
            title="Facturado"
            value="$67,890.75"
            subtitle="Total USD"
            trend="+15%"
            trendValue={15}
            icon={Receipt}
            color="blue"
            helpText="Total facturado"
          />

          {/* Promedio por Factura - Amarillo */}
          <StatsCard 
            title="Promedio por Factura"
            value="$1,234.56"
            subtitle="Promedio USD"
            trend="+3%"
            trendValue={3}
            icon={FileText}
            color="yellow"
            helpText="Ticket promedio"
          />
        </div>

        {/* Grid secundario con tarjetas adicionales */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-6 mb-12">
          {/* Total Clientes */}
          <StatsCard 
            title="Total Clientes"
            value="1,234"
            trend="+5%"
            trendValue={5}
            icon={Users}
            color="blue"
            helpText="Clientes registrados"
          />

          {/* Productos en Inventario */}
          <StatsCard 
            title="Productos en Inventario"
            value="567"
            trend="flat"
            icon={Package}
            color="green"
            helpText="Productos activos"
          />

          {/* Facturas del Mes */}
          <StatsCard 
            title="Facturas del Mes"
            value="89"
            trend="+22%"
            trendValue={22}
            icon={Calendar}
            color="blue"
            helpText="Facturas emitidas"
          />

          {/* Tasa BCV */}
          <StatsCard 
            title="Tasa BCV"
            value="36.25"
            subtitle="Bs/USD"
            trend="+0.5%"
            trendValue={0.5}
            icon={TrendingUp}
            color="yellow"
            helpText="Tasa actual"
          />
        </div>

        {/* Ejemplos con estados de carga */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            Estados de Carga (Skeleton)
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatsCard 
              title="Cargando..."
              value={0}
              icon={DollarSign}
              color="red"
              loading={true}
            />
            <StatsCard 
              title="Cargando..."
              value={0}
              icon={HandCoins}
              color="green"
              loading={true}
            />
            <StatsCard 
              title="Cargando..."
              value={0}
              icon={Receipt}
              color="blue"
              loading={true}
            />
            <StatsCard 
              title="Cargando..."
              value={0}
              icon={FileText}
              color="yellow"
              loading={true}
            />
          </div>
        </div>

        {/* Ejemplos con interacciones */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            Tarjetas Interactivas (Click)
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatsCard 
              title="Ver Detalles"
              value="$12,345.67"
              subtitle="Click para ver más"
              icon={DollarSign}
              color="red"
              onClick={() => alert('¡Hiciste clic en Cuentas por Cobrar!')}
            />
            <StatsCard 
              title="Ver Reportes"
              value="$8,901.23"
              subtitle="Click para reportes"
              icon={HandCoins}
              color="green"
              onClick={() => alert('¡Hiciste clic en Pagos Recibidos!')}
            />
            <StatsCard 
              title="Ver Facturas"
              value="$15,678.90"
              subtitle="Click para facturas"
              icon={Receipt}
              color="blue"
              onClick={() => alert('¡Hiciste clic en Facturado!')}
            />
            <StatsCard 
              title="Ver Estadísticas"
              value="$2,345.67"
              subtitle="Click para estadísticas"
              icon={FileText}
              color="yellow"
              onClick={() => alert('¡Hiciste clic en Promedio por Factura!')}
            />
          </div>
        </div>

        {/* Código de ejemplo */}
        <div className="bg-gray-800 rounded-lg p-6 text-white">
          <h3 className="text-lg font-semibold mb-4">Código de Ejemplo:</h3>
          <pre className="text-sm overflow-x-auto">
{`// Ejemplo de uso básico
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

// Con interacción
<StatsCard 
  title="Ver Detalles"
  value="$12,345.67"
  subtitle="Click para ver más"
  icon={DollarSign}
  color="red"
  onClick={() => handleClick()}
/>

// Con estado de carga
<StatsCard 
  title="Cargando..."
  value={0}
  icon={DollarSign}
  color="red"
  loading={true}
/>`}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default StatsCardExample;
