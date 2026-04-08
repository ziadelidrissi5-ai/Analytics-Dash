import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  CloudArrowUp,
  FileCsv,
  FileXls,
  File,
  Spinner,
  ArrowsLeftRight,
  Plus,
} from "@phosphor-icons/react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

export function MergeDatasetModal({
  currentDatasetId,
  currentDatasetInfo,
  onClose,
  onMergeComplete,
}) {
  const [secondDataset, setSecondDataset] = useState(null);
  const [secondDatasetInfo, setSecondDatasetInfo] = useState(null);
  const [mergeType, setMergeType] = useState("concat"); // concat, left_join, inner_join
  const [joinKey, setJoinKey] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isMerging, setIsMerging] = useState(false);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setSecondDataset(response.data.id);
      setSecondDatasetInfo(response.data);
      toast.success(`"${response.data.filename}" charge`, {
        description: `${response.data.row_count.toLocaleString()} lignes`,
      });
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Echec du chargement");
    } finally {
      setIsUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "application/json": [".json"],
    },
    multiple: false,
    disabled: isUploading,
  });

  const handleMerge = async () => {
    if (!secondDataset) {
      toast.error("Veuillez d'abord charger un second jeu de donnees");
      return;
    }

    if ((mergeType === "left_join" || mergeType === "inner_join") && !joinKey) {
      toast.error("Veuillez selectionner une colonne de jointure");
      return;
    }

    setIsMerging(true);
    try {
      const response = await axios.post(`${API}/datasets/merge`, {
        dataset1_id: currentDatasetId,
        dataset2_id: secondDataset,
        merge_type: mergeType,
        join_key: joinKey || null,
      });

      onMergeComplete(response.data.id, response.data);
    } catch (error) {
      console.error("Merge error:", error);
      toast.error("Echec de la fusion", {
        description: error.response?.data?.detail || "Veuillez reessayer",
      });
    } finally {
      setIsMerging(false);
    }
  };

  // Find common columns between datasets for join suggestions
  const commonColumns =
    currentDatasetInfo && secondDatasetInfo
      ? currentDatasetInfo.columns
          .filter((col1) =>
            secondDatasetInfo.columns.some((col2) => col2.name === col1.name)
          )
          .map((col) => col.name)
      : [];

  const getFileIcon = (filename) => {
    if (!filename) return File;
    const ext = filename.split(".").pop().toLowerCase();
    if (ext === "csv") return FileCsv;
    if (["xlsx", "xls"].includes(ext)) return FileXls;
    return File;
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">
            Fusion / croisement de jeux de donnees
          </DialogTitle>
          <DialogDescription>
            Combinez votre jeu de donnees actuel avec un autre fichier
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Current Dataset */}
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">
              Jeu de donnees actuel
            </Label>
            <Card className="border border-border">
              <CardContent className="p-3 flex items-center gap-3">
                {(() => {
                  const Icon = getFileIcon(currentDatasetInfo?.filename);
                  return <Icon className="h-8 w-8 text-accent" weight="duotone" />;
                })()}
                <div className="flex-1">
                  <p className="font-medium text-sm">{currentDatasetInfo?.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {currentDatasetInfo?.row_count.toLocaleString()} lignes •{" "}
                    {currentDatasetInfo?.column_count} colonnes
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Arrow */}
          <div className="flex justify-center">
            <div className="p-2 rounded-full bg-secondary">
              <Plus className="h-5 w-5 text-muted-foreground" />
            </div>
          </div>

          {/* Second Dataset Upload/Info */}
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider text-muted-foreground">
              Second jeu de donnees
            </Label>
            {!secondDatasetInfo ? (
              <Card
                {...getRootProps()}
                className={`border-2 border-dashed cursor-pointer transition-colors ${
                  isDragActive
                    ? "border-accent bg-accent/5"
                    : "border-border hover:border-muted-foreground"
                } ${isUploading ? "pointer-events-none opacity-60" : ""}`}
                data-testid="merge-upload-zone"
              >
                <input {...getInputProps()} />
                <CardContent className="p-6 flex flex-col items-center gap-2">
                  {isUploading ? (
                    <Spinner className="h-8 w-8 animate-spin text-accent" />
                  ) : (
                    <CloudArrowUp className="h-8 w-8 text-muted-foreground" />
                  )}
                  <p className="text-sm text-center">
                    {isUploading
                      ? "Chargement..."
                      : "Deposez un fichier ici ou cliquez pour parcourir"}
                  </p>
                  <div className="flex gap-2">
                    <Badge variant="secondary">CSV</Badge>
                    <Badge variant="secondary">Excel</Badge>
                    <Badge variant="secondary">JSON</Badge>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border border-accent">
                <CardContent className="p-3 flex items-center gap-3">
                  {(() => {
                    const Icon = getFileIcon(secondDatasetInfo.filename);
                    return <Icon className="h-8 w-8 text-accent" weight="duotone" />;
                  })()}
                  <div className="flex-1">
                    <p className="font-medium text-sm">{secondDatasetInfo.filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {secondDatasetInfo.row_count.toLocaleString()} lignes •{" "}
                      {secondDatasetInfo.column_count} colonnes
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSecondDataset(null);
                      setSecondDatasetInfo(null);
                    }}
                  >
                    Changer
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Merge Options */}
          {secondDatasetInfo && (
            <div className="space-y-4 p-4 bg-secondary/50 rounded-lg">
              <div className="space-y-2">
                <Label className="text-sm font-medium">Type de fusion</Label>
                <Select value={mergeType} onValueChange={setMergeType}>
                  <SelectTrigger data-testid="merge-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="concat">
                      <div className="flex items-center gap-2">
                        <span>Concatener (ajouter les lignes)</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="left_join">
                      <div className="flex items-center gap-2">
                        <span>Jointure gauche (garder tout l'actuel)</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="inner_join">
                      <div className="flex items-center gap-2">
                        <span>Jointure interne (garder les correspondances)</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Join Key Selection */}
              {(mergeType === "left_join" || mergeType === "inner_join") && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Colonne de jointure</Label>
                  {commonColumns.length > 0 ? (
                    <Select value={joinKey} onValueChange={setJoinKey}>
                      <SelectTrigger data-testid="join-key-select">
                        <SelectValue placeholder="Selectionnez une colonne commune" />
                      </SelectTrigger>
                      <SelectContent>
                        {commonColumns.map((col) => (
                          <SelectItem key={col} value={col}>
                            {col}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <p className="text-sm text-destructive">
                      Aucune colonne commune trouvee entre les jeux de donnees. Utilisez plutot la concatenation.
                    </p>
                  )}
                  {commonColumns.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {commonColumns.length} colonne(s) commune(s) trouvee(s) :{" "}
                      {commonColumns.slice(0, 5).join(", ")}
                      {commonColumns.length > 5 && "..."}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={handleMerge}
            disabled={!secondDatasetInfo || isMerging}
            data-testid="merge-datasets-btn"
            className="bg-accent hover:bg-accent/90"
          >
            {isMerging ? (
              <>
                <Spinner className="h-4 w-4 mr-2 animate-spin" />
                Fusion...
              </>
            ) : (
              <>
                <ArrowsLeftRight className="h-4 w-4 mr-2" />
                Fusionner
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
