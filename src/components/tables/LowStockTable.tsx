import React, { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Product } from '@/types';
import { formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';
import { 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  ChevronUp, 
  ChevronDown,
  Eye,
  Edit,
  Plus,
  AlertTriangle
} from 'lucide-react';

interface LowStockTableProps {
  data: Product[];
  loading?: boolean;
  onView?: (product: Product) => void;
  onEdit?: (product: Product) => void;
  onRestock?: (product: Product) => void;
}

const columnHelper = createColumnHelper<Product>();

const LowStockTable: React.FC<LowStockTableProps> = ({
  data,
  loading = false,
  onView,
  onEdit,
  onRestock,
}) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = React.useState('');

  const columns = useMemo<ColumnDef<Product>[]>(
    () => [
      columnHelper.accessor('sku', {
        header: 'SKU',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm font-medium">
            {getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('nombre', {
        header: 'Producto',
        cell: ({ getValue }) => (
          <span className="text-sm font-medium">
            {getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('stock', {
        header: 'Stock Actual',
        cell: ({ getValue, row }) => {
          const stock = getValue();
          const puntoPedido = row.original.punto_pedido;
          const isLowStock = stock <= puntoPedido;
          
          return (
            <div className="flex items-center gap-2">
              <span className={cn(
                "font-mono text-sm font-medium",
                isLowStock ? "text-red-600 dark:text-red-400" : "text-foreground"
              )}>
                {formatNumber(stock)}
              </span>
              {isLowStock && (
                <AlertTriangle className="h-4 w-4 text-red-500" />
              )}
            </div>
          );
        },
      }),
      columnHelper.accessor('punto_pedido', {
        header: 'Punto de Pedido',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-muted-foreground">
            {formatNumber(getValue())}
          </span>
        ),
      }),
      columnHelper.accessor('precio', {
        header: 'Precio',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm">
            ${formatNumber(getValue(), 2)}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'status',
        header: 'Estado',
        cell: ({ row }) => {
          const stock = row.original.stock;
          const puntoPedido = row.original.punto_pedido;
          
          if (stock === 0) {
            return (
              <Badge variant="destructive" className="text-xs">
                Sin Stock
              </Badge>
            );
          } else if (stock <= puntoPedido) {
            return (
              <Badge variant="warning" className="text-xs">
                Bajo Stock
              </Badge>
            );
          } else {
            return (
              <Badge variant="success" className="text-xs">
                Normal
              </Badge>
            );
          }
        },
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Acciones',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onView?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Ver producto ${row.original.nombre}`}
            >
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Editar producto ${row.original.nombre}`}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRestock?.(row.original)}
              className="h-8 w-8 p-0"
              aria-label={`Reponer stock de ${row.original.nombre}`}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        ),
      }),
    ],
    [onView, onEdit, onRestock]
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
  });

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Productos con Bajo Stock</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Productos con Bajo Stock</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <div className="text-muted-foreground mb-4">
              <AlertTriangle className="h-12 w-12 mx-auto mb-2" />
              <p>No hay productos con bajo stock</p>
              <p className="text-sm">¡Excelente gestión de inventario!</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Productos con Bajo Stock
          </CardTitle>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Buscar productos..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="w-64"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                {table.getHeaderGroups().map(headerGroup => (
                  <tr key={headerGroup.id} className="border-b">
                    {headerGroup.headers.map(header => (
                      <th
                        key={header.id}
                        className="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                      >
                        {header.isPlaceholder ? null : (
                          <div
                            className={cn(
                              "flex items-center gap-2",
                              header.column.getCanSort() && "cursor-pointer select-none hover:text-foreground"
                            )}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {header.column.getCanSort() && (
                              <div className="flex flex-col">
                                <ChevronUp 
                                  className={cn(
                                    "h-3 w-3",
                                    header.column.getIsSorted() === 'asc' ? "text-foreground" : "text-muted-foreground"
                                  )}
                                />
                                <ChevronDown 
                                  className={cn(
                                    "h-3 w-3 -mt-1",
                                    header.column.getIsSorted() === 'desc' ? "text-foreground" : "text-muted-foreground"
                                  )}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map(row => (
                  <tr
                    key={row.id}
                    className="border-b hover:bg-muted/50 transition-colors"
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Paginación */}
        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-muted-foreground">
            Mostrando {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} a{' '}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
              table.getFilteredRowModel().rows.length
            )}{' '}
            de {table.getFilteredRowModel().rows.length} productos
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              aria-label="Página anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              Página {table.getState().pagination.pageIndex + 1} de{' '}
              {table.getPageCount()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              aria-label="Página siguiente"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default LowStockTable;

