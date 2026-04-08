import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  FileText,
  Download,
  Spinner,
  Table,
} from "@phosphor-icons/react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

export function ReportGenerator({ datasetId, datasetInfo, onClose }) {
  const [reportType, setReportType] = useState("business");
  const [exportFormat, setExportFormat] = useState("json");
  const [sections, setSections] = useState({
    summary: true,
    kpis: true,
    trends: true,
    recommendations: true,
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [reportData, setReportData] = useState(null);

  const toggleSection = (section) => {
    setSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const generateReport = async () => {
    setIsGenerating(true);

    try {
      const response = await axios.post(`${API}/datasets/${datasetId}/report`, {
        dataset_id: datasetId,
        report_type: reportType,
        sections: Object.entries(sections)
          .filter(([_, enabled]) => enabled)
          .map(([section]) => section),
      });

      const data = response.data;
      setReportData(data);

      if (exportFormat === "json") {
        downloadJSON(data);
      } else if (exportFormat === "csv") {
        downloadCSV(data);
      } else if (exportFormat === "txt") {
        downloadTextReport(data);
      }

      toast.success("Report generated successfully");
    } catch (error) {
      console.error("Report generation error:", error);
      toast.error("Failed to generate report");
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadJSON = (data) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${datasetInfo?.filename || "report"}_analysis.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadCSV = (data) => {
    let csv = "Analytics Report\n\n";
    
    // Summary
    csv += "SUMMARY\n";
    csv += `Total Records,${data.summary.total_records}\n`;
    csv += `Total Columns,${data.summary.total_columns}\n`;
    csv += `Data Completeness,${data.summary.data_completeness}%\n\n`;

    // KPIs
    if (data.kpis) {
      csv += "KEY PERFORMANCE INDICATORS\n";
      csv += "Name,Value\n";
      data.kpis.forEach(kpi => {
        csv += `"${kpi.name}","${kpi.value}"\n`;
      });
      csv += "\n";
    }

    // Correlations
    if (data.correlations?.length > 0) {
      csv += "CORRELATIONS\n";
      csv += "Column 1,Column 2,Correlation,Strength\n";
      data.correlations.forEach(corr => {
        csv += `"${corr.column1}","${corr.column2}",${corr.correlation},"${corr.strength}"\n`;
      });
      csv += "\n";
    }

    // Columns Overview
    if (data.columns_overview) {
      csv += "COLUMNS OVERVIEW\n";
      csv += "Column,Type,Unique Values,Missing Values,Missing %\n";
      data.columns_overview.forEach(col => {
        csv += `"${col.name}","${col.type}",${col.unique_values},${col.missing_values},${col.missing_percentage}\n`;
      });
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${datasetInfo?.filename || "report"}_analysis.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadTextReport = (data) => {
    let text = "=" .repeat(60) + "\n";
    text += `ANALYTICS REPORT: ${data.title}\n`;
    text += "=" .repeat(60) + "\n\n";
    text += `Generated: ${new Date(data.generated_at).toLocaleString()}\n\n`;

    // Summary
    text += "-".repeat(40) + "\n";
    text += "EXECUTIVE SUMMARY\n";
    text += "-".repeat(40) + "\n";
    text += `Total Records: ${data.summary.total_records.toLocaleString()}\n`;
    text += `Total Columns: ${data.summary.total_columns}\n`;
    text += `Data Completeness: ${data.summary.data_completeness}%\n`;
    text += `Numeric Columns: ${data.summary.numeric_columns}\n\n`;

    // KPIs
    if (data.kpis) {
      text += "-".repeat(40) + "\n";
      text += "KEY PERFORMANCE INDICATORS\n";
      text += "-".repeat(40) + "\n";
      data.kpis.forEach(kpi => {
        const value = typeof kpi.value === "number" 
          ? kpi.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
          : kpi.value;
        text += `• ${kpi.name}: ${value}\n`;
      });
      text += "\n";
    }

    // Correlations
    if (data.correlations?.length > 0) {
      text += "-".repeat(40) + "\n";
      text += "KEY CORRELATIONS\n";
      text += "-".repeat(40) + "\n";
      data.correlations.slice(0, 10).forEach(corr => {
        text += `• ${corr.column1} ↔ ${corr.column2}: ${corr.correlation.toFixed(3)} (${corr.strength})\n`;
      });
      text += "\n";
    }

    // Anomalies
    if (data.anomalies?.length > 0) {
      text += "-".repeat(40) + "\n";
      text += "DETECTED ANOMALIES\n";
      text += "-".repeat(40) + "\n";
      data.anomalies.forEach(anom => {
        text += `• ${anom.description}\n`;
      });
      text += "\n";
    }

    // Column Overview
    if (data.columns_overview) {
      text += "-".repeat(40) + "\n";
      text += "COLUMN ANALYSIS\n";
      text += "-".repeat(40) + "\n";
      data.columns_overview.forEach(col => {
        text += `• ${col.name} (${col.type}): ${col.unique_values} unique, ${col.missing_percentage}% missing\n`;
      });
    }

    const blob = new Blob([text], { type: "text/plain;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${datasetInfo?.filename || "report"}_analysis.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">
            Generate Report
          </DialogTitle>
          <DialogDescription>
            Create a professional analysis report for your dataset
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Report Type */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Report Style</Label>
            <RadioGroup
              value={reportType}
              onValueChange={setReportType}
              className="grid grid-cols-3 gap-2"
            >
              <Label
                htmlFor="business"
                className={`flex flex-col items-center justify-center p-3 border rounded cursor-pointer transition-colors ${
                  reportType === "business"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
              >
                <RadioGroupItem
                  value="business"
                  id="business"
                  className="sr-only"
                />
                <span className="text-sm font-medium">Business</span>
              </Label>
              <Label
                htmlFor="technical"
                className={`flex flex-col items-center justify-center p-3 border rounded cursor-pointer transition-colors ${
                  reportType === "technical"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
              >
                <RadioGroupItem
                  value="technical"
                  id="technical"
                  className="sr-only"
                />
                <span className="text-sm font-medium">Technical</span>
              </Label>
              <Label
                htmlFor="strategic"
                className={`flex flex-col items-center justify-center p-3 border rounded cursor-pointer transition-colors ${
                  reportType === "strategic"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
              >
                <RadioGroupItem
                  value="strategic"
                  id="strategic"
                  className="sr-only"
                />
                <span className="text-sm font-medium">Strategic</span>
              </Label>
            </RadioGroup>
          </div>

          {/* Export Format */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Export Format</Label>
            <div className="grid grid-cols-3 gap-2">
              <Card
                className={`cursor-pointer transition-colors ${
                  exportFormat === "txt"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
                onClick={() => setExportFormat("txt")}
                data-testid="export-txt-option"
              >
                <CardContent className="flex flex-col items-center p-3">
                  <FileText className="h-6 w-6 mb-1" />
                  <span className="text-xs font-medium">Text Report</span>
                </CardContent>
              </Card>
              <Card
                className={`cursor-pointer transition-colors ${
                  exportFormat === "csv"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
                onClick={() => setExportFormat("csv")}
                data-testid="export-csv-option"
              >
                <CardContent className="flex flex-col items-center p-3">
                  <Table className="h-6 w-6 mb-1" />
                  <span className="text-xs font-medium">CSV</span>
                </CardContent>
              </Card>
              <Card
                className={`cursor-pointer transition-colors ${
                  exportFormat === "json"
                    ? "border-accent bg-accent/10"
                    : "border-border hover:bg-muted"
                }`}
                onClick={() => setExportFormat("json")}
                data-testid="export-json-option"
              >
                <CardContent className="flex flex-col items-center p-3">
                  <FileText className="h-6 w-6 mb-1" />
                  <span className="text-xs font-medium">JSON</span>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Sections */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Include Sections</Label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(sections).map(([section, enabled]) => (
                <div key={section} className="flex items-center space-x-2">
                  <Checkbox
                    id={section}
                    checked={enabled}
                    onCheckedChange={() => toggleSection(section)}
                    data-testid={`section-${section}-checkbox`}
                  />
                  <Label htmlFor={section} className="text-sm capitalize">
                    {section}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={generateReport}
            disabled={isGenerating}
            data-testid="generate-report-submit-btn"
            className="bg-accent hover:bg-accent/90"
          >
            {isGenerating ? (
              <>
                <Spinner className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Generate Report
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
