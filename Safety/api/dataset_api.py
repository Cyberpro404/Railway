"""
Dataset API endpoints for managing CSV training datasets.
Provides endpoints to list, view, delete datasets and get dataset statistics.
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class DatasetInfo(BaseModel):
    """Dataset information model."""
    filename: str
    filepath: str
    size_bytes: int
    size_formatted: str
    created_at: str
    modified_at: str
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    label_counts: Optional[Dict[str, int]] = None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_dataset_info(filepath: str) -> DatasetInfo:
    """Get detailed information about a dataset file."""
    stat = os.stat(filepath)
    filename = os.path.basename(filepath)
    
    info = DatasetInfo(
        filename=filename,
        filepath=filepath,
        size_bytes=stat.st_size,
        size_formatted=format_file_size(stat.st_size),
        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
    )
    
    # Try to read CSV for additional info
    try:
        df = pd.read_csv(filepath)
        info.row_count = len(df)
        info.columns = list(df.columns)
        
        # Count labels if 'label' column exists
        if 'label' in df.columns:
            info.label_counts = df['label'].value_counts().to_dict()
    except Exception as e:
        logger.warning(f"Could not read CSV {filename}: {e}")
    
    return info


def setup_dataset_routes(app):
    """Setup all dataset-related API routes."""
    
    @app.get("/api/datasets", tags=["Datasets"])
    def api_list_datasets() -> Dict:
        """
        List all CSV dataset files in the data directory.
        Returns metadata about each file including size, row count, and labels.
        """
        try:
            datasets = []
            
            if not os.path.exists(DATA_DIR):
                return {"status": "ok", "data": [], "total": 0}
            
            for filename in os.listdir(DATA_DIR):
                if filename.endswith('.csv'):
                    filepath = os.path.join(DATA_DIR, filename)
                    try:
                        info = get_dataset_info(filepath)
                        datasets.append(info.dict())
                    except Exception as e:
                        logger.error(f"Error reading dataset {filename}: {e}")
                        # Include basic info even if we can't read the file
                        stat = os.stat(filepath)
                        datasets.append({
                            "filename": filename,
                            "filepath": filepath,
                            "size_bytes": stat.st_size,
                            "size_formatted": format_file_size(stat.st_size),
                            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "error": str(e)
                        })
            
            # Sort by modified date, newest first
            datasets.sort(key=lambda x: x.get('modified_at', ''), reverse=True)
            
            return {
                "status": "ok",
                "data": datasets,
                "total": len(datasets)
            }
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")
    
    @app.get("/api/datasets/{filename}", tags=["Datasets"])
    def api_get_dataset(filename: str, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get contents of a specific dataset file with pagination.
        """
        try:
            filepath = os.path.join(DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Dataset {filename} not found")
            
            if not filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail="Only CSV files are supported")
            
            df = pd.read_csv(filepath)
            total_rows = len(df)
            
            # Apply pagination
            df_page = df.iloc[offset:offset + limit]
            
            # Get basic stats
            info = get_dataset_info(filepath)
            
            return {
                "status": "ok",
                "data": {
                    "info": info.dict(),
                    "rows": df_page.to_dict(orient='records'),
                    "total_rows": total_rows,
                    "page_size": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_rows
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading dataset {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to read dataset: {str(e)}")
    
    @app.get("/api/datasets/{filename}/stats", tags=["Datasets"])
    def api_get_dataset_stats(filename: str) -> Dict:
        """
        Get detailed statistics for a dataset file.
        """
        try:
            filepath = os.path.join(DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Dataset {filename} not found")
            
            df = pd.read_csv(filepath)
            
            stats = {
                "filename": filename,
                "total_rows": len(df),
                "columns": list(df.columns),
                "column_types": {col: str(df[col].dtype) for col in df.columns},
                "missing_values": df.isnull().sum().to_dict(),
                "numeric_stats": {}
            }
            
            # Add numeric statistics
            numeric_cols = df.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                stats["numeric_stats"][col] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "median": float(df[col].median())
                }
            
            # Add label distribution if present
            if 'label' in df.columns:
                stats["label_distribution"] = df['label'].value_counts().to_dict()
            
            # Add train_state distribution if present
            if 'train_state' in df.columns:
                stats["train_state_distribution"] = df['train_state'].value_counts().to_dict()
            
            return {"status": "ok", "data": stats}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting stats for {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    @app.delete("/api/datasets/{filename}", tags=["Datasets"])
    def api_delete_dataset(filename: str) -> Dict:
        """
        Delete a dataset file.
        """
        try:
            filepath = os.path.join(DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Dataset {filename} not found")
            
            os.remove(filepath)
            logger.info(f"Deleted dataset: {filename}")
            
            return {
                "status": "ok",
                "message": f"Dataset {filename} deleted successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting dataset {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")
    
    @app.post("/api/datasets/{filename}/import", tags=["Datasets"])
    def api_import_dataset_to_training(filename: str) -> Dict:
        """
        Import a CSV dataset into the training database.
        """
        try:
            from database.training_db import get_training_db
            
            filepath = os.path.join(DATA_DIR, filename)
            
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail=f"Dataset {filename} not found")
            
            df = pd.read_csv(filepath)
            training_db = get_training_db()
            
            imported_count = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    # Build sample data from CSV row
                    sample_data = row.to_dict()
                    label = sample_data.get('label', None)
                    
                    # Insert into training DB
                    training_db.insert_raw_sample(sample_data, label=label)
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
                    if len(errors) > 10:  # Limit error messages
                        errors.append("... more errors truncated")
                        break
            
            return {
                "status": "ok",
                "message": f"Imported {imported_count} samples from {filename}",
                "imported_count": imported_count,
                "total_rows": len(df),
                "errors": errors if errors else None
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error importing dataset {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to import dataset: {str(e)}")
    
    @app.get("/api/ml/realtime-stats", tags=["ML"])
    def api_get_ml_realtime_stats() -> Dict:
        """
        Get real-time ML prediction statistics.
        Returns recent predictions, confidence distribution, and class distribution.
        """
        try:
            from database.operational_db import get_db
            
            db = get_db()
            
            # Get recent readings with ML predictions
            recent = db.get_recent_readings(limit=100)
            
            stats = {
                "total_predictions": 0,
                "class_distribution": {},
                "confidence_distribution": {
                    "high": 0,    # > 80%
                    "medium": 0,  # 50-80%
                    "low": 0      # < 50%
                },
                "avg_confidence": 0,
                "recent_predictions": []
            }
            
            confidences = []
            
            for reading in recent:
                ml_pred = reading.get('ml_prediction')
                if ml_pred and isinstance(ml_pred, dict):
                    stats["total_predictions"] += 1
                    
                    label = ml_pred.get('label', 'unknown')
                    stats["class_distribution"][label] = stats["class_distribution"].get(label, 0) + 1
                    
                    confidence = ml_pred.get('confidence', 0)
                    confidences.append(confidence)
                    
                    if confidence > 0.8:
                        stats["confidence_distribution"]["high"] += 1
                    elif confidence > 0.5:
                        stats["confidence_distribution"]["medium"] += 1
                    else:
                        stats["confidence_distribution"]["low"] += 1
                    
                    # Add to recent predictions (last 10)
                    if len(stats["recent_predictions"]) < 10:
                        stats["recent_predictions"].append({
                            "timestamp": reading.get('timestamp'),
                            "label": label,
                            "confidence": confidence,
                            "z_rms": reading.get('z_rms_mm_s'),
                            "x_rms": reading.get('x_rms_mm_s')
                        })
            
            if confidences:
                stats["avg_confidence"] = sum(confidences) / len(confidences)
            
            return {"status": "ok", "data": stats}
        except Exception as e:
            logger.error(f"Error getting ML realtime stats: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    class CaptureSampleRequest(BaseModel):
        """Request model for capturing a training sample."""
        z_rms: float
        x_rms: float
        temperature: float
        label: str
        notes: Optional[str] = None
        z_peak: Optional[float] = None
        x_peak: Optional[float] = None
        z_band_energy: Optional[Dict] = None
        x_band_energy: Optional[Dict] = None
        timestamp: Optional[str] = None
    
    @app.post("/api/training/capture", tags=["Training"])
    def api_capture_training_sample(request: CaptureSampleRequest) -> Dict:
        """
        Capture a single training sample from the current sensor reading.
        Appends to or creates a CSV file in the data directory.
        """
        try:
            # Generate filename based on today's date
            today = datetime.now().strftime("%Y%m%d")
            filename = f"gandiva_captured_{today}.csv"
            filepath = os.path.join(DATA_DIR, filename)
            
            # Prepare sample data
            timestamp = request.timestamp or datetime.now().isoformat()
            sample = {
                "timestamp": timestamp,
                "z_rms": request.z_rms,
                "x_rms": request.x_rms,
                "temperature": request.temperature,
                "z_peak": request.z_peak or 0,
                "x_peak": request.x_peak or 0,
                "label": request.label,
                "notes": request.notes or ""
            }
            
            # Add band energy data if provided
            if request.z_band_energy:
                for band, value in request.z_band_energy.items():
                    sample[f"z_band_{band}"] = value
            if request.x_band_energy:
                for band, value in request.x_band_energy.items():
                    sample[f"x_band_{band}"] = value
            
            # Append to CSV file
            df_new = pd.DataFrame([sample])
            
            if os.path.exists(filepath):
                # Append to existing file
                df_existing = pd.read_csv(filepath)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                df_combined.to_csv(filepath, index=False)
                row_count = len(df_combined)
            else:
                # Create new file
                df_new.to_csv(filepath, index=False)
                row_count = 1
            
            logger.info(f"Captured training sample: {request.label} -> {filename}")
            
            return {
                "status": "ok",
                "message": f"Sample captured with label '{request.label}'",
                "filename": filename,
                "total_samples": row_count
            }
        except Exception as e:
            logger.error(f"Error capturing training sample: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to capture sample: {str(e)}")
