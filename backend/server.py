from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import json
import io
from scipy import stats
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None

try:
    from google import genai as google_genai
    from google.genai import types as google_types
except ImportError:
    google_genai = None
    google_types = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Analytics Engine API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ==============================================================================
# Pydantic Models
# ==============================================================================

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    unique_count: int
    null_count: int
    sample_values: List[Any]
    is_numeric: bool
    is_temporal: bool
    is_categorical: bool
    stats: Optional[Dict[str, Any]] = None


class DatasetInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    file_size: int
    detected_relations: List[Dict[str, Any]] = []


class DatasetResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    filename: str
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    created_at: str
    file_size: int


class KPIMetric(BaseModel):
    name: str
    value: Any
    change: Optional[float] = None
    change_type: Optional[str] = None
    format: str = "number"


class ChartConfig(BaseModel):
    chart_type: str
    title: str
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    data: List[Dict[str, Any]]
    config: Dict[str, Any] = {}


class DashboardResponse(BaseModel):
    dataset_id: str
    kpis: List[KPIMetric]
    charts: List[ChartConfig]
    correlations: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]


class FilterRequest(BaseModel):
    column: str
    operator: str
    value: Any


class AggregationRequest(BaseModel):
    dataset_id: str
    group_by: List[str]
    aggregations: Dict[str, str]
    filters: List[FilterRequest] = []


class CalculatedColumnRequest(BaseModel):
    dataset_id: str
    new_column_name: str
    expression: str


class AIInsightRequest(BaseModel):
    dataset_id: str
    question: Optional[str] = None


class AIInsightResponse(BaseModel):
    insights: List[str]
    recommendations: List[str]
    anomalies: List[str]
    key_findings: List[str]


class ReportRequest(BaseModel):
    dataset_id: str
    report_type: str = "business"
    sections: List[str] = ["summary", "kpis", "trends", "recommendations"]


class MergeRequest(BaseModel):
    dataset1_id: str
    dataset2_id: str
    merge_type: str = "concat"  # concat, left_join, inner_join
    join_key: Optional[str] = None


class SheetInfo(BaseModel):
    sheet_name: str
    dataset_id: str
    row_count: int
    column_count: int
    columns: List[ColumnInfo]


class CrossSheetRelation(BaseModel):
    sheet1: str
    sheet2: str
    sheet1_id: str
    sheet2_id: str
    common_columns: List[str]
    join_keys: List[str]
    relation_type: str  # "join" | "reference" | "lookup"
    confidence: float


class WorkbookInfo(BaseModel):
    workbook_id: str
    filename: str
    file_size: int
    sheets: List[SheetInfo]
    detected_relations: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UploadResponse(BaseModel):
    """Unified upload response for both single-sheet and multi-sheet files."""
    is_workbook: bool = False
    # Single dataset fields (is_workbook=False)
    id: Optional[str] = None
    filename: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[ColumnInfo]] = None
    created_at: Optional[str] = None
    file_size: int
    # Workbook fields (is_workbook=True)
    workbook_id: Optional[str] = None
    sheets: List[SheetInfo] = []
    detected_relations: List[Dict[str, Any]] = []


# ==============================================================================
# Helper Functions
# ==============================================================================

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

def detect_column_type(series: pd.Series) -> Dict[str, Any]:
    """Detect the type of a pandas Series."""
    dtype_str = str(series.dtype)
    is_numeric = pd.api.types.is_numeric_dtype(series)
    is_temporal = pd.api.types.is_datetime64_any_dtype(series)
    is_categorical = False
    
    # Try to detect temporal
    if not is_numeric and not is_temporal and series.dtype == 'object':
        try:
            pd.to_datetime(series.dropna().head(100))
            is_temporal = True
        except (ValueError, TypeError):
            pass
    
    # Detect categorical
    if not is_numeric and not is_temporal:
        unique_ratio = series.nunique() / len(series) if len(series) > 0 else 0
        is_categorical = unique_ratio < 0.5 or series.nunique() < 50
    
    return {
        "dtype": dtype_str,
        "is_numeric": is_numeric,
        "is_temporal": is_temporal,
        "is_categorical": is_categorical
    }


def calculate_column_stats(series: pd.Series, is_numeric: bool) -> Dict[str, Any]:
    """Calculate statistics for a column."""
    stats_dict = {}
    
    if is_numeric:
        stats_dict = {
            "mean": float(series.mean()) if not pd.isna(series.mean()) else None,
            "median": float(series.median()) if not pd.isna(series.median()) else None,
            "std": float(series.std()) if not pd.isna(series.std()) else None,
            "min": float(series.min()) if not pd.isna(series.min()) else None,
            "max": float(series.max()) if not pd.isna(series.max()) else None,
            "q25": float(series.quantile(0.25)) if not pd.isna(series.quantile(0.25)) else None,
            "q75": float(series.quantile(0.75)) if not pd.isna(series.quantile(0.75)) else None,
        }
    else:
        value_counts = series.value_counts().head(10).to_dict()
        stats_dict = {
            "top_values": {str(k): int(v) for k, v in value_counts.items()},
            "mode": str(series.mode().iloc[0]) if len(series.mode()) > 0 else None
        }
    
    return convert_numpy_types(stats_dict)


def detect_anomalies(df: pd.DataFrame, numeric_columns: List[str]) -> List[Dict[str, Any]]:
    """Detect anomalies in numeric columns using Z-score."""
    anomalies = []
    
    for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
        series = df[col].dropna()
        if len(series) < 10:
            continue
            
        z_scores = np.abs(stats.zscore(series))
        anomaly_indices = np.where(z_scores > 3)[0]
        
        if len(anomaly_indices) > 0:
            anomalies.append({
                "column": col,
                "count": int(len(anomaly_indices)),
                "percentage": float(round(len(anomaly_indices) / len(series) * 100, 2)),
                "description": f"{len(anomaly_indices)} outliers detected in '{col}' (values beyond 3 standard deviations)"
            })
    
    return convert_numpy_types(anomalies)


def calculate_correlations(df: pd.DataFrame, numeric_columns: List[str]) -> List[Dict[str, Any]]:
    """Calculate correlations between numeric columns."""
    correlations = []
    
    if len(numeric_columns) < 2:
        return correlations
    
    corr_matrix = df[numeric_columns].corr()
    
    for i, col1 in enumerate(numeric_columns):
        for col2 in numeric_columns[i+1:]:
            corr_value = corr_matrix.loc[col1, col2]
            if not pd.isna(corr_value) and abs(corr_value) > 0.5:
                correlations.append({
                    "column1": col1,
                    "column2": col2,
                    "correlation": float(round(corr_value, 3)),
                    "strength": "strong" if abs(corr_value) > 0.7 else "moderate"
                })
    
    return sorted(correlations, key=lambda x: abs(x["correlation"]), reverse=True)[:10]


DOMAIN_KEYWORDS = {
    "finance": [
        "revenue", "profit", "margin", "expense", "cost", "amount", "price", "sales",
        "income", "cash", "ebitda", "balance", "asset", "liability", "invoice",
        "payment", "budget", "forecast", "turnover"
    ],
    "customers": [
        "customer", "client", "user", "account", "segment", "churn", "retention",
        "lifetime", "nps", "satisfaction", "signup", "subscription", "cohort"
    ],
    "marketing": [
        "campaign", "channel", "lead", "click", "impression", "conversion", "ctr",
        "cpc", "cac", "roas", "reach", "engagement", "traffic", "session", "source"
    ],
    "sales": [
        "deal", "pipeline", "opportunity", "order", "quota", "region", "product",
        "seller", "salesperson", "rep", "booking", "closed", "won"
    ],
    "hr": [
        "employee", "salary", "department", "headcount", "hire", "termination",
        "attrition", "tenure", "payroll", "manager", "team", "performance"
    ],
    "operations": [
        "operation", "shipment", "delivery", "throughput", "cycle", "process",
        "utilization", "downtime", "capacity", "sla", "queue", "ticket"
    ],
    "inventory": [
        "inventory", "stock", "warehouse", "sku", "product", "supplier",
        "reorder", "on_hand", "backorder", "fulfillment", "units"
    ],
    "healthcare": [
        "patient", "hospital", "clinic", "diagnosis", "treatment", "visit",
        "admission", "discharge", "provider", "claim", "medical"
    ],
}


def normalize_column_name(name: str) -> str:
    return str(name).strip().lower().replace("_", " ").replace("-", " ")


