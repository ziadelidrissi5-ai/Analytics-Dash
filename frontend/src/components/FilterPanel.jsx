import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Plus, Funnel, Trash } from "@phosphor-icons/react";

const OPERATORS = [
  { value: "eq", label: "Equals" },
  { value: "ne", label: "Not Equals" },
  { value: "gt", label: "Greater Than" },
  { value: "lt", label: "Less Than" },
  { value: "gte", label: "Greater or Equal" },
  { value: "lte", label: "Less or Equal" },
  { value: "contains", label: "Contains" },
];

export function FilterPanel({ columns, filters, onApplyFilters, onClose }) {
  const [localFilters, setLocalFilters] = useState(filters);
  const [newFilter, setNewFilter] = useState({
    column: "",
    operator: "eq",
    value: "",
  });

  const addFilter = () => {
    if (newFilter.column && newFilter.value) {
      setLocalFilters([...localFilters, { ...newFilter }]);
      setNewFilter({ column: "", operator: "eq", value: "" });
    }
  };

  const removeFilter = (index) => {
    setLocalFilters(localFilters.filter((_, i) => i !== index));
  };

  const applyFilters = () => {
    onApplyFilters(localFilters);
  };

  const clearFilters = () => {
    setLocalFilters([]);
    onApplyFilters([]);
  };

  const getColumnType = (columnName) => {
    const col = columns.find((c) => c.name === columnName);
    return col ? (col.is_numeric ? "numeric" : "text") : "text";
  };

  return (
    <div className="fixed top-16 left-0 w-80 h-[calc(100vh-64px)] border-r border-border bg-background z-40 sidebar-panel">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Funnel className="h-5 w-5 text-accent" />
            <h3 className="font-serif text-lg font-bold">Filters</h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            data-testid="close-filter-panel-btn"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {/* Active Filters */}
            {localFilters.length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Active Filters
                </Label>
                {localFilters.map((filter, idx) => (
                  <Card key={idx} className="border border-border">
                    <CardContent className="p-2 flex items-center justify-between">
                      <div className="text-sm">
                        <span className="font-medium">{filter.column}</span>
                        <span className="text-muted-foreground mx-1">
                          {OPERATORS.find((o) => o.value === filter.operator)?.label}
                        </span>
                        <Badge variant="secondary">{filter.value}</Badge>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFilter(idx)}
                        className="h-6 w-6"
                        data-testid={`remove-filter-${idx}-btn`}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Add New Filter */}
            <div className="space-y-3">
              <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                Add Filter
              </Label>

              {/* Column Select */}
              <div className="space-y-1">
                <Label className="text-xs">Column</Label>
                <Select
                  value={newFilter.column}
                  onValueChange={(value) =>
                    setNewFilter({ ...newFilter, column: value })
                  }
                >
                  <SelectTrigger data-testid="filter-column-select">
                    <SelectValue placeholder="Select column" />
                  </SelectTrigger>
                  <SelectContent>
                    {columns.map((col) => (
                      <SelectItem key={col.name} value={col.name}>
                        {col.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Operator Select */}
              <div className="space-y-1">
                <Label className="text-xs">Operator</Label>
                <Select
                  value={newFilter.operator}
                  onValueChange={(value) =>
                    setNewFilter({ ...newFilter, operator: value })
                  }
                >
                  <SelectTrigger data-testid="filter-operator-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPERATORS.map((op) => (
                      <SelectItem key={op.value} value={op.value}>
                        {op.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Value Input */}
              <div className="space-y-1">
                <Label className="text-xs">Value</Label>
                <Input
                  value={newFilter.value}
                  onChange={(e) =>
                    setNewFilter({ ...newFilter, value: e.target.value })
                  }
                  placeholder="Enter value"
                  type={
                    newFilter.column && getColumnType(newFilter.column) === "numeric"
                      ? "number"
                      : "text"
                  }
                  data-testid="filter-value-input"
                />
              </div>

              {/* Add Button */}
              <Button
                onClick={addFilter}
                disabled={!newFilter.column || !newFilter.value}
                className="w-full"
                data-testid="add-filter-btn"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Filter
              </Button>
            </div>
          </div>
        </ScrollArea>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border space-y-2">
          <Button
            onClick={applyFilters}
            className="w-full bg-accent hover:bg-accent/90"
            data-testid="apply-filters-btn"
          >
            Apply Filters
          </Button>
          {localFilters.length > 0 && (
            <Button
              variant="outline"
              onClick={clearFilters}
              className="w-full"
              data-testid="clear-filters-btn"
            >
              <Trash className="h-4 w-4 mr-2" />
              Clear All
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
