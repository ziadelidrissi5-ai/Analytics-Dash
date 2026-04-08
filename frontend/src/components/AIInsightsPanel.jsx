import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  X,
  Brain,
  Lightbulb,
  Warning,
  Target,
  PaperPlaneTilt,
  Spinner,
} from "@phosphor-icons/react";

export function AIInsightsPanel({ insights, onClose, onAskQuestion, isLoading }) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (question.trim()) {
      onAskQuestion(question.trim());
      setQuestion("");
    }
  };

  return (
    <div className="fixed top-0 right-0 h-full w-96 border-l border-border bg-background/95 backdrop-blur-xl sidebar-panel z-50">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-accent" />
            <h3 className="font-serif text-lg font-bold">Analyse IA</h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            data-testid="close-ai-panel-btn"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-6">
            {/* Key Findings */}
            {insights.key_findings?.length > 0 && (
              <InsightSection
                icon={<Target className="h-4 w-4" />}
                title="Points cles"
                items={insights.key_findings}
                accentColor="text-accent"
              />
            )}

            {/* Insights */}
            {insights.insights?.length > 0 && (
              <InsightSection
                icon={<Lightbulb className="h-4 w-4" />}
                title="Observations"
                items={insights.insights}
                accentColor="text-chart-2"
              />
            )}

            {/* Anomalies */}
            {insights.anomalies?.length > 0 && (
              <InsightSection
                icon={<Warning className="h-4 w-4" />}
                title="Anomalies et risques"
                items={insights.anomalies}
                accentColor="text-destructive"
              />
            )}

            {/* Recommendations */}
            {insights.recommendations?.length > 0 && (
              <InsightSection
                icon={<Brain className="h-4 w-4" />}
                title="Recommandations"
                items={insights.recommendations}
                accentColor="text-chart-3"
              />
            )}
          </div>
        </ScrollArea>

        {/* Question Input */}
        <div className="p-4 border-t border-border">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Posez une question sur vos donnees..."
              disabled={isLoading}
              data-testid="ai-question-input"
              className="flex-1"
            />
            <Button
              type="submit"
              size="icon"
              disabled={isLoading || !question.trim()}
              data-testid="ai-submit-question-btn"
              className="bg-accent hover:bg-accent/90"
            >
              {isLoading ? (
                <Spinner className="h-4 w-4 animate-spin" />
              ) : (
                <PaperPlaneTilt className="h-4 w-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

function InsightSection({ icon, title, items, accentColor }) {
  return (
    <div className="space-y-2">
      <div className={`flex items-center gap-2 ${accentColor}`}>
        {icon}
        <h4 className="text-sm font-semibold uppercase tracking-wider">
          {title}
        </h4>
      </div>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <Card key={idx} className="border border-border">
            <CardContent className="p-3">
              <p className="text-sm text-foreground/90">{item}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