def infer_format_from_name(name: str) -> str:
    lowered = normalize_column_name(name)
    if any(token in lowered for token in ["margin", "rate", "ratio", "share", "percent", "pct", "%"]):
        return "percentage"
    if any(token in lowered for token in ["revenue", "sales", "amount", "price", "cost", "profit", "income", "cash", "budget", "expense"]):
        return "currency"
    if any(token in lowered for token in ["count", "qty", "quantity", "volume", "units", "customers", "orders", "transactions"]):
        return "integer"
    return "number"


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and coerce obvious numeric/date columns."""
    df = df.copy()

    cleaned_columns = []
    seen = {}
    for col in df.columns:
        base = str(col).strip() or "column"
        count = seen.get(base, 0)
        seen[base] = count + 1
        cleaned_columns.append(base if count == 0 else f"{base}_{count + 1}")
    df.columns = cleaned_columns

    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue

        if series.dtype == "object":
            stripped = series.astype(str).str.strip()
            stripped = stripped.replace({"": None, "nan": None, "None": None, "null": None, "NULL": None})
            non_null = stripped.dropna()
            if len(non_null) == 0:
                df[col] = stripped
                continue

            numeric_candidate = non_null.str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("€", "", regex=False).str.replace("%", "", regex=False)
            numeric_converted = pd.to_numeric(numeric_candidate, errors="coerce")
            numeric_ratio = numeric_converted.notna().mean() if len(non_null) > 0 else 0

            should_try_date = any(token in normalize_column_name(col) for token in ["date", "time", "month", "year", "day"])
            date_converted = pd.to_datetime(non_null, errors="coerce")
            date_ratio = date_converted.notna().mean() if len(non_null) > 0 else 0

            if should_try_date and date_ratio >= 0.7:
                df[col] = pd.to_datetime(stripped, errors="coerce")
            elif numeric_ratio >= 0.8:
                df[col] = pd.to_numeric(
                    stripped.str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("€", "", regex=False).str.replace("%", "", regex=False),
                    errors="coerce"
                )
            else:
                df[col] = stripped

    return df


def infer_dataset_domain(columns_info: List[ColumnInfo], filename: str) -> str:
    search_space = [normalize_column_name(filename)] + [normalize_column_name(col.name) for col in columns_info]
    scores = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for text in search_space:
        for domain, keywords in DOMAIN_KEYWORDS.items():
            scores[domain] += sum(1 for keyword in keywords if keyword in text)

    best_domain = max(scores, key=scores.get)
    return best_domain if scores[best_domain] > 0 else "other"


def rank_columns(columns_info: List[ColumnInfo], predicate, keywords: Optional[List[str]] = None) -> List[str]:
    ranked = []
    keywords = keywords or []

    for col in columns_info:
        if not predicate(col):
            continue
        score = 0
        lowered = normalize_column_name(col.name)
        score += max(0, 100 - col.null_count)
        score += min(col.unique_count, 25)
        score += sum(20 for keyword in keywords if keyword in lowered)
        ranked.append((score, col.name))

    ranked.sort(reverse=True)
    return [name for _, name in ranked]


def semantic_score(name: str, keywords: List[str]) -> int:
    lowered = normalize_column_name(name)
    return sum(1 for keyword in keywords if keyword in lowered)


def choose_time_column(columns_info: List[ColumnInfo]) -> Optional[str]:
    temporal = [c.name for c in columns_info if c.is_temporal]
    if not temporal:
        return None
    priority = ["date", "month", "period", "time", "year", "quarter", "week", "day"]
    temporal.sort(key=lambda col: (-semantic_score(col, priority), len(col)))
    return temporal[0]


def choose_metric_columns(columns_info: List[ColumnInfo], domain: str, limit: int = 4) -> List[str]:
    domain_keywords = DOMAIN_KEYWORDS.get(domain, [])
    metrics = []
    for col in columns_info:
        if not col.is_numeric:
            continue
        lowered = normalize_column_name(col.name)
        variability = 0
        if col.stats and col.stats.get("mean") not in (None, 0) and col.stats.get("std") is not None:
            variability = abs(float(col.stats["std"])) / max(abs(float(col.stats["mean"])), 1e-9)
        score = 100
        score += semantic_score(lowered, domain_keywords) * 25
        score += semantic_score(lowered, ["revenue", "sales", "profit", "margin", "cost", "amount", "value", "score", "count", "rate", "price", "ebitda", "income"]) * 20
        score += min(col.unique_count, 50)
        score += min(int(variability * 20), 25)
        score -= min(col.null_count, 50)
        metrics.append((score, col.name))
    metrics.sort(reverse=True)
    return [name for _, name in metrics[:limit]]


def choose_dimension_columns(columns_info: List[ColumnInfo], domain: str, limit: int = 3) -> List[str]:
    domain_keywords = DOMAIN_KEYWORDS.get(domain, [])
    dims = []
    for col in columns_info:
        if not col.is_categorical:
            continue
        if col.unique_count <= 1 or col.unique_count > 30:
            continue
        lowered = normalize_column_name(col.name)
        score = 100
        score += semantic_score(lowered, domain_keywords) * 20
        score += semantic_score(lowered, ["region", "segment", "category", "product", "department", "channel", "status", "type", "group"]) * 20
        score += max(0, 20 - col.unique_count)
        score -= min(col.null_count, 50)
        dims.append((score, col.name))
    dims.sort(reverse=True)
    return [name for _, name in dims[:limit]]


def infer_default_aggregation(domain: str, metric_name: Optional[str]) -> str:
    if not metric_name:
        return "count"
    lowered = normalize_column_name(metric_name)
    if any(token in lowered for token in ["price", "rate", "ratio", "margin", "score", "age", "duration"]):
        return "mean"
    if domain in ["finance", "sales", "marketing", "inventory", "operations"]:
        return "sum"
    return "mean"


def compute_period_change(df: pd.DataFrame, time_col: Optional[str], metric_col: str, aggregation: str) -> Optional[float]:
    if not time_col or time_col not in df.columns or metric_col not in df.columns:
        return None
    period_df = df[[time_col, metric_col]].dropna().copy()
    if period_df.empty or not pd.api.types.is_datetime64_any_dtype(period_df[time_col]):
        return None
    period_df = period_df.sort_values(time_col)
    unique_dates = period_df[time_col].nunique()
    freq = "D"
    if unique_dates > 24:
        freq = "W"
    if unique_dates > 90:
        freq = "M"
    grouped = period_df.set_index(time_col).resample(freq)[metric_col]
    if aggregation == "mean":
        series = grouped.mean()
    elif aggregation == "count":
        series = grouped.count()
    else:
        series = grouped.sum()
    series = series.dropna()
    if len(series) < 2:
        return None
    previous = float(series.iloc[-2])
    current = float(series.iloc[-1])
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def find_strongest_correlation_pair(df: pd.DataFrame, metric_cols: List[str]) -> Optional[tuple[str, str]]:
    if len(metric_cols) < 2:
        return None
    correlations = calculate_correlations(df, metric_cols[:6])
    if not correlations:
        return None
    top = correlations[0]
    if abs(top["correlation"]) < 0.65:
        return None
    return top["column1"], top["column2"]


def build_chart_data(
    df: pd.DataFrame,
    chart_type: str,
    x_col: Optional[str],
    y_col: Optional[str],
    aggregation: str = "none",
    limit: int = 12,
) -> List[Dict[str, Any]]:
    if chart_type == "pie":
        if not x_col or x_col not in df.columns:
            return []
        value_counts = df[x_col].astype(str).value_counts().head(limit)
        return [{"name": str(k), "value": int(v)} for k, v in value_counts.items()]

    if chart_type == "bar":
        if not x_col or x_col not in df.columns:
            return []
        if y_col is None and pd.api.types.is_numeric_dtype(df[x_col]):
            series = df[x_col].dropna()
            if len(series) < 5:
                return []
            hist, bin_edges = np.histogram(series, bins=min(limit, 10))
            return [
                {"bin": f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}", "count": int(hist[i])}
                for i in range(len(hist))
            ]
        if y_col and y_col in df.columns:
            grouped_df = df[[x_col, y_col]].dropna()
            if grouped_df.empty:
                return []
            if aggregation == "mean":
                grouped = grouped_df.groupby(x_col)[y_col].mean()
            elif aggregation == "count":
                grouped = grouped_df.groupby(x_col)[y_col].count()
            else:
                grouped = grouped_df.groupby(x_col)[y_col].sum()
            grouped = grouped.sort_values(ascending=False).head(limit)
            return [{"category": str(k), "count": float(v)} for k, v in grouped.items()]
        value_counts = df[x_col].astype(str).value_counts().head(limit)
        return [{"category": str(k), "count": int(v)} for k, v in value_counts.items()]

    if chart_type == "line":
        if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
            return []
        line_df = df[[x_col, y_col]].dropna().copy()
        if line_df.empty:
            return []
        is_time = pd.api.types.is_datetime64_any_dtype(line_df[x_col])
        if is_time:
            line_df = line_df.sort_values(x_col)
            if aggregation in ["sum", "mean", "count"]:
                freq = "D"
                unique_dates = line_df[x_col].nunique()
                if unique_dates > 24:
                    freq = "W"
                if unique_dates > 90:
                    freq = "M"
                grouped = line_df.set_index(x_col).resample(freq)[y_col]
                if aggregation == "mean":
                    line_df = grouped.mean().reset_index()
                elif aggregation == "count":
                    line_df = grouped.count().reset_index()
                else:
                    line_df = grouped.sum().reset_index()
            if len(line_df) > 100:
                step = max(1, len(line_df) // 100)
                line_df = line_df.iloc[::step]
            return [
                {"date": row[x_col].isoformat() if pd.notna(row[x_col]) else None, "value": float(row[y_col]) if pd.notna(row[y_col]) else None}
                for _, row in line_df.iterrows()
            ]

        if aggregation in ["sum", "mean", "count"]:
            grouped = line_df.groupby(x_col)[y_col]
            if aggregation == "mean":
                line_df = grouped.mean().reset_index()
            elif aggregation == "count":
                line_df = grouped.count().reset_index()
            else:
                line_df = grouped.sum().reset_index()
        line_df = line_df.head(100)
        return [{"date": str(row[x_col]), "value": float(row[y_col]) if pd.notna(row[y_col]) else None} for _, row in line_df.iterrows()]

    if chart_type == "scatter":
        if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
            return []
        scatter_df = df[[x_col, y_col]].dropna()
        if len(scatter_df) > 400:
            scatter_df = scatter_df.sample(400, random_state=42)
        return [{"x": float(row[x_col]), "y": float(row[y_col])} for _, row in scatter_df.iterrows()]

    return []


def build_domain_insights(df: pd.DataFrame, columns_info: List[ColumnInfo], domain: str) -> List[str]:
    insights = []
    completeness = (1 - df.isnull().sum().sum() / max(len(df) * max(len(df.columns), 1), 1)) * 100
    time_col = choose_time_column(columns_info)
    metric_cols = choose_metric_columns(columns_info, domain, limit=3)
    dim_cols = choose_dimension_columns(columns_info, domain, limit=2)

    insights.append(f"Le dataset contient {len(df):,} lignes, {len(df.columns)} colonnes et une completude de {completeness:.1f}%.".replace(",", " "))
    if metric_cols:
        insights.append(f"La mesure principale a suivre est '{metric_cols[0]}', car elle combine bonne couverture et forte valeur analytique.")
    if dim_cols:
        top_value = df[dim_cols[0]].astype(str).value_counts().head(1)
        if not top_value.empty:
            insights.append(f"La segmentation la plus utile passe par '{dim_cols[0]}', avec '{top_value.index[0]}' comme categorie dominante.")
    if time_col and metric_cols:
        variation = compute_period_change(df, time_col, metric_cols[0], infer_default_aggregation(domain, metric_cols[0]))
        if variation is not None:
            direction = "hausse" if variation >= 0 else "baisse"
            insights.append(f"La derniere periode montre une {direction} de {abs(variation):.1f}% sur '{metric_cols[0]}'.")

    domain_messages = {
        "finance": "Le tableau de bord doit mettre l'accent sur les evolutions temporelles, la rentabilite et les concentrations par segment.",
        "customers": "Le tableau de bord doit faire ressortir la segmentation client, la valeur, la retention et les signaux de risque.",
        "marketing": "Le tableau de bord doit comparer les canaux, les campagnes, les volumes et l'efficacite des actions.",
        "sales": "Le tableau de bord doit prioriser performance commerciale, mix produit, regions et dynamique des ventes.",
        "hr": "Le tableau de bord doit privilegier effectifs, remuneration, attrition et performance par equipe ou departement.",
        "operations": "Le tableau de bord doit suivre capacite, volumes, qualite de service et points de friction du processus.",
        "inventory": "Le tableau de bord doit suivre stocks, rotation, categories dominantes et risques de concentration.",
    }
    if domain in domain_messages:
        insights.append(domain_messages[domain])

    return insights[:4]


def build_fallback_ai_analysis(df: pd.DataFrame, columns_info: List[ColumnInfo], filename: str) -> Dict[str, Any]:
    """Heuristic analysis used when the external AI service is unavailable."""
    domain = infer_dataset_domain(columns_info, filename)
    metric_cols = choose_metric_columns(columns_info, domain, limit=4)
    time_col = choose_time_column(columns_info)
    dimension_cols = choose_dimension_columns(columns_info, domain, limit=3)
    primary_metric = metric_cols[0] if metric_cols else None
    secondary_metric = metric_cols[1] if len(metric_cols) > 1 else None
    aggregation = infer_default_aggregation(domain, primary_metric)

    kpis = [{"name": "Total Records", "column": None, "aggregation": "count", "formula": "Nombre total de lignes", "format": "integer"}]
    if primary_metric:
        main_format = infer_format_from_name(primary_metric)
        main_agg = infer_default_aggregation(domain, primary_metric)
        metric_prefix = "Total" if main_agg == "sum" else "Moyenne"
        kpis.append({"name": f"{metric_prefix} {primary_metric}", "column": primary_metric, "aggregation": main_agg, "formula": "Indicateur principal", "format": main_format})
        kpis.append({"name": f"Mediane {primary_metric}", "column": primary_metric, "aggregation": "median", "formula": "Valeur centrale", "format": main_format})
    if secondary_metric:
        secondary_agg = infer_default_aggregation(domain, secondary_metric)
        kpis.append({"name": f"{'Total' if secondary_agg == 'sum' else 'Moyenne'} {secondary_metric}", "column": secondary_metric, "aggregation": secondary_agg, "formula": "Indicateur secondaire", "format": infer_format_from_name(secondary_metric)})
    if dimension_cols:
        kpis.append({"name": f"Segments {dimension_cols[0]}", "column": dimension_cols[0], "aggregation": "count", "formula": "Nombre de categories distinctes", "format": "integer"})
    if time_col and primary_metric:
        kpis.append({"name": f"Evolution recente {primary_metric}", "column": primary_metric, "aggregation": aggregation, "formula": f"Variation recente sur la colonne temporelle {time_col}", "format": "percentage"})
    kpis.append({"name": "Data Completeness", "column": None, "aggregation": "custom", "formula": "Part des cellules non nulles", "format": "percentage"})

    charts = []
    if time_col and primary_metric:
        charts.append({
            "type": "line",
            "title": f"Evolution de {primary_metric}",
            "x_column": time_col,
            "y_column": primary_metric,
            "aggregation": aggregation,
            "group_by": None,
            "description": "Montre la tendance principale dans le temps",
        })
    if time_col and secondary_metric:
        charts.append({
            "type": "line",
            "title": f"Evolution de {secondary_metric}",
            "x_column": time_col,
            "y_column": secondary_metric,
            "aggregation": infer_default_aggregation(domain, secondary_metric),
            "group_by": None,
            "description": "Permet de comparer une deuxieme mesure cle dans le temps",
        })
    if dimension_cols and primary_metric:
        charts.append({
            "type": "bar",
            "title": f"{primary_metric} par {dimension_cols[0]}",
            "x_column": dimension_cols[0],
            "y_column": primary_metric,
            "aggregation": aggregation,
            "group_by": dimension_cols[0],
            "description": "Classe les segments les plus contributifs",
        })
    if len(dimension_cols) > 1 and primary_metric:
        charts.append({
            "type": "bar",
            "title": f"{primary_metric} par {dimension_cols[1]}",
            "x_column": dimension_cols[1],
            "y_column": primary_metric,
            "aggregation": aggregation,
            "group_by": dimension_cols[1],
            "description": "Fournit une seconde lecture de la performance par segment",
        })
    elif dimension_cols and not primary_metric:
        charts.append({
            "type": "bar",
            "title": f"Repartition de {dimension_cols[0]}",
            "x_column": dimension_cols[0],
            "y_column": None,
            "aggregation": "count",
            "group_by": None,
            "description": "Montre la distribution de la variable la plus structurante",
        })
    small_dim = next((col for col in dimension_cols if df[col].nunique() <= 6), None)
    if small_dim:
        charts.append({
            "type": "pie",
            "title": f"Poids de {small_dim}",
            "x_column": small_dim,
            "y_column": None,
            "aggregation": "count",
            "group_by": None,
            "description": "Visualise le poids relatif des principales categories",
        })
    if primary_metric and primary_metric in df.columns:
        charts.append({
            "type": "bar",
            "title": f"Distribution de {primary_metric}",
            "x_column": primary_metric,
            "y_column": None,
            "aggregation": "count",
            "group_by": None,
            "description": "Montre la dispersion de la mesure principale",
        })
    corr_pair = find_strongest_correlation_pair(df, metric_cols)
    if corr_pair:
        charts.append({
            "type": "scatter",
            "title": f"{corr_pair[0]} vs {corr_pair[1]}",
            "x_column": corr_pair[0],
            "y_column": corr_pair[1],
            "aggregation": "none",
            "group_by": None,
            "description": "Met en evidence la relation la plus forte entre deux mesures",
        })

    deduped_charts = []
    seen = set()
    for chart in charts:
        key = (chart["type"], chart["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped_charts.append(chart)

    return {
        "domain": domain,
        "context": f"Dataset classe comme '{domain}' a partir des colonnes et du nom de fichier.",
        "kpis": kpis[:8],
        "charts": deduped_charts[:6],
        "insights": build_domain_insights(df, columns_info, domain),
        "recommended_filters": dimension_cols[:3],
    }


def generate_auto_charts(df: pd.DataFrame, columns_info: List[ColumnInfo]) -> List[ChartConfig]:
    """Generate automatic chart configurations based on data."""
    analysis = build_fallback_ai_analysis(df, columns_info, "dataset")
    return generate_smart_charts(df, columns_info, analysis)


def generate_kpis(df: pd.DataFrame, columns_info: List[ColumnInfo]) -> List[KPIMetric]:
    """Generate KPI metrics from dataframe."""
    analysis = build_fallback_ai_analysis(df, columns_info, "dataset")
    return generate_smart_kpis(df, columns_info, analysis)


async def call_gemini(prompt: str, system: str = "") -> Optional[str]:
    """Call Google Gemini and return raw text response, or None on failure."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or google_genai is None:
        return None
    try:
        client = google_genai.Client(api_key=api_key)
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None


