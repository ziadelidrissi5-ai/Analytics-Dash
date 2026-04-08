import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  ChartBar,
  Link,
  Warning,
} from "@phosphor-icons/react";

/**
 * SheetSelector – tab bar shown when a multi-sheet workbook is loaded.
 *
 * Props:
 *  workbookInfo    – WorkbookInfo object from the backend
 *  activeSheetId   – currently selected dataset_id (or "global")
 *  onSelectSheet   – (dataset_id) => void
 *  onSelectGlobal  – () => void
 *  isLoading       – bool
 */
export function SheetSelector({
  workbookInfo,
  activeSheetId,
  onSelectSheet,
  onSelectGlobal,
  isLoading,
}) {
  if (!workbookInfo) return null;

  const { sheets, detected_relations = [] } = workbookInfo;
  const hasRelations = detected_relations.length > 0;

  return (
    <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="px-6 py-0 flex items-center gap-1 overflow-x-auto scrollbar-none">
        {/* Per-sheet tabs */}
        {sheets.map((sheet) => {
          const isActive = activeSheetId === sheet.dataset_id;
          return (
            <button
              key={sheet.dataset_id}
              onClick={() => !isLoading && onSelectSheet(sheet.dataset_id)}
              disabled={isLoading}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all whitespace-nowrap
                ${isActive
                  ? "border-accent text-accent"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                }
                ${isLoading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              <Table className="h-3.5 w-3.5" />
              <span>{sheet.sheet_name}</span>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                {sheet.row_count.toLocaleString()}r
              </Badge>
            </button>
          );
        })}

        {/* Divider */}
        <div className="h-5 w-px bg-border mx-1 shrink-0" />

        {/* Global / cross-sheet tab */}
        <button
          onClick={() => !isLoading && onSelectGlobal()}
          disabled={isLoading}
          className={`
            flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all whitespace-nowrap
            ${activeSheetId === "global"
              ? "border-accent text-accent"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }
            ${isLoading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
          `}
        >
          <ChartBar className="h-3.5 w-3.5" />
          <span>Vue globale</span>
          {hasRelations && (
            <Badge className="text-[10px] px-1.5 py-0 h-4 bg-accent/20 text-accent border-accent/30">
              <Link className="h-2.5 w-2.5 mr-0.5" />
              {detected_relations.length}
            </Badge>
          )}
        </button>

        {/* Relations summary (right side) */}
        {hasRelations && (
          <div className="ml-auto shrink-0 flex items-center gap-2 text-xs text-muted-foreground py-3 pl-4">
            <Link className="h-3 w-3 text-accent" />
            <span>
              {detected_relations.length} relation{detected_relations.length > 1 ? "s" : ""} détectée{detected_relations.length > 1 ? "s" : ""}
            </span>
            {detected_relations[0]?.join_keys?.length > 0 && (
              <Badge variant="outline" className="text-[10px]">
                via &quot;{detected_relations[0].join_keys[0]}&quot;
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Relations detail strip */}
      {hasRelations && (
        <div className="px-6 pb-2 flex flex-wrap gap-2">
          {detected_relations.slice(0, 3).map((rel, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1.5 text-xs bg-accent/5 border border-accent/20 rounded-full px-3 py-0.5"
            >
              <Link className="h-3 w-3 text-accent" />
              <span className="text-muted-foreground">
                <span className="text-foreground font-medium">{rel.sheet1}</span>
                {" ↔ "}
                <span className="text-foreground font-medium">{rel.sheet2}</span>
                {rel.join_keys?.length > 0 && (
                  <span className="text-accent ml-1">via &quot;{rel.join_keys[0]}&quot;</span>
                )}
              </span>
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-4 ml-1"
              >
                {Math.round(rel.confidence * 100)}%
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
