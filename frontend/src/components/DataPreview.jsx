import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  CaretLeft,
  CaretRight,
  ChartBar,
  Hash,
  Calendar,
  TextAa,
  Info,
} from "@phosphor-icons/react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function DataPreview({
  data,
  datasetInfo,
  onPageChange,
  onGenerateDashboard,
}) {
  const { data: rows, total_rows, page, page_size, total_pages } = data;
  const columns = datasetInfo?.columns || [];

  const getTypeIcon = (col) => {
    if (col.is_numeric) return <Hash className="h-3 w-3" />;
    if (col.is_temporal) return <Calendar className="h-3 w-3" />;
    return <TextAa className="h-3 w-3" />;
  };

  const getTypeBadge = (col) => {
    if (col.is_numeric) return "numeric";
    if (col.is_temporal) return "temporal";
    if (col.is_categorical) return "categorical";
    return "text";
  };

  const formatCellValue = (value) => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">null</span>;
    }
    if (typeof value === "number") {
      return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
    }
    const strValue = String(value);
    if (strValue.length > 50) {
      return strValue.substring(0, 50) + "...";
    }
    return strValue;
  };

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      {/* Header Stats */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold">Apercu des donnees</h2>
          <p className="text-sm text-muted-foreground">
            {total_rows.toLocaleString()} lignes au total •{" "}
            {columns.length} colonnes
          </p>
        </div>

        <Button
          onClick={onGenerateDashboard}
          data-testid="generate-dashboard-from-preview-btn"
          className="bg-accent hover:bg-accent/90"
        >
          <ChartBar className="h-4 w-4 mr-2" />
          Generer le tableau de bord
        </Button>
      </div>

      {/* Column Summary */}
      <Card className="border border-border">
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Info className="h-4 w-4" />
            Analyse des colonnes
          </CardTitle>
        </CardHeader>
        <CardContent className="py-2 px-4">
          <div className="flex flex-wrap gap-2">
            {columns.slice(0, 12).map((col) => (
              <TooltipProvider key={col.name}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="secondary"
                      className="flex items-center gap-1 cursor-help"
                    >
                      {getTypeIcon(col)}
                      <span className="max-w-[120px] truncate">{col.name}</span>
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <div className="text-xs space-y-1">
                      <p>
                        <strong>Type :</strong> {getTypeBadge(col)}
                      </p>
                      <p>
                        <strong>Valeurs uniques :</strong> {col.unique_count.toLocaleString()}
                      </p>
                      <p>
                        <strong>Valeurs nulles :</strong> {col.null_count.toLocaleString()}
                      </p>
                      {col.stats?.mean !== undefined && (
                        <p>
                          <strong>Moyenne :</strong> {col.stats.mean?.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
            {columns.length > 12 && (
              <Badge variant="outline">+{columns.length - 12} autres</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card className="border border-border">
        <ScrollArea className="h-[calc(100vh-400px)] w-full">
          <Table className="data-table-dense">
            <TableHeader>
              <TableRow className="bg-secondary/50 hover:bg-secondary/50">
                {columns.map((col) => (
                  <TableHead
                    key={col.name}
                    className="whitespace-nowrap py-2 px-3 font-semibold"
                  >
                    <div className="flex items-center gap-1">
                      {getTypeIcon(col)}
                      <span className="truncate max-w-[150px]">{col.name}</span>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, idx) => (
                <TableRow
                  key={idx}
                  className="hover:bg-muted/50"
                  data-testid={`data-row-${idx}`}
                >
                  {columns.map((col) => (
                    <TableCell
                      key={col.name}
                      className="py-1 px-3 whitespace-nowrap"
                    >
                      {formatCellValue(row[col.name])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-border">
          <p className="text-sm text-muted-foreground">
            Affichage de {((page - 1) * page_size + 1).toLocaleString()} a{" "}
            {Math.min(page * page_size, total_rows).toLocaleString()} of{" "}
            {total_rows.toLocaleString()} lignes
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              data-testid="prev-page-btn"
            >
              <CaretLeft className="h-4 w-4" />
              Precedent
            </Button>
            <span className="text-sm px-2">
              Page {page} sur {total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= total_pages}
              data-testid="next-page-btn"
            >
              Suivant
              <CaretRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