def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def analyze_dataset_with_ai(df: pd.DataFrame, columns_info: List[ColumnInfo], filename: str) -> Dict[str, Any]:
    """Use AI (Gemini) to analyze the dataset and determine the best dashboard configuration."""

    columns_summary = []
    for col in columns_info[:25]:
        col_summary = {
            "name": col.name,
            "type": "numeric" if col.is_numeric else ("temporal" if col.is_temporal else "categorical"),
            "unique_values": col.unique_count,
            "null_pct": round(col.null_count / len(df) * 100, 1) if len(df) > 0 else 0,
        }
        if col.stats:
            if col.is_numeric:
                col_summary["min"] = col.stats.get("min")
                col_summary["max"] = col.stats.get("max")
                col_summary["mean"] = col.stats.get("mean")
            elif col.stats.get("top_values"):
                col_summary["top_values"] = list(col.stats["top_values"].keys())[:5]
        columns_summary.append(col_summary)

    sample_data = df.head(5).to_dict(orient="records")
    for row in sample_data:
        for key, val in row.items():
            if pd.isna(val):
                row[key] = None
            elif isinstance(val, (np.integer, np.floating)):
                row[key] = float(val)
            elif isinstance(val, (pd.Timestamp, datetime)):
                row[key] = str(val)

    prompt = f"""Tu es un expert en Business Intelligence. Analyse ce dataset et génère une configuration de dashboard complète.

DATASET: {filename} | {len(df)} lignes | {len(df.columns)} colonnes

COLONNES:
{json.dumps(columns_summary, indent=2, default=str)}

ÉCHANTILLON (5 lignes):
{json.dumps(sample_data, indent=2, default=str)}

RÈGLES IMPORTANTES:
- Utilise UNIQUEMENT les noms de colonnes EXACTS tels qu'ils apparaissent dans COLONNES ci-dessus.
- Génère EXACTEMENT 6 à 8 charts distincts et pertinents. C'est obligatoire.
- Varie les types: line, bar, scatter, pie (pas tous le même type).
- Pour pie: uniquement si la colonne a moins de 10 valeurs uniques.
- Pour scatter: uniquement entre deux colonnes numériques.
- Pour line: uniquement si une colonne temporelle existe.
- Génère 6 à 8 KPIs pertinents.

Réponds UNIQUEMENT en JSON valide:
{{
    "domain": "finance|sales|hr|marketing|customers|operations|inventory|healthcare|other",
    "context": "Description courte",
    "kpis": [
        {{"name": "Nom KPI", "column": "col_exacte_ou_null", "aggregation": "sum|mean|count|max|min|median|custom", "formula": "desc si custom", "format": "currency|number|percentage|integer"}}
    ],
    "charts": [
        {{"type": "line|bar|scatter|pie", "title": "Titre", "x_column": "col_exacte", "y_column": "col_exacte_ou_null", "aggregation": "sum|mean|count|none", "group_by": null, "description": "Raison"}}
    ],
    "insights": ["Observation 1", "Observation 2", "Observation 3"],
    "recommended_filters": ["col1"]
}}"""

    system = "Tu es un expert data analyst et Business Intelligence. Tu réponds toujours en JSON valide uniquement, sans texte autour."

    raw = await call_gemini(prompt, system)
    if raw:
        result = _parse_json_response(raw)
        if result:
            logger.info(f"Gemini analysis OK: domain={result.get('domain')}, charts={len(result.get('charts', []))}")
            return result

    # Fallback: emergentintegrations / Claude
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if api_key and LlmChat and UserMessage:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"analysis-{uuid.uuid4()}",
                system_message=system,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            response = await chat.send_message(UserMessage(text=prompt))
            result = _parse_json_response(response)
            if result:
                logger.info(f"Claude analysis OK: domain={result.get('domain')}")
                return result
    except Exception as e:
        logger.error(f"Claude fallback error: {e}")

    logger.warning("All AI providers failed, using heuristic analysis")
    return None


