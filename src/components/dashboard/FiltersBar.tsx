import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { FiltersBarProps } from '@/types';
import { FILTER_OPTIONS, getDateRange, getActiveFiltersDescription } from '@/lib/filters';
import { cn } from '@/lib/utils';
import { 
  Search, 
  Calendar, 
  Filter, 
  X, 
  Download,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const FiltersBar: React.FC<FiltersBarProps> = ({
  filters,
  onFiltersChange,
  onReset,
  onExport,
  bcvRate,
  onUpdateBcvRate,
  loading = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [dateRange, setDateRange] = useState('mes');

  const handleDateRangeChange = (range: string) => {
    setDateRange(range);
    
    if (range === 'personalizado') {
      // No hacer nada, el usuario seleccionará fechas manualmente
      return;
    }
    
    const { desde, hasta } = getDateRange(range);
    onFiltersChange({
      ...filters,
      fecha_desde: desde,
      fecha_hasta: hasta,
    });
  };

  const handleCustomDateChange = (field: 'fecha_desde' | 'fecha_hasta', value: string) => {
    onFiltersChange({
      ...filters,
      [field]: value,
    });
    
    // Si ambas fechas están llenas, cambiar a personalizado
    if (field === 'fecha_desde' && filters.fecha_hasta) {
      setDateRange('personalizado');
    } else if (field === 'fecha_hasta' && filters.fecha_desde) {
      setDateRange('personalizado');
    }
  };

  const handleSearchChange = (value: string) => {
    onFiltersChange({
      ...filters,
      busqueda: value || undefined,
    });
  };

  const handleFilterChange = (field: keyof typeof filters, value: string) => {
    onFiltersChange({
      ...filters,
      [field]: value === 'todos' ? undefined : value,
    });
  };

  const activeFiltersCount = Object.values(filters).filter(Boolean).length;

  if (loading) {
    return (
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-64" />
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-24" />
            </div>
            <Skeleton className="h-4 w-48" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <CardContent className="p-4">
        {/* Fila principal de filtros */}
        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center">
          {/* Búsqueda */}
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por cliente, factura o producto..."
              value={filters.busqueda || ''}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
              aria-label="Búsqueda global"
            />
          </div>

          {/* Filtros rápidos */}
          <div className="flex flex-wrap gap-2">
            <Select
              value={filters.estado || 'todos'}
              onChange={(e) => handleFilterChange('estado', e.target.value)}
              className="w-32"
              aria-label="Filtrar por estado"
            >
              {FILTER_OPTIONS.estados.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>

            <Select
              value={filters.moneda || 'USD'}
              onChange={(e) => handleFilterChange('moneda', e.target.value)}
              className="w-24"
              aria-label="Filtrar por moneda"
            >
              {FILTER_OPTIONS.monedas.map(option => (
                <option key={option.value} value={option.value}>
                  {option.value}
                </option>
              ))}
            </Select>

            <Select
              value={filters.orden || 'fecha'}
              onChange={(e) => handleFilterChange('orden', e.target.value)}
              className="w-32"
              aria-label="Ordenar por"
            >
              {FILTER_OPTIONS.orden.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Botones de acción */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1"
              aria-label={isExpanded ? 'Ocultar filtros avanzados' : 'Mostrar filtros avanzados'}
            >
              <Filter className="h-4 w-4" />
              <span className="hidden sm:inline">Filtros</span>
              {activeFiltersCount > 0 && (
                <Badge variant="secondary" className="ml-1 h-5 w-5 p-0 flex items-center justify-center text-xs">
                  {activeFiltersCount}
                </Badge>
              )}
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onReset}
              className="flex items-center gap-1"
              aria-label="Resetear filtros"
            >
              <X className="h-4 w-4" />
              <span className="hidden sm:inline">Reset</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onExport}
              className="flex items-center gap-1"
              aria-label="Exportar datos"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Exportar</span>
            </Button>
          </div>
        </div>

        {/* Filtros avanzados expandibles */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Rango de fechas */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Rango de fechas
                </label>
                <Select
                  value={dateRange}
                  onChange={(e) => handleDateRangeChange(e.target.value)}
                  aria-label="Seleccionar rango de fechas"
                >
                  {FILTER_OPTIONS.rangos_fecha.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Fecha desde */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Desde
                </label>
                <Input
                  type="date"
                  value={filters.fecha_desde || ''}
                  onChange={(e) => handleCustomDateChange('fecha_desde', e.target.value)}
                  aria-label="Fecha desde"
                />
              </div>

              {/* Fecha hasta */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Hasta
                </label>
                <Input
                  type="date"
                  value={filters.fecha_hasta || ''}
                  onChange={(e) => handleCustomDateChange('fecha_hasta', e.target.value)}
                  aria-label="Fecha hasta"
                />
              </div>

              {/* Tasa BCV */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Tasa BCV
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    {bcvRate.tasa.toFixed(2)} Bs/USD
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onUpdateBcvRate}
                    className="h-6 w-6 p-0"
                    aria-label="Actualizar tasa BCV"
                  >
                    <RefreshCw className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Descripción de filtros activos */}
        {activeFiltersCount > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Filter className="h-4 w-4" />
              <span>Filtros activos:</span>
              <span className="font-medium">
                {getActiveFiltersDescription(filters)}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default FiltersBar;

