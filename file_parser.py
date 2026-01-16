import pandas as pd
from docx import Document
import re
from datetime import datetime
import pdfplumber
try:
    import easyocr
    import numpy as np
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

EXCEL_COL_MAP = {
    "Sesión": "numero_sesion",
    "Cedis": "cedis", 
    "Estado": "estado_geo",
    "Descripción del hallazgo": "hallazgo",
    "Riesgo": "riesgo",
    "Fecha de Detección": "fecha_hallazgo",
    "Fecha Compromiso": "fecha_compromiso",
    "Responsable": "responsable",
    "Estatus": "estatus",
    "Acciones Realizadas": "acciones_inmediatas"
}

def parse_excel_matrix(file):
    try:
        df = pd.read_excel(file)
        df = df.rename(columns=EXCEL_COL_MAP)
        for date_col in ["fecha_hallazgo", "fecha_compromiso"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
        if "estatus" not in df.columns: df["estatus"] = "Abierto"
        return df
    except Exception as e:
        return None, str(e)

def parse_pdf_acta(file):
    """
    Intenta 3 estrategias:
    1. Parseo Nativo de Tablas (pdfplumber)
    2. OCR para escaneos (easyocr)
    3. Fallback: Extracción de Texto Crudo (si todo falla)
    """
    findings = []
    HEADER_KEYWORDS = ["HALLAZGO", "ACCIONES", "RESPONSABLE", "FECHA", "OBSERVACION", "DETECCION"]

    # 1. INTENTO NATIVO (Texto Selectable)
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables: continue
                
                for table in tables:
                    if not table or not table[0]: continue
                    # Safe header extraction handling None
                    headers = [str(x).upper().strip() if x else "" for x in table[0]]
                    
                    # Check if relevant table
                    if any(k in h for h in headers for k in HEADER_KEYWORDS):
                        idx_map = {"hallazgo":-1, "acciones_inmediatas":-1, "responsable":-1, "fecha_hallazgo":-1, "fecha_compromiso":-1}
                        
                        for i, h in enumerate(headers):
                            if "HALLAZGO" in h or "OBSERVAC" in h: idx_map["hallazgo"] = i
                            if "ACCIONES" in h or "CORRECTIVA" in h: idx_map["acciones_inmediatas"] = i
                            if "RESPONSABLE" in h: idx_map["responsable"] = i
                            if "DETECCI" in h or "FECHA" in h: idx_map["fecha_hallazgo"] = i
                            if "COMPROMISO" in h: idx_map["fecha_compromiso"] = i
                        
                        for row in table[1:]:
                            if len(row) != len(headers): continue
                            
                            idx_h = idx_map["hallazgo"]
                            if idx_h >= 0:
                                h_txt = str(row[idx_h]).strip() if row[idx_h] else ""
                                if h_txt:
                                    findings.append({
                                        "hallazgo": h_txt,
                                        "acciones_inmediatas": str(row[idx_map["acciones_inmediatas"]]) if idx_map["acciones_inmediatas"] >= 0 and row[idx_map["acciones_inmediatas"]] else "",
                                        "responsable": str(row[idx_map["responsable"]]) if idx_map["responsable"] >= 0 and row[idx_map["responsable"]] else "",
                                        "fecha_hallazgo": row[idx_map["fecha_hallazgo"]] if idx_map["fecha_hallazgo"] >= 0 else None,
                                        "fecha_compromiso": row[idx_map["fecha_compromiso"]] if idx_map["fecha_compromiso"] >= 0 else None,
                                        "estatus": "Abierto",
                                        "tipo_hallazgo": "Documental"
                                    })
        
        if findings: return findings

    except Exception as e:
        print(f"Error parseo nativo: {e}")

    # 2. INTENTO OCR (Si falló el nativo y existe librería)
    if HAS_OCR:
        print("Iniciando OCR...")
        try:
            reader = easyocr.Reader(['es'], gpu=False) 
            
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    im = page.to_image(resolution=300).original
                    im_np = np.array(im)
                    result = reader.readtext(im_np) # [(bbox, text, conf), ...]
                    
                    header_y = -1
                    cols_x = {"hallazgo": 0}
                    
                    # Detectar Header
                    for (bbox, text, prob) in result:
                        text_up = text.upper()
                        if "HALLAZGO" in text_up or "OBSERVACION" in text_up:
                            header_y = bbox[0][1]
                            cols_x["hallazgo"] = bbox[0][0]
                            break 
                    
                    if header_y > 0:
                        # Filtrar contenido
                        content_items = [x for x in result if x[0][0][1] > header_y + 20]
                        content_items.sort(key=lambda x: x[0][0][1])
                        
                        for (bbox, text, prob) in content_items:
                            # Alinear mas o menos con la columna Hallazgo detected
                            if abs(bbox[0][0] - cols_x["hallazgo"]) < 200: 
                                # Heurística muy laxa: cualquier texto en esa zona X
                                findings.append({
                                    "hallazgo": text,
                                    "acciones_inmediatas": "",
                                    "responsable": "",
                                    "estatus": "Abierto (OCR)",
                                    "tipo_hallazgo": "Documental"
                                })
        except Exception as e:
             print(f"Error OCR: {e}")

    if findings: return findings

    # 3. ULTRO RECURSO: FALLBACK TEXTO CRUDO
    # Si todo falla, extrae todo texto posible para que el usuario no se vaya con las manos vacías
    try:
        print("Iniciando Fallback Texto Crudo...")
        with pdfplumber.open(file) as pdf:
            all_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text: all_text += text + "\n"
        
        # Intentar dividir por lineas y asumir que lineas largas son hallazgos
        lines = all_text.split('\n')
        for line in lines:
            if len(line.strip()) > 10: # Ignorar cositas cortas
                findings.append({
                    "hallazgo": line.strip(),
                    "acciones_inmediatas": "Revisar texto extraído manual",
                    "responsable": "",
                    "estatus": "Abierto (Texto Crudo)",
                    "tipo_hallazgo": "Documental"
                })
    except Exception:
        pass

    return findings