def generate_smart_kpis(df: pd.DataFrame, columns_info: List[ColumnInfo], ai_analysis: Dict[str, Any]) -> List[KPIMetric]:
    """Generate intelligent KPIs based on AI analysis."""
    kpis = []
    
    if not ai_analysis or "kpis" not in ai_analysis:
        return generate_kpis(df, columns_info)
    
    for kpi_config in ai_analysis.get("kpis", [])[:8]:
        try:
            name = kpi_config.get("name", "KPI")
            column = kpi_config.get("column")
            aggregation = kpi_config.get("aggregation", "sum")
            fmt = kpi_config.get("format", "number")
            
            value = None
            
            if column and column in df.columns:
                series = df[column].dropna()
                if len(series) > 0:
                    if aggregation == "sum":
                        value = float(series.sum())
                    elif aggregation == "mean":
                        value = float(series.mean())
                    elif aggregation == "count":
                        value = int(series.nunique()) if "unique" in name.lower() else int(series.count())
                    elif aggregation == "max":
                        value = float(series.max())
                    elif aggregation == "min":
                        value = float(series.min())
                    elif aggregation == "median":
                        value = float(series.median())
            elif aggregation == "custom" and "evolution recente" in name.lower() and column:
                time_col = choose_time_column(columns_info)
                change = compute_period_change(df, time_col, column, infer_default_aggregation(ai_analysis.get("domain", "other"), column))
                value = change
            elif aggregation == "custom" and "completeness" in name.lower():
                value = float(round((1 - df.isnull().sum().sum() / max(len(df) * max(len(df.columns), 1), 1)) * 100, 1))
            elif aggregation == "count":
                value = int(len(df))
            
            if value is not None:
                kpis.append(KPIMetric(
                    name=name,
                    value=value,
                    format=fmt,
                    change=value if aggregation == "custom" and "evolution recente" in name.lower() else None
                ))
        except Exception as e:
            logger.error(f"Error generating KPI {kpi_config}: {e}")
            continue
    
    # Add completeness if not enough KPIs
    if len(kpis) < 4:
        completeness = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        kpis.append(KPIMetric(
            name="Data Completeness",
            value=float(round(completeness, 1)),
            format="percentage"
        ))
    
    return kpis


