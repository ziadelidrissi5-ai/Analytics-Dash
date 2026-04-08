import { useState, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  TrendUp,
  TrendDown,
  Minus,
  Brain,
  Warning,
  Link,
  DownloadSimple,
  Plus,
} from "@phosphor-icons/react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { toast } from "sonner";

const CHART_COLORS = [
  "hsl(150, 60%, 40%)", // accent/emerald
  "hsl(210, 100%, 60%)", // blue
  "hsl(40, 100%, 50%)", // yellow/gold
  "hsl(0, 70%, 50%)", // red
  "hsl(215, 20%, 65%)", // gray
  "hsl(280, 60%, 50%)", // purple
];

export function Dashboard({
  data,
  datasetInfo,
  onShowAI,
  onMergeDataset,
  sheetName,
  isGlobalView,
  workbookRelations,
}) {
  const { kpis, charts, correlations, anomalies } = data;

  // Separate AI insights from technical anomalies
  const aiInsights = anomalies.filter(a => a.column === "AI Insight");
  const technicalAnomalies = anomalies.filter(a => a.column !== "AI Insight");

  const subtitle = isGlobalView
    ? `Vue croisée de toutes les feuilles — ${datasetInfo?.filename || ""}`
    : sheetName
    ? `Feuille "${sheetName}" — ${datasetInfo?.filename || ""}`
    : `Insights IA pour ${datasetInfo?.filename || ""}`;

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-2xl md:text-3xl font-bold">
              {isGlobalView ? "Vue globale" : "Tableau de bord analytique"}
            </h2>
            {isGlobalView && (
              <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/30">
                <Link className="h-3 w-3" />
                Multi-feuilles
              </span>
            )}
            {sheetName && !isGlobalView && (
              <span className="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                {sheetName}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="flex gap-2">
          {!isGlobalView && onMergeDataset && (
            <Button
              onClick={onMergeDataset}
              variant="outline"
              data-testid="merge-dataset-btn"
            >
              <Plus className="h-4 w-4 mr-2" />
              Fusionner les jeux de donnees
            </Button>
          )}
          {!isGlobalView && onShowAI && (
            <Button
              onClick={onShowAI}
              data-testid="dashboard-ai-btn"
              className="bg-accent hover:bg-accent/90"
            >
              <Brain className="h-4 w-4 mr-2" />
              Analyse approfondie
            </Button>
          )}
        </div>
      </div>

      {/* Cross-sheet relations summary (global view only) */}
      {isGlobalView && workbookRelations && workbookRelations.length > 0 && (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-4">
          <p className="text-xs font-semibold text-accent uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Link className="h-3.5 w-3.5" />
            Relations inter-feuilles détectées
          </p>
          <div className="flex flex-wrap gap-2">
            {workbookRelations.map((rel, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 text-xs bg-background border border-border rounded-full px-3 py-1"
              >
                <span className="font-medium">{rel.sheet1}</span>
                <span className="text-muted-foreground">↔</span>
                <span className="font-medium">{rel.sheet2}</span>
                {rel.join_keys?.length > 0 && (
                  <span className="text-accent">via &quot;{rel.join_keys[0]}&quot;</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* AI Insights Banner */}
      {aiInsights.length > 0 && (
        <Card className="border border-accent/50 bg-accent/5">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Brain className="h-4 w-4 text-accent" />
              Analyse IA
            </CardTitle>
          </CardHeader>
          <CardContent className="py-2 px-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {aiInsights.map((insight, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-accent font-bold">•</span>
                  <p className="text-foreground/90">{insight.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => (
          <KPICard key={idx} kpi={kpi} />
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {charts.map((chart, idx) => (
          <ChartCard key={idx} chart={chart} chartIndex={idx} />
        ))}
      </div>

      {/* Correlations & Anomalies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Correlations */}
        {correlations.length > 0 && (
          <Card className="border border-border">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Link className="h-4 w-4" />
                Correlations fortes
              </CardTitle>
            </CardHeader>
            <CardContent className="py-2 px-4">
              <div className="space-y-2">
                {correlations.slice(0, 5).map((corr, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-muted-foreground">
                      {corr.column1} ↔ {corr.column2}
                    </span>
                    <Badge
                      variant={corr.correlation > 0 ? "default" : "destructive"}
                      className="font-mono"
                    >
                      {corr.correlation > 0 ? "+" : ""}
                      {corr.correlation.toFixed(3)}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Technical Anomalies */}
        {technicalAnomalies.length > 0 && (
          <Card className="border border-border border-l-4 border-l-destructive">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Warning className="h-4 w-4 text-destructive" />
                Alertes qualite des donnees
              </CardTitle>
            </CardHeader>
            <CardContent className="py-2 px-4">
              <div className="space-y-2">
                {technicalAnomalies.map((anom, idx) => (
                  <div key={idx} className="text-sm">
                    <p className="text-muted-foreground">{anom.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function KPICard({ kpi }) {
  // Enhanced number formatting for better readability
  const formatValue = (value, format, name) => {
    if (value === null || value === undefined) return "N/A";

    const num = typeof value === "number" ? value : parseFloat(value);
    if (isNaN(num)) return value;

    // Detect if it's a currency/financial metric based on name
    const isCurrency = /revenue|income|ebitda|assets|cash|profit|sales|cost|price|amount/i.test(name || "");
    const isPercentage = /percentage|%|rate|ratio/i.test(name || "") || format === "percentage";
    
    if (isPercentage) {
      return `${num.toFixed(1)}%`;
    }

    // Format large numbers with appropriate suffixes
    const formatLargeNumber = (n, currencySymbol = "") => {
      const abs = Math.abs(n);
      if (abs >= 1e12) {
        return `${currencySymbol}${(n / 1e12).toFixed(2)}T`;
      } else if (abs >= 1e9) {
        return `${currencySymbol}${(n / 1e9).toFixed(2)}B`;
      } else if (abs >= 1e6) {
        return `${currencySymbol}${(n / 1e6).toFixed(2)}M`;
      } else if (abs >= 1e3) {
        return `${currencySymbol}${(n / 1e3).toFixed(2)}K`;
      } else {
        return `${currencySymbol}${n.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}`;
      }
    };

    if (isCurrency || format === "currency") {
      return formatLargeNumber(num, "€");
    }

    if (format === "integer") {
      return Math.round(num).toLocaleString("fr-FR");
    }

    // Default: format with French locale (space as thousands separator)
    if (Math.abs(num) >= 1e6) {
      return formatLargeNumber(num);
    }
    
    return num.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  };

  const getTrendIcon = () => {
    if (!kpi.change) return null;
    if (kpi.change > 0) return <TrendUp className="h-4 w-4 text-accent" />;
    if (kpi.change < 0) return <TrendDown className="h-4 w-4 text-destructive" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <Card
      className="kpi-card border border-border"
      data-testid={`kpi-card-${kpi.name.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
          {kpi.name}
        </p>
        <div className="flex items-end justify-between">
          <p className="text-xl md:text-2xl font-semibold tracking-tight">
            {formatValue(kpi.value, kpi.format, kpi.name)}
          </p>
          {kpi.change !== null && kpi.change !== undefined && (
            <div className="flex items-center gap-1 text-sm">
              {getTrendIcon()}
              <span
                className={
                  kpi.change > 0
                    ? "text-accent"
                    : kpi.change < 0
                      ? "text-destructive"
                      : "text-muted-foreground"
                }
              >
                {kpi.change > 0 ? "+" : ""}
                {kpi.change.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ChartCard({ chart, chartIndex }) {
  const chartRef = useRef(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Download chart as PNG using canvas
  const downloadChart = useCallback(async () => {
    if (!chartRef.current) return;
    
    setIsDownloading(true);
    try {
      // Find the SVG element inside the chart container
      const svg = chartRef.current.querySelector("svg");
      if (!svg) {
        toast.error("Chart not found");
        return;
      }

      // Get SVG dimensions
      const svgRect = svg.getBoundingClientRect();
      const width = svgRect.width || 600;
      const height = svgRect.height || 400;

      // Create a canvas
      const canvas = document.createElement("canvas");
      const scale = 2; // Higher resolution
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext("2d");
      
      // Fill background
      ctx.fillStyle = "#0d1117"; // Dark background
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);

      // Convert SVG to data URL
      const svgData = new XMLSerializer().serializeToString(svg);
      const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
      const svgUrl = URL.createObjectURL(svgBlob);

      // Create image from SVG
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(svgUrl);

        // Download canvas as PNG
        canvas.toBlob((blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${chart.title.replace(/[^a-z0-9]/gi, "_")}_chart.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast.success("Chart downloaded");
        }, "image/png");
      };
      img.onerror = () => {
        toast.error("Failed to generate image");
        URL.revokeObjectURL(svgUrl);
      };
      img.src = svgUrl;
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download chart");
    } finally {
      setIsDownloading(false);
    }
  }, [chart.title]);

  // Format axis values for better readability
  const formatAxisValue = (value) => {
    if (typeof value !== "number") return value;
    const abs = Math.abs(value);
    if (abs >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    if (abs >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
    return value.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
  };

  const formatTooltipValue = (value) => {
    if (typeof value !== "number") return value;
    return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  };

  const renderChart = () => {
    switch (chart.chart_type) {
      case "line":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chart.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey={chart.config?.xAxisType === "time" ? "date" : "x"}
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={(val) => {
                  if (chart.config?.xAxisType === "time" && val) {
                    return new Date(val).toLocaleDateString("fr-FR", {
                      month: "short",
                      day: "numeric",
                    });
                  }
                  return formatAxisValue(val);
                }}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={formatAxisValue}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "4px",
                }}
                formatter={(value) => [formatTooltipValue(value), "Valeur"]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case "bar":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chart.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey={chart.config?.isHistogram ? "bin" : "category"}
                stroke="hsl(var(--muted-foreground))"
                fontSize={9}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
                tickFormatter={(val) => {
                  // Shorten long labels
                  if (typeof val === "string" && val.length > 12) {
                    return val.substring(0, 10) + "...";
                  }
                  return val;
                }}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={formatAxisValue}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "4px",
                }}
                formatter={(value) => [formatTooltipValue(value), chart.config?.isHistogram ? "Frequence" : "Valeur"]}
              />
              <Bar dataKey="count" fill={CHART_COLORS[0]} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case "scatter":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="x"
                name={chart.x_column}
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={formatAxisValue}
              />
              <YAxis
                dataKey="y"
                name={chart.y_column}
                stroke="hsl(var(--muted-foreground))"
                fontSize={10}
                tickFormatter={formatAxisValue}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "4px",
                }}
                formatter={(value) => formatTooltipValue(value)}
              />
              <Scatter data={chart.data} fill={CHART_COLORS[1]} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case "pie":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={chart.data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, percent }) =>
                  `${name.length > 10 ? name.substring(0, 8) + "..." : name} (${(percent * 100).toFixed(0)}%)`
                }
                labelLine={false}
              >
                {chart.data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "4px",
                }}
                formatter={(value) => formatTooltipValue(value)}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <div className="h-[280px] flex items-center justify-center text-muted-foreground">
            Chart type "{chart.chart_type}" not supported
          </div>
        );
    }
  };

  return (
      <Card
      className="border border-border"
      data-testid={`chart-${chart.chart_type}-${chartIndex}`}
    >
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
        <div className="pr-4">
          <CardTitle className="text-sm font-medium">{chart.title}</CardTitle>
          {chart.config?.description && (
            <p className="text-xs text-muted-foreground mt-1">{chart.config.description}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={downloadChart}
          disabled={isDownloading}
          data-testid={`download-chart-${chartIndex}-btn`}
          className="h-7 px-2"
        >
          <DownloadSimple className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="p-4 pt-0" ref={chartRef}>
        {renderChart()}
      </CardContent>
    </Card>
  );
}
