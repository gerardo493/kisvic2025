import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { BcvRateCardProps } from '@/types';
import { formatCurrency, formatDate } from '@/lib/format';
import { cn } from '@/lib/utils';
import { 
  DollarSign, 
  RefreshCw, 
  Clock, 
  TrendingUp,
  AlertCircle
} from 'lucide-react';

const BcvRateCard: React.FC<BcvRateCardProps> = ({
  rate,
  onUpdate,
  loading = false,
}) => {
  const isStale = () => {
    if (!rate.fecha) return false;
    
    const lastUpdate = new Date(rate.ultima_actualizacion);
    const now = new Date();
    const hoursDiff = (now.getTime() - lastUpdate.getTime()) / (1000 * 60 * 60);
    
    return hoursDiff > 24; // Considerar obsoleta si tiene más de 24 horas
  };

  const getStatusColor = () => {
    if (isStale()) {
      return 'text-yellow-600 dark:text-yellow-400';
    }
    return 'text-green-600 dark:text-green-400';
  };

  const getStatusText = () => {
    if (isStale()) {
      return 'Tasa desactualizada';
    }
    return 'Tasa actualizada';
  };

  if (loading) {
    return (
      <Card className="border-l-4 border-l-blue-500">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-8 w-24" />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card 
      className={cn(
        "border-l-4 border-l-blue-500 transition-all duration-200 hover:shadow-lg",
        isStale() && "border-l-yellow-500"
      )}
      role="region"
      aria-label={`Tasa BCV: ${formatCurrency(rate.tasa, 'BS')}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Tasa BCV
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={onUpdate}
            disabled={loading}
            className="h-8 px-3"
            aria-label="Actualizar tasa BCV"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            <span className="ml-1 hidden sm:inline">Actualizar</span>
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground">
              {formatCurrency(rate.tasa, 'BS')}
            </span>
            <span className="text-sm text-muted-foreground">
              por USD
            </span>
          </div>
          
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Actualizada: {formatDate(rate.ultima_actualizacion, 'dd/MM/yyyy HH:mm')}
            </span>
          </div>
          
          <div className="flex items-center gap-2 text-sm">
            <div className={cn("flex items-center gap-1", getStatusColor())}>
              {isStale() ? (
                <AlertCircle className="h-4 w-4" />
              ) : (
                <TrendingUp className="h-4 w-4" />
              )}
              <span>{getStatusText()}</span>
            </div>
          </div>
          
          {isStale() && (
            <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-md">
              <p className="text-xs text-yellow-800 dark:text-yellow-200">
                La tasa BCV no se ha actualizado en más de 24 horas. 
                Se recomienda actualizarla para obtener conversiones precisas.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default BcvRateCard;