def generate_smart_charts(df: pd.DataFrame, columns_info: List[ColumnInfo], ai_analysis: Dict[str, Any]) -> List[ChartConfig]:
    """Generate intelligent charts based on AI analysis."""
    charts = []
    
    if not ai_analysis or "charts" not in ai_analysis:
        return generate_auto_charts(df, columns_info)
    
    for chart_config in ai_analysis.get("charts", [])[:8]:
        try:
            chart_type = chart_config.get("type", "bar")
            title = chart_config.get("title", "Chart")
            x_col = chart_config.get("x_column")
            y_col = chart_config.get("y_column")
            aggregation = chart_config.get("aggregation", "none")
            group_by = chart_config.get("group_by")
            description = chart_config.get("description")
            
            # Validate columns exist
            if x_col and x_col not in df.columns:
                continue
            if y_col and y_col not in df.columns:
                continue
            if chart_type == "area":
                chart_type = "line"
            chart_data = build_chart_data(
                df=df,
                chart_type=chart_type,
                x_col=group_by if chart_type == "bar" and group_by else x_col,
                y_col=y_col,
                aggregation=aggregation,
                limit=15 if chart_type == "bar" else 12,
            )
            
            if chart_data:
                config = {"xAxisType": "time"} if chart_type == "line" and x_col and x_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[x_col]) else {}
                if chart_type == "bar" and chart_data and "bin" in chart_data[0]:
                    config["isHistogram"] = True
                if description:
                    config["description"] = description
                charts.append(ChartConfig(
                    chart_type=chart_type,
                    title=title,
                    x_column=x_col,
                    y_column=y_col,
                    data=chart_data,
                    config=config
                ))
                
        except Exception as e:
            logger.error(f"Error generating chart {chart_config}: {e}")
            continue
    
    # Supplement with heuristic charts to always reach at least 6
    if len(charts) < 4:
        logger.info(f"Only {len(charts)} AI charts generated, supplementing with heuristic charts")
        heuristic = _build_heuristic_charts(df, columns_info)
        existing_titles = {c.title for c in charts}
        for h in heuristic:
            if len(charts) >= 6:
                break
            if h.title not in existing_titles:
                charts.append(h)
                existing_titles.add(h.title)

    return charts[:6]


def _build_heuristic_charts(df: pd.DataFrame, columns_info: List[ColumnInfo]) -> List[ChartConfig]:
    """Build up to 8 heuristic charts from whatever columns are available."""
    numeric_cols = [c.name for c in columns_info if c.is_numeric and c.name in df.columns]
    temporal_cols = [c.name for c in columns_info if c.is_temporal and c.name in df.columns]
    cat_cols = [c.name for c in columns_info if c.is_categorical and c.name in df.columns]

    charts: List[ChartConfig] = []

    def add(chart_type, title, x, y, agg="none", limit=15):
        data = build_chart_data(df, chart_type, x, y, agg, limit)
        if not data:
            return
        config = {}
        if chart_type == "line" and x and x in df.columns and pd.api.types.is_datetime64_any_dtype(df[x]):
            config = {"xAxisType": "time"}
        charts.append(ChartConfig(chart_type=chart_type, title=title, x_column=x, y_column=y, data=data, config=config))

    primary_num = numeric_cols[0] if numeric_cols else None
    second_num  = numeric_cols[1] if len(numeric_cols) > 1 else None

    for t in temporal_cols[:1]:
        if primary_num:
            add("line", f"Evolution de {primary_num}", t, primary_num, "sum")
        if second_num:
            add("line", f"Evolution de {second_num}", t, second_num, "mean")

    if cat_cols:
        if primary_num:
            add("bar", f"{primary_num} par {cat_cols[0]}", cat_cols[0], primary_num, "sum", 12)
        else:
            add("bar", f"Repartition de {cat_cols[0]}", cat_cols[0], None, "count", 12)

    if len(cat_cols) > 1 and primary_num:
        add("bar", f"{primary_num} par {cat_cols[1]}", cat_cols[1], primary_num, "sum", 12)

    small_cat = next((cat for cat in cat_cols if df[cat].nunique() <= 6), None)
    if small_cat:
        add("pie", f"Poids de {small_cat}", small_cat, None, "count")

    if primary_num:
        add("bar", f"Distribution de {primary_num}", primary_num, None, "count", 10)

    pair = find_strongest_correlation_pair(df, numeric_cols[:5])
    if pair:
        add("scatter", f"{pair[0]} vs {pair[1]}", pair[0], pair[1])

    return charts[:6]


# In-memory storage for datasets (for demo purposes)
datasets_storage: Dict[str, pd.DataFrame] = {}
datasets_info: Dict[str, DatasetInfo] = {}
ai_analysis_cache: Dict[str, Dict[str, Any]] = {}
workbooks_info: Dict[str, WorkbookInfo] = {}


def detect_cross_sheet_relations(sheets: List[SheetInfo]) -> List[Dict[str, Any]]:
    """Detect relationships between sheets based on common and semantically similar column names."""
    relations = []
    key_keywords = ["id", "code", "key", "ref", "num", "no", "number", "sku", "uuid"]

    for i, sheet1 in enumerate(sheets):
        for sheet2 in sheets[i + 1:]:
            cols1 = {normalize_column_name(c.name): c.name for c in sheet1.columns}
            cols2 = {normalize_column_name(c.name): c.name for c in sheet2.columns}

            common_normalized = set(cols1.keys()) & set(cols2.keys())
            if not common_normalized:
                continue

            common_originals = [cols1[n] for n in common_normalized]
            join_keys = [cols1[n] for n in common_normalized if any(kw in n for kw in key_keywords)]

            confidence = min(1.0, 0.3 + len(join_keys) * 0.3 + min(len(common_normalized), 5) * 0.06)

            relations.append({
                "sheet1": sheet1.sheet_name,
                "sheet2": sheet2.sheet_name,
                "sheet1_id": sheet1.dataset_id,
                "sheet2_id": sheet2.dataset_id,
                "common_columns": common_originals,
                "join_keys": join_keys,
                "relation_type": "join" if join_keys else "reference",
                "confidence": round(confidence, 2),
            })

    return sorted(relations, key=lambda x: x["confidence"], reverse=True)


async def analyze_cross_sheet_with_ai(
    sheets: List[SheetInfo],
    relations: List[Dict[str, Any]],
    filename: str,
) -> Dict[str, Any]:
    """Generate AI-powered cross-sheet analysis description."""
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key or LlmChat is None or UserMessage is None:
            return None

        sheets_summary = []
        for s in sheets:
            col_types = {"numeric": 0, "temporal": 0, "categorical": 0}
            for c in s.columns:
                if c.is_numeric:
                    col_types["numeric"] += 1
                elif c.is_temporal:
                    col_types["temporal"] += 1
                else:
                    col_types["categorical"] += 1
            sheets_summary.append({
                "name": s.sheet_name,
                "rows": s.row_count,
                "columns": [c.name for c in s.columns[:15]],
                "col_types": col_types,
            })

        relations_summary = [
            {
                "between": f"{r['sheet1']} ↔ {r['sheet2']}",
                "via": r["common_columns"][:5],
                "join_keys": r["join_keys"],
                "type": r["relation_type"],
            }
            for r in relations[:5]
        ]

        prompt = f"""Tu es un expert en BI (Business Intelligence) et data modelling. Analyse ce workbook Excel multi-feuilles.

FICHIER: {filename}
FEUILLES:
{json.dumps(sheets_summary, indent=2, ensure_ascii=False)}

RELATIONS DÉTECTÉES ENTRE FEUILLES:
{json.dumps(relations_summary, indent=2, ensure_ascii=False)}

Génère une analyse croisée intelligente. Réponds UNIQUEMENT en JSON valide:
{{
    "domain": "finance|sales|hr|marketing|customers|operations|inventory|healthcare|other",
    "context": "Description du workbook et de ce que représentent les données croisées",
    "cross_insights": [
        "Insight 1 sur les relations entre feuilles",
        "Insight 2 sur ce qu'on peut déduire en croisant les données"
    ],
    "kpis": [
        {{"name": "KPI", "column": "colonne ou null", "aggregation": "sum|mean|count|max|min|median|custom", "formula": "desc si custom", "format": "currency|number|percentage|integer"}}
    ],
    "charts": [
        {{"type": "line|bar|scatter|pie", "title": "Titre", "x_column": "col_x", "y_column": "col_y ou null", "aggregation": "sum|mean|count|none", "group_by": null, "description": "Pourquoi"}}
    ],
    "insights": ["Observation 1", "Observation 2"],
    "recommended_filters": ["col1"]
}}"""

        system = "Tu es un expert data analyst et BI. Réponds toujours en JSON valide uniquement."
        raw = await call_gemini(prompt, system)
        if raw:
            result = _parse_json_response(raw)
            if result:
                logger.info("Gemini cross-sheet analysis OK")
                return result

        # Fallback to emergentintegrations
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if api_key and LlmChat and UserMessage:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"cross-{uuid.uuid4()}",
                system_message=system,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            response = await chat.send_message(UserMessage(text=prompt))
            result = _parse_json_response(response)
            if result:
                return result

        return None
    except Exception as e:
        logger.error(f"Cross-sheet AI analysis error: {e}")
        return None


# ==============================================================================
# API Routes
# ==============================================================================

