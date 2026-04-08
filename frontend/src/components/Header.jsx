import { useState } from "react";
import {
  Sun,
  Moon,
  Database,
  ChartBar,
  Table,
  Funnel,
  Brain,
  FileText,
  Plus,
  Spinner,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export function Header({
  theme,
  toggleTheme,
  datasetInfo,
  activeView,
  setActiveView,
  onNewDataset,
  onGenerateDashboard,
  onShowFilters,
  onShowAI,
  onShowReport,
  isLoading,
  hasDataset,
}) {
  return (
    <header className="header-sticky border-b border-border px-6 py-3">
      <div className="flex items-center justify-between">
        {/* Logo & Title */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-accent flex items-center justify-center">
              <ChartBar className="h-5 w-5 text-accent-foreground" weight="bold" />
            </div>
            <div>
              <h1 className="font-serif text-xl font-bold tracking-tight">
                Z.Analytics
              </h1>
              <p className="text-xs text-muted-foreground">
                Intelligence des donnees
              </p>
            </div>
          </div>

          {/* Dataset Info Badge */}
          {datasetInfo && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-secondary rounded border border-border">
              <Database className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium truncate max-w-[200px]">
                {datasetInfo.filename}
              </span>
              <span className="text-xs text-muted-foreground">
                {datasetInfo.row_count.toLocaleString()} rows
              </span>
            </div>
          )}
        </div>

        {/* Navigation & Actions */}
        <div className="flex items-center gap-2">
          {hasDataset && (
            <>
              {/* View Toggle */}
              <div className="hidden sm:flex items-center gap-1 p-1 bg-secondary rounded">
                <Button
                  variant={activeView === "preview" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setActiveView("preview")}
                  data-testid="view-preview-btn"
                  className="h-7 px-3"
                >
                  <Table className="h-4 w-4 mr-1" />
                  Donnees
                </Button>
                <Button
                  variant={activeView === "dashboard" ? "default" : "ghost"}
                  size="sm"
                  onClick={onGenerateDashboard}
                  disabled={isLoading}
                  data-testid="view-dashboard-btn"
                  className="h-7 px-3"
                >
                  <ChartBar className="h-4 w-4 mr-1" />
                  Tableau de bord
                </Button>
              </div>

              {/* Action Buttons */}
              <Button
                variant="outline"
                size="sm"
                onClick={onShowFilters}
                data-testid="show-filters-btn"
                className="hidden md:flex"
              >
                <Funnel className="h-4 w-4 mr-1" />
                Filtres
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onShowAI}
                disabled={isLoading}
                data-testid="ai-insights-btn"
                className="hidden md:flex"
              >
                {isLoading ? (
                  <Spinner className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <Brain className="h-4 w-4 mr-1" />
                )}
                Analyse IA
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onShowReport}
                data-testid="generate-report-btn"
                className="hidden lg:flex"
              >
                <FileText className="h-4 w-4 mr-1" />
                Rapport
              </Button>

              {/* Mobile Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="md:hidden">
                    Actions
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setActiveView("preview")}>
                    <Table className="h-4 w-4 mr-2" />
                    Voir les donnees
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onGenerateDashboard}>
                    <ChartBar className="h-4 w-4 mr-2" />
                    Tableau de bord
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={onShowFilters}>
                    <Funnel className="h-4 w-4 mr-2" />
                    Filtres
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onShowAI}>
                    <Brain className="h-4 w-4 mr-2" />
                    Analyse IA
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onShowReport}>
                    <FileText className="h-4 w-4 mr-2" />
                    Generer un rapport
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <div className="w-px h-6 bg-border hidden sm:block" />
            </>
          )}

          {/* New Dataset */}
          <Button
            variant="default"
            size="sm"
            onClick={onNewDataset}
            data-testid="new-dataset-btn"
            className="bg-accent hover:bg-accent/90"
          >
            <Plus className="h-4 w-4 mr-1" />
            <span className="hidden sm:inline">Nouveau jeu de donnees</span>
          </Button>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            data-testid="theme-toggle-btn"
            className="h-8 w-8"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
