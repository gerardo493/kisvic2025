import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, 
  Package, 
  FileText, 
  DollarSign, 
  TrendingUp, 
  Calendar,
  Plus,
  FilePlus,
  ShoppingCart,
  ClipboardList,
  RefreshCw,
  Receipt,
  HandCoins
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import StatsCard from '@/components/dashboard/StatsCard';
import FiltersBar from '@/components/dashboard/FiltersBar';
import BcvRateCard from '@/components/dashboard/BcvRateCard';
import InvoicesTable from '@/components/tables/InvoicesTable';
import LowStockTable from '@/components/tables/LowStockTable';
import { 
  Stats, 
  Invoice, 
  Product, 
  BcvRate, 
  DashboardFilters,
  LoadingState 
} from '@/types';
import { 
  mockStats, 
  mockInvoices, 
  mockProducts, 
  mockBcvRate,
  fetchMockData 
} from '@/mocks/data';
import { 
  filterInvoices, 
  filterProducts, 
  getDefaultFilters,
  exportToCSV 
} from '@/lib/filters';
import { formatDate } from '@/lib/format';
import { cn } from '@/lib/utils';

const Dashboard: React.FC = () => {
  // Estado de datos
  const [stats, setStats] = useState<Stats | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [bcvRate, setBcvRate] = useState<BcvRate | null>(null);
  
  // Estado de filtros
  const [filters, setFilters] = useState<DashboardFilters>(getDefaultFilters());
  
  // Estado de carga
  const [loading, setLoading] = useState<LoadingState>({
    stats: true,
    invoices: true,
    products: true,
    bcvRate: true,
  });

  // Datos filtrados
  const filteredInvoices = filterInvoices(invoices, filters);
  const filteredProducts = filterProducts(products, filters);
  const lowStockProducts = filteredProducts.filter(p => p.stock <= p.punto_pedido);

  // Cargar datos iniciales
  const loadData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, stats: true, invoices: true, products: true, bcvRate: true }));
      
      const [statsData, invoicesData, productsData, bcvData] = await Promise.all([
        fetchMockData(mockStats, 800),
        fetchMockData(mockInvoices, 1000),
        fetchMockData(mockProducts, 600),
        fetchMockData(mockBcvRate, 400),
      ]);
      
      setStats(statsData);
      setInvoices(invoicesData);
      setProducts(productsData);
      setBcvRate(bcvData);
    } catch (error) {
      console.error('Error cargando datos:', error);
    } finally {
      setLoading(prev => ({ ...prev, stats: false, invoices: false, products: false, bcvRate: false }));
    }
  }, []);

  // Actualizar tasa BCV
  const handleUpdateBcvRate = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, bcvRate: true }));
      const newRate = await fetchMockData({
        ...mockBcvRate,
        tasa: mockBcvRate.tasa + (Math.random() - 0.5) * 2, // Simular cambio
        ultima_actualizacion: new Date().toISOString(),
      }, 1000);
      setBcvRate(newRate);
    } catch (error) {
      console.error('Error actualizando tasa BCV:', error);
    } finally {
      setLoading(prev => ({ ...prev, bcvRate: false }));
    }
  }, []);

  // Manejar cambios de filtros
  const handleFiltersChange = useCallback((newFilters: DashboardFilters) => {
    setFilters(newFilters);
  }, []);

  // Resetear filtros
  const handleResetFilters = useCallback(() => {
    setFilters(getDefaultFilters());
  }, []);

  // Exportar datos
  const handleExport = useCallback(() => {
    const columns = [
      { key: 'numero', header: 'Nº Factura' },
      { key: 'fecha', header: 'Fecha' },
      { key: 'cliente', header: 'Cliente' },
      { key: 'total_usd', header: 'Total USD' },
      { key: 'estado', header: 'Estado' },
    ];
    
    exportToCSV(filteredInvoices, columns, `facturas_${formatDate(new Date(), 'yyyy-MM-dd')}.csv`);
  }, [filteredInvoices]);

  // Acciones de facturas
  const handleViewInvoice = useCallback((invoice: Invoice) => {
    console.log('Ver factura:', invoice);
    // Implementar navegación a vista de factura
  }, []);

  const handleDownloadInvoice = useCallback((invoice: Invoice) => {
    console.log('Descargar factura:', invoice);
    // Implementar descarga de PDF
  }, []);

  const handleResendInvoice = useCallback((invoice: Invoice) => {
    console.log('Reenviar factura:', invoice);
    // Implementar reenvío por email/WhatsApp
  }, []);

  // Acciones de productos
  const handleViewProduct = useCallback((product: Product) => {
    console.log('Ver producto:', product);
    // Implementar navegación a vista de producto
  }, []);

  const handleEditProduct = useCallback((product: Product) => {
    console.log('Editar producto:', product);
    // Implementar edición de producto
  }, []);

  const handleRestockProduct = useCallback((product: Product) => {
    console.log('Reponer stock:', product);
    // Implementar reposición de stock
  }, []);

  // Acciones rápidas
  const quickActions = [
    {
      label: 'Nuevo Cliente',
      icon: Users,
      onClick: () => console.log('Nuevo cliente'),
      shortcut: 'C',
    },
    {
      label: 'Nuevo Producto',
      icon: Package,
      onClick: () => console.log('Nuevo producto'),
      shortcut: 'P',
    },
    {
      label: 'Nueva Factura',
      icon: FileText,
      onClick: () => console.log('Nueva factura'),
      shortcut: 'F',
    },
    {
      label: 'Nueva Cotización',
      icon: FilePlus,
      onClick: () => console.log('Nueva cotización'),
      shortcut: 'Q',
    },
    {
      label: 'Nueva Nota de Entrega',
      icon: ClipboardList,
      onClick: () => console.log('Nueva nota de entrega'),
      shortcut: 'N',
    },
  ];

  // Cargar datos al montar el componente
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Atajos de teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) return;
      
      const action = quickActions.find(a => a.shortcut === e.key.toUpperCase());
      if (action) {
        e.preventDefault();
        action.onClick();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [quickActions]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">
                Sistema de Facturación
              </h1>
              <p className="text-muted-foreground mt-1">
                Dashboard principal - {formatDate(new Date(), 'dd/MM/yyyy')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={loadData}
                disabled={Object.values(loading).some(Boolean)}
                className="flex items-center gap-2"
              >
                <RefreshCw className={cn("h-4 w-4", Object.values(loading).some(Boolean) && "animate-spin")} />
                Actualizar
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        {/* Barra de filtros */}
        <FiltersBar
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onReset={handleResetFilters}
          onExport={handleExport}
          bcvRate={bcvRate || mockBcvRate}
          onUpdateBcvRate={handleUpdateBcvRate}
          loading={loading.bcvRate}
        />

        {/* Grid de tarjetas de estadísticas modernas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
          {/* Cuentas por Cobrar */}
          <StatsCard
            title="Cuentas por Cobrar"
            value={`$${(stats?.total_cobrar_usd || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subtitle={`${(stats?.total_cobrar_bs || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Bs`}
            icon={DollarSign}
            color="red"
            trend="up"
            trendValue={5.2}
            loading={loading.stats}
          />

          {/* Pagos Recibidos */}
          <StatsCard
            title="Pagos Recibidos"
            value={`$${(stats?.total_pagos_recibidos_usd || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subtitle={`${(stats?.total_pagos_recibidos_bs || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Bs`}
            icon={HandCoins}
            color="green"
            trend="up"
            trendValue={12.8}
            loading={loading.stats}
          />

          {/* Facturado */}
          <StatsCard
            title="Facturado"
            value={`$${(stats?.total_facturado_usd || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subtitle="Total USD"
            icon={Receipt}
            color="blue"
            trend="up"
            trendValue={15.7}
            loading={loading.stats}
          />

          {/* Promedio por Factura */}
          <StatsCard
            title="Promedio por Factura"
            value={`$${(stats?.promedio_factura_usd || 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subtitle="Promedio USD"
            icon={FileText}
            color="yellow"
            trend="up"
            trendValue={3.1}
            loading={loading.stats}
          />
        </div>

        {/* Grid de tarjetas secundarias */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-6 mb-8">
          {/* Total Clientes */}
          <StatsCard
            title="Total Clientes"
            value={stats?.total_clientes || 0}
            icon={Users}
            color="blue"
            trend="up"
            trendValue={8.3}
            helpText="Clientes registrados"
            loading={loading.stats}
          />

          {/* Productos en Inventario */}
          <StatsCard
            title="Productos en Inventario"
            value={stats?.total_productos || 0}
            icon={Package}
            color="green"
            trend="flat"
            helpText="Productos activos"
            loading={loading.stats}
          />

          {/* Facturas del Mes */}
          <StatsCard
            title="Facturas del Mes"
            value={stats?.facturas_mes || 0}
            icon={Calendar}
            color="blue"
            trend="up"
            trendValue={22.4}
            helpText="Facturas emitidas"
            loading={loading.stats}
          />

          {/* Tasa BCV */}
          <BcvRateCard
            rate={bcvRate || mockBcvRate}
            onUpdate={handleUpdateBcvRate}
            loading={loading.bcvRate}
          />
        </div>

        {/* Acciones Rápidas */}
        <Card className="mb-8">
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold mb-4">Acciones Rápidas</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {quickActions.map((action, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="h-auto p-4 flex flex-col items-center gap-2 hover:bg-primary/5 hover:border-primary/20 transition-all duration-200"
                  onClick={action.onClick}
                >
                  <action.icon className="h-6 w-6" />
                  <span className="text-sm font-medium">{action.label}</span>
                  <span className="text-xs text-muted-foreground">
                    Ctrl+{action.shortcut}
                  </span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tablas */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* Últimas Facturas */}
          <InvoicesTable
            data={filteredInvoices.slice(0, 10)}
            loading={loading.invoices}
            onView={handleViewInvoice}
            onDownload={handleDownloadInvoice}
            onResend={handleResendInvoice}
          />

          {/* Productos con Bajo Stock */}
          <LowStockTable
            data={lowStockProducts}
            loading={loading.products}
            onView={handleViewProduct}
            onEdit={handleEditProduct}
            onRestock={handleRestockProduct}
          />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