@api_router.get("/")
async def root():
    return {"message": "Analytics Engine API v1.0"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


def _build_dataset_from_df(df: pd.DataFrame, filename: str, file_size: int) -> tuple:
    """Build DatasetInfo and store a single DataFrame. Returns (dataset_id, DatasetInfo)."""
    df = preprocess_dataframe(df)
    columns_info = []
    for col in df.columns:
        series = df[col]
        type_info = detect_column_type(series)
        sample_values = series.dropna().head(5).tolist()
        sample_values = [str(v) if not isinstance(v, (int, float, bool)) else v for v in sample_values]
        columns_info.append(ColumnInfo(
            name=col,
            dtype=type_info["dtype"],
            unique_count=int(series.nunique()),
            null_count=int(series.isnull().sum()),
            sample_values=sample_values,
            is_numeric=type_info["is_numeric"],
            is_temporal=type_info["is_temporal"],
            is_categorical=type_info["is_categorical"],
            stats=calculate_column_stats(series, type_info["is_numeric"])
        ))
    dataset_id = str(uuid.uuid4())
    dataset_info = DatasetInfo(
        id=dataset_id,
        filename=filename,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns_info,
        file_size=file_size,
    )
    datasets_storage[dataset_id] = df
    datasets_info[dataset_id] = dataset_info
    return dataset_id, dataset_info


@api_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and analyze a data file (CSV, Excel, JSON). Multi-sheet Excel returns a workbook."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = file.filename.lower().split('.')[-1]
    if ext not in ['csv', 'xlsx', 'xls', 'json']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV, Excel, or JSON.")

    try:
        content = await file.read()
        file_size = len(content)

        # ── Multi-sheet Excel path ────────────────────────────────────────────
        if ext in ['xlsx', 'xls']:
            xl = pd.ExcelFile(io.BytesIO(content))
            sheet_names = xl.sheet_names

            if len(sheet_names) > 1:
                logger.info(f"Multi-sheet Excel detected: {len(sheet_names)} sheets in {file.filename}")
                workbook_id = str(uuid.uuid4())
                sheet_infos: List[SheetInfo] = []

                for sheet_name in sheet_names:
                    try:
                        raw_df = xl.parse(sheet_name)
                        if raw_df.empty or len(raw_df.columns) == 0:
                            logger.warning(f"Skipping empty sheet: {sheet_name}")
                            continue
                        dataset_id, dataset_info = _build_dataset_from_df(raw_df, f"{file.filename} [{sheet_name}]", file_size)
                        # Persist metadata
                        doc = dataset_info.model_dump()
                        doc["workbook_id"] = workbook_id
                        doc["sheet_name"] = sheet_name
                        await db.datasets.insert_one(doc)

                        sheet_infos.append(SheetInfo(
                            sheet_name=sheet_name,
                            dataset_id=dataset_id,
                            row_count=dataset_info.row_count,
                            column_count=dataset_info.column_count,
                            columns=dataset_info.columns,
                        ))
                    except Exception as e:
                        logger.error(f"Error parsing sheet '{sheet_name}': {e}")
                        continue

                if not sheet_infos:
                    raise HTTPException(status_code=400, detail="All sheets are empty or could not be parsed.")

                relations = detect_cross_sheet_relations(sheet_infos)

                workbook = WorkbookInfo(
                    workbook_id=workbook_id,
                    filename=file.filename,
                    file_size=file_size,
                    sheets=sheet_infos,
                    detected_relations=relations,
                )
                workbooks_info[workbook_id] = workbook

                await db.workbooks.insert_one(workbook.model_dump())
                logger.info(f"Workbook {workbook_id} created: {len(sheet_infos)} sheets, {len(relations)} relations")

                return UploadResponse(
                    is_workbook=True,
                    filename=file.filename,
                    file_size=file_size,
                    workbook_id=workbook_id,
                    sheets=sheet_infos,
                    detected_relations=relations,
                )

            # Single-sheet Excel – fall through to standard path
            df = xl.parse(sheet_names[0])

        # ── Single-file path (CSV, JSON, single-sheet Excel) ─────────────────
        elif ext == 'csv':
            df = pd.read_csv(io.BytesIO(content))
        elif ext == 'json':
            df = pd.read_json(io.BytesIO(content))

        dataset_id, dataset_info = _build_dataset_from_df(df, file.filename, file_size)

        # Persist metadata in MongoDB
        doc = dataset_info.model_dump()
        await db.datasets.insert_one(doc)

        logger.info(f"Uploaded dataset {dataset_id}: {file.filename} ({dataset_info.row_count} rows, {dataset_info.column_count} cols)")

        return UploadResponse(
            is_workbook=False,
            id=dataset_id,
            filename=file.filename,
            row_count=dataset_info.row_count,
            column_count=dataset_info.column_count,
            columns=dataset_info.columns,
            created_at=dataset_info.created_at,
            file_size=file_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@api_router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets():
    """List all uploaded datasets."""
    datasets = await db.datasets.find({}, {"_id": 0}).to_list(100)
    return datasets


@api_router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    """Get dataset metadata."""
    dataset = await db.datasets.find_one({"id": dataset_id}, {"_id": 0})
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@api_router.get("/datasets/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500)
):
    """Get paginated data preview."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found in memory. Please re-upload.")
    
    df = datasets_storage[dataset_id]
    start = (page - 1) * page_size
    end = start + page_size
    
    df_page = df.iloc[start:end]
    
    # Convert to list of dicts, handling special types
    data = []
    for _, row in df_page.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (np.integer, np.floating)):
                row_dict[col] = float(val)
            elif isinstance(val, (pd.Timestamp, datetime)):
                row_dict[col] = val.isoformat()
            else:
                row_dict[col] = str(val)
        data.append(row_dict)
    
    return {
        "data": data,
        "total_rows": len(df),
        "page": page,
        "page_size": page_size,
        "total_pages": (len(df) + page_size - 1) // page_size
    }


@api_router.get("/datasets/{dataset_id}/dashboard", response_model=DashboardResponse)
async def generate_dashboard(dataset_id: str):
    """Generate automatic dashboard for dataset using AI analysis."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found in memory. Please re-upload.")
    
    df = datasets_storage[dataset_id]
    info = datasets_info[dataset_id]
    
    # Check if we have cached AI analysis
    ai_analysis = ai_analysis_cache.get(dataset_id)
    
    # Run AI analysis if not cached
    if ai_analysis is None:
        logger.info(f"Running AI analysis for dataset {dataset_id}")
        ai_analysis = await analyze_dataset_with_ai(df, info.columns, info.filename)
        if not ai_analysis:
            ai_analysis = build_fallback_ai_analysis(df, info.columns, info.filename)
        ai_analysis_cache[dataset_id] = ai_analysis
    
    # Generate smart KPIs and charts based on AI analysis
    logger.info(f"Generating smart dashboard for domain: {ai_analysis.get('domain')}")
    kpis = generate_smart_kpis(df, info.columns, ai_analysis)
    charts = generate_smart_charts(df, info.columns, ai_analysis)
    
    # Calculate correlations
    numeric_cols = [c.name for c in info.columns if c.is_numeric]
    correlations = calculate_correlations(df, numeric_cols)
    
    # Detect anomalies
    anomalies = detect_anomalies(df, numeric_cols)
    
    # Add AI insights to anomalies if available
    if ai_analysis and ai_analysis.get("insights"):
        for insight in ai_analysis.get("insights", [])[:3]:
            anomalies.append({
                "column": "AI Insight",
                "description": insight,
                "count": 0,
                "percentage": 0
            })
    
    return DashboardResponse(
        dataset_id=dataset_id,
        kpis=kpis,
        charts=charts,
        correlations=correlations,
        anomalies=anomalies
    )


# ==============================================================================
# Workbook (multi-sheet) endpoints
# ==============================================================================

@api_router.get("/workbooks/{workbook_id}")
async def get_workbook(workbook_id: str):
    """Get workbook metadata including all sheets and detected relations."""
    if workbook_id not in workbooks_info:
        wb = await db.workbooks.find_one({"workbook_id": workbook_id}, {"_id": 0})
        if not wb:
            raise HTTPException(status_code=404, detail="Workbook not found")
        return wb
    return workbooks_info[workbook_id].model_dump()


@api_router.get("/workbooks/{workbook_id}/cross-dashboard", response_model=DashboardResponse)
async def generate_cross_dashboard(workbook_id: str):
    """Generate a combined dashboard by intelligently joining/merging all sheets in a workbook."""
    if workbook_id not in workbooks_info:
        raise HTTPException(status_code=404, detail="Workbook not found in memory. Please re-upload.")

    workbook = workbooks_info[workbook_id]
    relations = workbook.detected_relations

    # Collect loaded sheets
    available = {s.sheet_name: s for s in workbook.sheets if s.dataset_id in datasets_storage}
    if not available:
        raise HTTPException(status_code=404, detail="Sheet data not found in memory. Please re-upload.")

    all_sheet_names = list(available.keys())

    # ── Strategy 1: join on shared key ──────────────────────────────────────
    merged_df = None
    merge_description = ""

    for rel in relations:
        if rel.get("join_keys") and rel["sheet1"] in available and rel["sheet2"] in available:
            join_key = rel["join_keys"][0]
            df1 = datasets_storage[available[rel["sheet1"]].dataset_id]
            df2 = datasets_storage[available[rel["sheet2"]].dataset_id]

            # Match key column names case-insensitively
            key1 = next((c for c in df1.columns if normalize_column_name(c) == normalize_column_name(join_key)), None)
            key2 = next((c for c in df2.columns if normalize_column_name(c) == normalize_column_name(join_key)), None)

            if key1 and key2:
                try:
                    suffix = f"_{rel['sheet2']}"
                    merged_df = pd.merge(df1, df2, left_on=key1, right_on=key2, how="left", suffixes=("", suffix))
                    # Also incorporate remaining sheets via concat
                    extra_dfs = [datasets_storage[available[n].dataset_id] for n in all_sheet_names
                                 if n not in (rel["sheet1"], rel["sheet2"]) and available[n].dataset_id in datasets_storage]
                    if extra_dfs:
                        merged_df = pd.concat([merged_df] + extra_dfs, ignore_index=True)
                    merge_description = f"Joined: '{rel['sheet1']}' + '{rel['sheet2']}' on '{join_key}'"
                    if extra_dfs:
                        merge_description += f" + {len(extra_dfs)} additional sheet(s)"
                    logger.info(f"Cross-sheet join successful: {merge_description}")
                    break
                except Exception as e:
                    logger.warning(f"Join failed for {rel}: {e}")
                    merged_df = None

    # ── Strategy 2: concatenate all sheets ───────────────────────────────────
    if merged_df is None:
        all_dfs = [datasets_storage[s.dataset_id] for s in available.values()]
        merged_df = pd.concat(all_dfs, ignore_index=True)
        merge_description = f"Concatenated {len(all_dfs)} sheets: {', '.join(all_sheet_names)}"
        logger.info(f"Cross-sheet concat: {merge_description}")

    # Build columns info for the merged dataframe
    merged_cols_info = []
    for col in merged_df.columns:
        series = merged_df[col]
        type_info = detect_column_type(series)
        sample_values = series.dropna().head(5).tolist()
        sample_values = [str(v) if not isinstance(v, (int, float, bool)) else v for v in sample_values]
        merged_cols_info.append(ColumnInfo(
            name=col,
            dtype=type_info["dtype"],
            unique_count=int(series.nunique()),
            null_count=int(series.isnull().sum()),
            sample_values=sample_values,
            is_numeric=type_info["is_numeric"],
            is_temporal=type_info["is_temporal"],
            is_categorical=type_info["is_categorical"],
            stats=calculate_column_stats(series, type_info["is_numeric"]),
        ))

    # Run AI analysis – try cross-sheet specific first, fall back to standard
    cross_analysis = await analyze_cross_sheet_with_ai(workbook.sheets, relations, workbook.filename)
    if not cross_analysis:
        cross_analysis = await analyze_dataset_with_ai(merged_df, merged_cols_info, workbook.filename)
    if not cross_analysis:
        cross_analysis = build_fallback_ai_analysis(merged_df, merged_cols_info, workbook.filename)

    # Prepend merge/relation insights
    if "insights" not in cross_analysis:
        cross_analysis["insights"] = []
    cross_analysis["insights"].insert(0, f"Analyse croisée – {merge_description}")
    for rel in relations[:2]:
        cross_analysis["insights"].append(
            f"Relation: '{rel['sheet1']}' ↔ '{rel['sheet2']}' via {', '.join(rel.get('common_columns', [])[:3])}"
        )

    kpis = generate_smart_kpis(merged_df, merged_cols_info, cross_analysis)
    charts = generate_smart_charts(merged_df, merged_cols_info, cross_analysis)

    numeric_cols = [c.name for c in merged_cols_info if c.is_numeric]
    correlations = calculate_correlations(merged_df, numeric_cols)
    anomalies = detect_anomalies(merged_df, numeric_cols)

    for insight in cross_analysis.get("insights", [])[:4]:
        anomalies.append({"column": "AI Insight", "description": insight, "count": 0, "percentage": 0})

    if cross_analysis.get("cross_insights"):
        for ci in cross_analysis["cross_insights"][:2]:
            anomalies.append({"column": "AI Insight", "description": ci, "count": 0, "percentage": 0})

    # Cache merged dataset so downstream endpoints work
    merged_id = f"cross_{workbook_id}"
    datasets_storage[merged_id] = merged_df

    return DashboardResponse(
        dataset_id=merged_id,
        kpis=kpis,
        charts=charts,
        correlations=correlations,
        anomalies=anomalies,
    )


@api_router.post("/datasets/{dataset_id}/aggregate")
async def aggregate_data(dataset_id: str, request: AggregationRequest):
    """Perform aggregation on dataset."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = datasets_storage[dataset_id].copy()
    
    # Apply filters
    for f in request.filters:
        if f.operator == "eq":
            df = df[df[f.column] == f.value]
        elif f.operator == "ne":
            df = df[df[f.column] != f.value]
        elif f.operator == "gt":
            df = df[df[f.column] > f.value]
        elif f.operator == "lt":
            df = df[df[f.column] < f.value]
        elif f.operator == "gte":
            df = df[df[f.column] >= f.value]
        elif f.operator == "lte":
            df = df[df[f.column] <= f.value]
        elif f.operator == "contains":
            df = df[df[f.column].astype(str).str.contains(str(f.value), case=False)]
    
    # Perform aggregation
    agg_dict = {}
    for col, agg_func in request.aggregations.items():
        if agg_func in ['sum', 'mean', 'count', 'min', 'max', 'std', 'median']:
            agg_dict[col] = agg_func
    
    if request.group_by and agg_dict:
        result = df.groupby(request.group_by).agg(agg_dict).reset_index()
    else:
        result = df
    
    # Convert to JSON-safe format
    data = []
    for _, row in result.head(1000).iterrows():
        row_dict = {}
        for col in result.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (np.integer, np.floating)):
                row_dict[col] = float(val)
            else:
                row_dict[col] = str(val)
        data.append(row_dict)
    
    return {"data": data, "row_count": len(result)}


@api_router.post("/datasets/{dataset_id}/filter")
async def filter_data(
    dataset_id: str,
    filters: List[FilterRequest],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500)
):
    """Filter dataset with multiple conditions."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = datasets_storage[dataset_id].copy()
    
    for f in filters:
        if f.column not in df.columns:
            continue
            
        if f.operator == "eq":
            df = df[df[f.column] == f.value]
        elif f.operator == "ne":
            df = df[df[f.column] != f.value]
        elif f.operator == "gt":
            df = df[df[f.column] > float(f.value)]
        elif f.operator == "lt":
            df = df[df[f.column] < float(f.value)]
        elif f.operator == "gte":
            df = df[df[f.column] >= float(f.value)]
        elif f.operator == "lte":
            df = df[df[f.column] <= float(f.value)]
        elif f.operator == "contains":
            df = df[df[f.column].astype(str).str.contains(str(f.value), case=False, na=False)]
        elif f.operator == "in":
            if isinstance(f.value, list):
                df = df[df[f.column].isin(f.value)]
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    df_page = df.iloc[start:end]
    
    data = []
    for _, row in df_page.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (np.integer, np.floating)):
                row_dict[col] = float(val)
            elif isinstance(val, (pd.Timestamp, datetime)):
                row_dict[col] = val.isoformat()
            else:
                row_dict[col] = str(val)
        data.append(row_dict)
    
    return {
        "data": data,
        "total_rows": len(df),
        "page": page,
        "page_size": page_size,
        "filtered_count": len(df)
    }


