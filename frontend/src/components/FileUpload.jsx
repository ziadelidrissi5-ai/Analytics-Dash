import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  CloudArrowUp,
  FileXls,
  FileCsv,
  File,
  Spinner,
  CheckCircle,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function FileUpload({ onUpload, isLoading }) {
  const [selectedFile, setSelectedFile] = useState(null);

  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        setSelectedFile(file);
        onUpload(file);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        ".xlsx",
      ],
      "application/vnd.ms-excel": [".xls"],
      "application/json": [".json"],
    },
    multiple: false,
    disabled: isLoading,
  });

  const getFileIcon = (filename) => {
    if (!filename) return File;
    const ext = filename.split(".").pop().toLowerCase();
    if (ext === "csv") return FileCsv;
    if (["xlsx", "xls"].includes(ext)) return FileXls;
    return File;
  };

  const FileIcon = selectedFile ? getFileIcon(selectedFile.name) : CloudArrowUp;

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] p-6">
      <div className="w-full max-w-3xl">
        {/* Hero Text */}
        <div className="text-center mb-8">
          <h2 className="font-serif text-4xl md:text-5xl font-bold mb-4">
            Des tableaux de bord qui s'adaptent a vos donnees
          </h2>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            Importez votre fichier et laissez Z.Analytics analyser vos
            donnees, detecter les tendances et generer automatiquement les
            visualisations les plus pertinentes.
          </p>
        </div>

        {/* Upload Zone */}
        <Card
          {...getRootProps()}
          className={`upload-zone cursor-pointer border-2 border-dashed p-12 text-center transition-all ${
            isDragActive
              ? "dragging border-accent bg-accent/5"
              : "border-border hover:border-muted-foreground"
          } ${isLoading ? "pointer-events-none opacity-60" : ""}`}
          data-testid="file-upload-zone"
        >
          <input {...getInputProps()} data-testid="file-input" />

          <div className="flex flex-col items-center gap-4">
            {/* Icon */}
            <div
              className={`h-20 w-20 rounded-full flex items-center justify-center ${
                isLoading
                  ? "bg-accent/20"
                  : selectedFile
                    ? "bg-accent/20"
                    : "bg-secondary"
              }`}
            >
              {isLoading ? (
                <Spinner className="h-10 w-10 text-accent animate-spin" />
              ) : (
                <FileIcon
                  className={`h-10 w-10 ${selectedFile ? "text-accent" : "text-muted-foreground"}`}
                  weight="duotone"
                />
              )}
            </div>

            {/* Text */}
            {isLoading ? (
              <div>
                <p className="text-lg font-medium">Analyse de vos donnees...</p>
                <p className="text-sm text-muted-foreground">
                  Detection des types de colonnes et des tendances
                </p>
              </div>
            ) : isDragActive ? (
              <div>
                <p className="text-lg font-medium text-accent">
                  Deposez votre fichier ici
                </p>
              </div>
            ) : (
              <div>
                <p className="text-lg font-medium">
                  Glissez-deposez votre fichier ici
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  ou cliquez pour parcourir
                </p>
              </div>
            )}

            {/* Supported formats */}
            <div className="flex items-center gap-4 mt-4">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <FileCsv className="h-4 w-4" />
                <span>CSV</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <FileXls className="h-4 w-4" />
                <span>Excel</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <File className="h-4 w-4" />
                <span>JSON</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <FeatureCard
            icon="📊"
            title="Tableaux de bord automatiques"
            description="Des visualisations adaptees a la structure de vos donnees"
          />
          <FeatureCard
            icon="🧠"
            title="Analyse IA"
            description="Des analyses et recommandations plus pertinentes"
          />
          <FeatureCard
            icon="📄"
            title="Export de rapports"
            description="Generez des rapports exploitables a partir de vos donnees"
          />
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <Card className="p-4 border border-border">
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </Card>
  );
}
