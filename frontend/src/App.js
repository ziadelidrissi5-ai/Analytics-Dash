import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";

// Components
import { Header } from "@/components/Header";
import { FileUpload } from "@/components/FileUpload";
import { DataPreview } from "@/components/DataPreview";
import { Dashboard } from "@/components/Dashboard";
import { AIInsightsPanel } from "@/components/AIInsightsPanel";
import { ReportGenerator } from "@/components/ReportGenerator";
import { FilterPanel } from "@/components/FilterPanel";
import { MergeDatasetModal } from "@/components/MergeDatasetModal";
import { SheetSelector } from "@/components/SheetSelector";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

function MainApp() {
  const [theme, setTheme] = useState("dark");

  // Single-dataset state
  const [currentDataset, setCurrentDataset] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);

  // Workbook (multi-sheet) state
  const [workbookInfo, setWorkbookInfo] = useState(null);   // WorkbookInfo | null
  const [activeSheetId, setActiveSheetId] = useState(null); // dataset_id | "global"

  // View state
  const [dashboardData, setDashboardData] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [aiInsights, setAiInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeView, setActiveView] = useState("upload"); // upload | preview | dashboard

  // Panels
  const [filters, setFilters] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);

  // Apply theme
  useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
  }, [theme]);

  const toggleTheme = () => setTheme((p) => (p === "dark" ? "light" : "dark"));

  // ── Upload ──────────────────────────────────────────────────────────────────
  const handleFileUpload = async (file) => {
    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const data = response.data;

      if (data.is_workbook) {
        // ── Multi-sheet workbook ──
        setWorkbookInfo(data);
        const firstSheet = data.sheets[0];
        setActiveSheetId(firstSheet.dataset_id);
        setCurrentDataset(firstSheet.dataset_id);
        setDatasetInfo(firstSheet);

        toast.success(`Workbook "${data.filename}" chargé`, {
          description: `${data.sheets.length} feuilles détectées${
            data.detected_relations.length > 0
              ? `, ${data.detected_relations.length} relation(s) entre feuilles`
              : ""
          }`,
        });

        await fetchPreview(firstSheet.dataset_id);
        setActiveView("preview");
      } else {
        // ── Single dataset ──
        setWorkbookInfo(null);
        setActiveSheetId(null);
        setCurrentDataset(data.id);
        setDatasetInfo(data);

        toast.success(`Fichier "${data.filename}" chargé`, {
          description: `${data.row_count.toLocaleString()} lignes, ${data.column_count} colonnes`,
        });

        await fetchPreview(data.id);
        setActiveView("preview");
      }
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Échec du chargement", {
        description: error.response?.data?.detail || "Veuillez réessayer",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ── Sheet switching ──────────────────────────────────────────────────────────
  const switchSheet = useCallback(
    async (datasetId) => {
      if (!workbookInfo || datasetId === activeSheetId) return;

      setActiveSheetId(datasetId);
      setCurrentDataset(datasetId);
      setDashboardData(null);
      setAiInsights(null);
      setFilters([]);
      setShowAIPanel(false);

      const sheetInfo = workbookInfo.sheets.find((s) => s.dataset_id === datasetId);
      setDatasetInfo(sheetInfo);

      setIsLoading(true);
      try {
        await fetchPreview(datasetId);
        setActiveView("preview");
      } finally {
        setIsLoading(false);
      }
    },
    [workbookInfo, activeSheetId]
  );

  const switchToGlobal = useCallback(async () => {
    if (!workbookInfo || activeSheetId === "global") return;

    setActiveSheetId("global");
    setCurrentDataset(null);
    setDatasetInfo(null);
    setPreviewData(null);
    setDashboardData(null);
    setAiInsights(null);
    setFilters([]);
    setShowAIPanel(false);

    // Immediately generate the cross-sheet dashboard
    setIsLoading(true);
    try {
      const response = await axios.get(
        `${API}/workbooks/${workbookInfo.workbook_id}/cross-dashboard`
      );
      setDashboardData(response.data);
      setActiveView("dashboard");
      toast.success("Vue globale générée", {
        description: "Analyse croisée de toutes les feuilles terminée",
      });
    } catch (error) {
      console.error("Cross-dashboard error:", error);
      toast.error("Échec de la vue globale", {
        description: error.response?.data?.detail || "Veuillez réessayer",
      });
    } finally {
      setIsLoading(false);
    }
  }, [workbookInfo, activeSheetId]);

  // ── Preview ─────────────────────────────────────────────────────────────────
  const fetchPreview = async (datasetId, page = 1) => {
    try {
      const response = await axios.get(
        `${API}/datasets/${datasetId}/preview?page=${page}&page_size=50`
      );
      setPreviewData(response.data);
    } catch (error) {
      console.error("Preview error:", error);
      toast.error("Échec du chargement de l'aperçu");
    }
  };

  // ── Dashboard ────────────────────────────────────────────────────────────────
  const generateDashboard = async () => {
    if (!currentDataset) return;

    setIsLoading(true);
    try {
      const response = await axios.get(`${API}/datasets/${currentDataset}/dashboard`);
      setDashboardData(response.data);
      setActiveView("dashboard");
      toast.success("Tableau de bord genere", { description: "Analyse automatique terminee" });
    } catch (error) {
      console.error("Dashboard error:", error);
      toast.error("Echec de la generation du tableau de bord");
    } finally {
      setIsLoading(false);
    }
  };

  // ── AI Insights ───────────────────────────────────────────────────────────────
  const fetchAIInsights = async (question = null) => {
    if (!currentDataset) return;

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/datasets/${currentDataset}/ai-insights`, {
        dataset_id: currentDataset,
        question,
      });
      setAiInsights(response.data);
      setShowAIPanel(true);
      toast.success("Analyse IA terminée");
    } catch (error) {
      console.error("AI insights error:", error);
      toast.error("Échec de l'analyse IA");
    } finally {
      setIsLoading(false);
    }
  };

  // ── Filters ───────────────────────────────────────────────────────────────────
  const applyFilters = useCallback(
    async (newFilters) => {
      if (!currentDataset) return;
      setFilters(newFilters);
      if (newFilters.length === 0) {
        await fetchPreview(currentDataset);
        return;
      }
      try {
        const response = await axios.post(`${API}/datasets/${currentDataset}/filter`, newFilters);
        setPreviewData(response.data);
      } catch (error) {
        console.error("Filter error:", error);
        toast.error("Échec du filtre");
      }
    },
    [currentDataset]
  );

  // ── Merge ─────────────────────────────────────────────────────────────────────
  const handleMergeComplete = async (newDatasetId, newDatasetInfo) => {
    setCurrentDataset(newDatasetId);
    setDatasetInfo(newDatasetInfo);
    await fetchPreview(newDatasetId);
    setShowMergeModal(false);
    setDashboardData(null);
    setActiveView("preview");
    toast.success("Datasets fusionnés", {
      description: `${newDatasetInfo.row_count.toLocaleString()} lignes, ${newDatasetInfo.column_count} colonnes`,
    });
  };

  // ── Reset ─────────────────────────────────────────────────────────────────────
  const resetWorkspace = () => {
    setCurrentDataset(null);
    setDatasetInfo(null);
    setWorkbookInfo(null);
    setActiveSheetId(null);
    setDashboardData(null);
    setPreviewData(null);
    setAiInsights(null);
    setFilters([]);
    setActiveView("upload");
    setShowAIPanel(false);
  };

  // ── Derived helpers ───────────────────────────────────────────────────────────
  const isMultiSheet = !!workbookInfo && workbookInfo.sheets.length > 1;
  const isGlobalView = activeSheetId === "global";

  // datasetInfo for header: use sheet info or single dataset info
  const headerDatasetInfo = isGlobalView
    ? { filename: workbookInfo?.filename, row_count: null, column_count: null, columns: [] }
    : datasetInfo;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Toaster richColors position="top-right" />

      <Header
        theme={theme}
        toggleTheme={toggleTheme}
        datasetInfo={headerDatasetInfo}
        activeView={activeView}
        setActiveView={setActiveView}
        onNewDataset={resetWorkspace}
        onGenerateDashboard={isGlobalView ? undefined : generateDashboard}
        onShowFilters={() => setShowFilters(!showFilters)}
        onShowAI={isGlobalView ? undefined : () => fetchAIInsights()}
        onShowReport={() => setShowReportModal(true)}
        isLoading={isLoading}
        hasDataset={!!currentDataset || isGlobalView}
      />

      {/* Sheet tabs (only shown for multi-sheet workbooks) */}
      {isMultiSheet && activeView !== "upload" && (
        <SheetSelector
          workbookInfo={workbookInfo}
          activeSheetId={activeSheetId}
          onSelectSheet={switchSheet}
          onSelectGlobal={switchToGlobal}
          isLoading={isLoading}
        />
      )}

      <main className="relative">
        {/* Filter Panel */}
        {showFilters && datasetInfo && !isGlobalView && (
          <FilterPanel
            columns={datasetInfo.columns}
            filters={filters}
            onApplyFilters={applyFilters}
            onClose={() => setShowFilters(false)}
          />
        )}

        {/* AI Insights Sidebar */}
        {showAIPanel && aiInsights && (
          <AIInsightsPanel
            insights={aiInsights}
            onClose={() => setShowAIPanel(false)}
            onAskQuestion={fetchAIInsights}
            isLoading={isLoading}
          />
        )}

        {/* Main Content */}
        <div className={`transition-all duration-300 ${showAIPanel ? "mr-96" : ""}`}>
          {activeView === "upload" && (
            <FileUpload onUpload={handleFileUpload} isLoading={isLoading} />
          )}

          {activeView === "preview" && previewData && datasetInfo && !isGlobalView && (
            <DataPreview
              data={previewData}
              datasetInfo={datasetInfo}
              onPageChange={(page) => fetchPreview(currentDataset, page)}
              onGenerateDashboard={generateDashboard}
            />
          )}

          {activeView === "dashboard" && dashboardData && (
            <Dashboard
              data={dashboardData}
              datasetInfo={
                isGlobalView
                  ? {
                      filename: workbookInfo?.filename,
                      columns: [],
                      row_count: null,
                      column_count: null,
                    }
                  : datasetInfo
              }
              sheetName={
                isGlobalView
                  ? null
                  : workbookInfo?.sheets?.find((s) => s.dataset_id === activeSheetId)?.sheet_name
              }
              isGlobalView={isGlobalView}
              workbookRelations={isGlobalView ? workbookInfo?.detected_relations : null}
              onShowAI={isGlobalView ? undefined : () => fetchAIInsights()}
              onMergeDataset={isGlobalView ? undefined : () => setShowMergeModal(true)}
            />
          )}
        </div>

        {/* Report Generator Modal */}
        {showReportModal && currentDataset && (
          <ReportGenerator
            datasetId={currentDataset}
            datasetInfo={datasetInfo}
            onClose={() => setShowReportModal(false)}
          />
        )}

        {/* Merge Dataset Modal */}
        {showMergeModal && currentDataset && (
          <MergeDatasetModal
            currentDatasetId={currentDataset}
            currentDatasetInfo={datasetInfo}
            onClose={() => setShowMergeModal(false)}
            onMergeComplete={handleMergeComplete}
          />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainApp />} />
        <Route path="*" element={<MainApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