@api_router.post("/datasets/{dataset_id}/ai-insights", response_model=AIInsightResponse)
async def get_ai_insights(dataset_id: str, request: AIInsightRequest):
    """Get AI-generated insights using Claude."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = datasets_storage[dataset_id]
    info = datasets_info[dataset_id]
    
    # Prepare data summary for AI
    numeric_cols = [c for c in info.columns if c.is_numeric]
    categorical_cols = [c for c in info.columns if c.is_categorical]
    
    data_summary = f"""
Dataset: {info.filename}
Rows: {info.row_count}
Columns: {info.column_count}

Column Summary:
"""
    for col in info.columns[:15]:  # Limit columns
        data_summary += f"- {col.name}: {col.dtype}, {col.unique_count} unique values, {col.null_count} nulls\n"
        if col.stats:
            if col.is_numeric:
                data_summary += f"  Stats: mean={col.stats.get('mean')}, min={col.stats.get('min')}, max={col.stats.get('max')}\n"
            elif col.stats.get('top_values'):
                top_vals = list(col.stats['top_values'].items())[:3]
                data_summary += f"  Top values: {top_vals}\n"
    
    # Calculate correlations for summary
    if len(numeric_cols) >= 2:
        corr_summary = calculate_correlations(df, [c.name for c in numeric_cols])
        if corr_summary:
            data_summary += "\nStrong Correlations:\n"
            for corr in corr_summary[:5]:
                data_summary += f"- {corr['column1']} & {corr['column2']}: {corr['correlation']}\n"
    
    # Add anomalies summary
    anomalies = detect_anomalies(df, [c.name for c in numeric_cols])
    if anomalies:
        data_summary += "\nDetected Anomalies:\n"
        for anom in anomalies[:5]:
            data_summary += f"- {anom['description']}\n"
    
    # Call AI for insights (Gemini first, then Claude fallback)
    user_question = request.question or "Analyse ce dataset et fournis des insights clés, recommandations et anomalies."

    ai_prompt = f"""{data_summary}

Question: {user_question}

Réponds UNIQUEMENT en JSON valide avec ces clés exactes:
{{
    "insights": ["observation 1", "observation 2", "observation 3", "observation 4"],
    "recommendations": ["recommandation 1", "recommandation 2", "recommandation 3"],
    "anomalies": ["anomalie ou problème qualité 1", "anomalie 2"],
    "key_findings": ["finding 1", "finding 2", "finding 3"]
}}"""

    ai_system = "Tu es un senior data analyst. Tu réponds uniquement en JSON valide, sans texte autour."

    ai_result = None
    try:
        raw = await call_gemini(ai_prompt, ai_system)
        if raw:
            ai_result = _parse_json_response(raw)

        if not ai_result:
            api_key = os.environ.get("EMERGENT_LLM_KEY")
            if api_key and LlmChat and UserMessage:
                chat = LlmChat(
                    api_key=api_key,
                    session_id=f"insights-{dataset_id}",
                    system_message=ai_system,
                ).with_model("anthropic", "claude-sonnet-4-5-20250929")
                response = await chat.send_message(UserMessage(text=ai_prompt))
                ai_result = _parse_json_response(response)

        if ai_result:
            return AIInsightResponse(
                insights=ai_result.get("insights", []),
                recommendations=ai_result.get("recommendations", []),
                anomalies=ai_result.get("anomalies", []),
                key_findings=ai_result.get("key_findings", []),
            )
    except Exception as e:
        logger.error(f"AI insights error: {e}")

    # Statistical fallback
    return AIInsightResponse(
        insights=[
            f"Le dataset contient {info.row_count} enregistrements avec {info.column_count} variables.",
            f"Complétude des données : {round((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 1)}%",
            f"{len(numeric_cols)} colonnes numériques et {len(categorical_cols)} colonnes catégorielles détectées.",
        ],
        recommendations=[
            "Vérifier les colonnes avec un fort taux de valeurs manquantes.",
            "Explorer les corrélations entre colonnes numériques.",
            "Segmenter l'analyse par les colonnes catégorielles clés.",
        ],
        anomalies=[a["description"] for a in anomalies[:3]],
        key_findings=[f"Analyse statistique complétée sur {info.row_count} enregistrements."],
    )


@api_router.post("/datasets/{dataset_id}/report")
async def generate_report(dataset_id: str, request: ReportRequest):
    """Generate an analytical report."""
    if dataset_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = datasets_storage[dataset_id]
    info = datasets_info[dataset_id]
    
    # Generate KPIs
    kpis = generate_kpis(df, info.columns)
    
    # Get correlations
    numeric_cols = [c.name for c in info.columns if c.is_numeric]
    correlations = calculate_correlations(df, numeric_cols)
    
    # Detect anomalies
    anomalies = detect_anomalies(df, numeric_cols)
    
    # Build report
    report = {
        "title": f"Data Analysis Report: {info.filename}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type": request.report_type,
        "summary": {
            "total_records": info.row_count,
            "total_columns": info.column_count,
            "data_completeness": round((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 1),
            "numeric_columns": len(numeric_cols),
            "file_size_kb": round(info.file_size / 1024, 2)
        },
        "kpis": [kpi.model_dump() for kpi in kpis],
        "correlations": correlations,
        "anomalies": anomalies,
        "columns_overview": [
            {
                "name": c.name,
                "type": "Numeric" if c.is_numeric else ("Temporal" if c.is_temporal else "Categorical"),
                "unique_values": c.unique_count,
                "missing_values": c.null_count,
                "missing_percentage": round(c.null_count / info.row_count * 100, 1)
            }
            for c in info.columns
        ]
    }
    
    return report


@api_router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset."""
    if dataset_id in datasets_storage:
        del datasets_storage[dataset_id]
    if dataset_id in datasets_info:
        del datasets_info[dataset_id]
    
    await db.datasets.delete_one({"id": dataset_id})
    
    return {"message": "Dataset deleted successfully"}


@api_router.post("/datasets/merge", response_model=DatasetResponse)
async def merge_datasets(request: MergeRequest):
    """Merge two datasets together."""
    if request.dataset1_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="First dataset not found in memory")
    if request.dataset2_id not in datasets_storage:
        raise HTTPException(status_code=404, detail="Second dataset not found in memory")
    
    df1 = datasets_storage[request.dataset1_id]
    df2 = datasets_storage[request.dataset2_id]
    info1 = datasets_info[request.dataset1_id]
    info2 = datasets_info[request.dataset2_id]
    
    try:
        if request.merge_type == "concat":
            # Concatenate datasets (append rows)
            merged_df = pd.concat([df1, df2], ignore_index=True)
        elif request.merge_type == "left_join":
            if not request.join_key:
                raise HTTPException(status_code=400, detail="Join key required for left join")
            if request.join_key not in df1.columns or request.join_key not in df2.columns:
                raise HTTPException(status_code=400, detail=f"Join key '{request.join_key}' not found in both datasets")
            merged_df = pd.merge(df1, df2, on=request.join_key, how="left", suffixes=("", "_merged"))
        elif request.merge_type == "inner_join":
            if not request.join_key:
                raise HTTPException(status_code=400, detail="Join key required for inner join")
            if request.join_key not in df1.columns or request.join_key not in df2.columns:
                raise HTTPException(status_code=400, detail=f"Join key '{request.join_key}' not found in both datasets")
            merged_df = pd.merge(df1, df2, on=request.join_key, how="inner", suffixes=("", "_merged"))
        else:
            raise HTTPException(status_code=400, detail="Invalid merge type")
        
        # Analyze merged dataset
        columns_info = []
        for col in merged_df.columns:
            series = merged_df[col]
            type_info = detect_column_type(series)
            
            sample_values = series.dropna().head(5).tolist()
            sample_values = [str(v) if not isinstance(v, (int, float, bool)) else v for v in sample_values]
            
            col_info = ColumnInfo(
                name=col,
                dtype=type_info["dtype"],
                unique_count=int(series.nunique()),
                null_count=int(series.isnull().sum()),
                sample_values=sample_values,
                is_numeric=type_info["is_numeric"],
                is_temporal=type_info["is_temporal"],
                is_categorical=type_info["is_categorical"],
                stats=calculate_column_stats(series, type_info["is_numeric"])
            )
            columns_info.append(col_info)
        
        # Create new dataset
        dataset_id = str(uuid.uuid4())
        merged_filename = f"merged_{info1.filename.split('.')[0]}_{info2.filename.split('.')[0]}.csv"
        
        # Estimate file size
        file_size = merged_df.memory_usage(deep=True).sum()
        
        dataset_info = DatasetInfo(
            id=dataset_id,
            filename=merged_filename,
            row_count=len(merged_df),
            column_count=len(merged_df.columns),
            columns=columns_info,
            file_size=int(file_size)
        )
        
        # Store in memory
        datasets_storage[dataset_id] = merged_df
        datasets_info[dataset_id] = dataset_info
        
        # Store metadata in MongoDB
        doc = dataset_info.model_dump()
        await db.datasets.insert_one(doc)
        
        logger.info(f"Merged datasets: {info1.filename} + {info2.filename} -> {merged_filename} ({len(merged_df)} rows)")
        
        return DatasetResponse(
            id=dataset_id,
            filename=merged_filename,
            row_count=len(merged_df),
            column_count=len(merged_df.columns),
            columns=columns_info,
            created_at=dataset_info.created_at,
            file_size=int(file_size)
        )
        
    except Exception as e:
        logger.error(f"Merge error: {e}")
        raise HTTPException(status_code=500, detail=f"Error merging datasets: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
