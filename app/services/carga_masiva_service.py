"""service layer for bulk student upload from csv/xlsx files"""
import csv
import io
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from datetime import datetime

from app.exceptions import ValidationError
from app.models.estudiante import Estudiante, EstadoEstudiante
from app.utils.security import encrypt_data
from app.utils.audit import AuditService

# required columns that must be present in the uploaded file
REQUIRED_COLUMNS = {"nombres", "apellidos", "programa", "semestre", "documento"}

# valid file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

# valid student states
VALID_ESTADOS = {"ACTIVO", "INACTIVO", "GRADUADO", "SUSPENDIDO"}

# valid sede options
SEDES = {"PAMPLONA", "VILLA DEL ROSARIO", "VIRTUAL"}


class CargaMasivaService:
    """handles bulk upload of students from csv/xlsx files"""

    def __init__(self, db: Session):
        self.db = db

    def procesar_archivo(
        self, file: UploadFile, usuario_id: str, ip: str
    ) -> dict:
        """process an uploaded csv/xlsx file and insert/update students.

        returns a summary dict with total_filas, insertadas, actualizadas,
        errores, and detalle_errores.
        """
        extension = self._get_extension(file.filename)
        self._validate_extension(extension)

        rows = self._read_file(file, extension)
        self._validate_columns(rows)

        insertadas = 0
        actualizadas = 0
        errores = 0
        detalle_errores = []

        for idx, row in enumerate(rows, start=2):
            # row index starts at 2 (header is row 1)
            row_errors = self._validate_row(row, idx)
            if row_errors:
                errores += len(row_errors)
                detalle_errores.extend(row_errors)
                continue

            try:
                was_updated = self._upsert_student(row, usuario_id, ip)
                if was_updated:
                    actualizadas += 1
                else:
                    insertadas += 1
            except Exception as e:
                errores += 1
                detalle_errores.append(
                    {"fila": idx, "campo": "general", "error": str(e)}
                )

        # commit all changes at once
        self.db.commit()

        total_filas = len(rows)

        AuditService.log(
            db=self.db,
            usuario_id=usuario_id,
            accion="CARGA_MASIVA",
            entidad="Estudiante",
            detalles={
                "total_filas": total_filas,
                "insertadas": insertadas,
                "actualizadas": actualizadas,
                "errores": errores,
            },
            ip=ip,
            estado="EXITOSO",
            mensaje=f"Carga masiva: {insertadas} insertadas, {actualizadas} actualizadas, {errores} errores",
        )

        return {
            "total_filas": total_filas,
            "insertadas": insertadas,
            "actualizadas": actualizadas,
            "errores": errores,
            "detalle_errores": detalle_errores,
        }

    def _get_extension(self, filename: Optional[str]) -> str:
        """extract lowercase file extension from filename"""
        if not filename:
            return ""
        dot_idx = filename.rfind(".")
        if dot_idx == -1:
            return ""
        return filename[dot_idx:].lower()

    def _validate_extension(self, extension: str) -> None:
        """raise ValidationError if extension is not csv or xlsx"""
        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                message="Formato de archivo no soportado. Use CSV o XLSX.",
                fields={"archivo": f"Extensión '{extension}' no permitida"},
            )

    def _read_file(self, file: UploadFile, extension: str) -> list[dict]:
        """read file content into a list of row dicts"""
        content = file.file.read()

        if extension == ".csv":
            return self._read_csv(content)
        elif extension == ".xlsx":
            return self._read_xlsx(content)
        return []

    def _read_csv(self, content: bytes) -> list[dict]:
        """parse csv content into list of dicts with normalized column names"""
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            # normalize column names to lowercase and strip whitespace
            normalized = {
                k.strip().lower(): v.strip() if v else ""
                for k, v in row.items()
                if k is not None
            }
            rows.append(normalized)
        return rows

    def _read_xlsx(self, content: bytes) -> list[dict]:
        """parse xlsx content into list of dicts with normalized column names"""
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ValidationError(
                message="Soporte XLSX no disponible. Instale openpyxl.",
                fields={"archivo": "openpyxl no instalado"},
            )

        wb = load_workbook(filename=io.BytesIO(content), read_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)
        # first row is the header
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return []

        headers = [
            str(h).strip().lower() if h else "" for h in header_row
        ]

        rows = []
        for row_values in rows_iter:
            row_dict = {}
            for col_idx, value in enumerate(row_values):
                if col_idx < len(headers) and headers[col_idx]:
                    row_dict[headers[col_idx]] = (
                        str(value).strip() if value is not None else ""
                    )
            rows.append(row_dict)

        wb.close()
        return rows

    def _validate_columns(self, rows: list[dict]) -> None:
        """check that required columns exist in the parsed data"""
        if not rows:
            raise ValidationError(
                message="El archivo está vacío o no contiene datos.",
                fields={"archivo": "sin datos"},
            )

        available_columns = set(rows[0].keys())
        missing = REQUIRED_COLUMNS - available_columns
        if missing:
            raise ValidationError(
                message=f"Columnas requeridas faltantes: {', '.join(sorted(missing))}",
                fields={"columnas": list(sorted(missing))},
            )

    def _validate_row(self, row: dict, row_number: int) -> list[dict]:
        """validate a single row, return list of error dicts (empty if valid)"""
        errors = []

        # nombres: required, max 100
        nombres = row.get("nombres", "").strip()
        if not nombres:
            errors.append(
                {"fila": row_number, "campo": "nombres", "error": "campo requerido. Debe contener al menos un carácter. Ej: 'María'"}
            )
        elif len(nombres) > 100:
            errors.append(
                {"fila": row_number, "campo": "nombres", "error": f"máximo 100 caracteres. Recibido: {len(nombres)} chars. Ej: 'María Fernanda'"}
            )

        # apellidos: required, max 100
        apellidos = row.get("apellidos", "").strip()
        if not apellidos:
            errors.append(
                {"fila": row_number, "campo": "apellidos", "error": "campo requerido. Debe contener al menos un carácter. Ej: 'González Pérez'"}
            )
        elif len(apellidos) > 100:
            errors.append(
                {"fila": row_number, "campo": "apellidos", "error": f"máximo 100 caracteres. Recibido: {len(apellidos)} chars. Ej: 'González Pérez'"}
            )

        # programa: required, max 255
        programa = row.get("programa", "").strip()
        if not programa:
            errors.append(
                {"fila": row_number, "campo": "programa", "error": "campo requerido. Ingrese el nombre del programa académico. Ej: 'Ingeniería de Sistemas', 'Trabajo Social'"}
            )
        elif len(programa) > 255:
            errors.append(
                {"fila": row_number, "campo": "programa", "error": f"máximo 255 caracteres. Recibido: {len(programa)} chars"}
            )

        # semestre: required, integer between 1 and 12
        semestre_str = row.get("semestre", "").strip()
        if not semestre_str:
            errors.append(
                {"fila": row_number, "campo": "semestre", "error": "campo requerido. Ingrese un número entre 1 y 12. Ej: '3'"}
            )
        else:
            try:
                semestre_val = int(semestre_str)
                if semestre_val < 1 or semestre_val > 12:
                    errors.append(
                        {
                            "fila": row_number,
                            "campo": "semestre",
                            "error": f"debe ser un entero entre 1 y 12. Recibido: '{semestre_str}'. Ej: '3'",
                        }
                    )
            except ValueError:
                errors.append(
                    {
                        "fila": row_number,
                        "campo": "semestre",
                        "error": f"debe ser un número entero. Recibido: '{semestre_str}'. Ej: '3'",
                    }
                )

        # estado: optional, must be one of valid states
        estado = row.get("estado", "").strip().upper()
        if estado and estado not in VALID_ESTADOS:
            errors.append(
                {
                    "fila": row_number,
                    "campo": "estado",
                    "error": f"debe ser uno de: {', '.join(sorted(VALID_ESTADOS))}. Recibido: '{estado}'. Ej: 'ACTIVO'",
                }
            )

        # documento: required, digits only, 5-15 chars
        documento = row.get("documento", "").strip()
        if not documento:
            errors.append(
                {"fila": row_number, "campo": "documento", "error": "campo requerido. Debe contener entre 5 y 15 dígitos. Ej: '1098765432'"}
            )
        elif not documento.isdigit():
            errors.append(
                {"fila": row_number, "campo": "documento", "error": f"solo se permiten números. Recibido: '{documento}'. Ej: '1098765432'"}
            )
        elif len(documento) < 5:
            errors.append(
                {"fila": row_number, "campo": "documento", "error": f"mínimo 5 dígitos. Recibido: '{documento}' ({len(documento)} chars). Ej: '1098765432'"}
            )
        elif len(documento) > 15:
            errors.append(
                {"fila": row_number, "campo": "documento", "error": f"máximo 15 dígitos. Recibido: '{documento}' ({len(documento)} chars). Ej: '1098765432'"}
            )

        # codigo: optional but must not be empty if provided
        codigo = row.get("codigo", "").strip()
        if codigo and not codigo.strip():
            errors.append(
                {"fila": row_number, "campo": "codigo", "error": "si se incluye la columna 'codigo', el valor no debe estar vacío. Ej: '12345'"}
            )

        # email: optional, validate format if provided
        email = row.get("email", "").strip()
        if email:
            if "@" not in email or "." not in email.split("@")[-1]:
                errors.append(
                    {"fila": row_number, "campo": "email", "error": f"formato de correo inválido. Recibido: '{email}'. Ej: 'maria@unipamplona.edu.co'"}
                )
            elif len(email) > 255:
                errors.append(
                    {"fila": row_number, "campo": "email", "error": f"máximo 255 caracteres. Recibido: {len(email)} chars"}
                )

        # telefono: optional, validate digits only + 7-15 chars if provided
        telefono = row.get("telefono", "").strip()
        if telefono:
            if not telefono.isdigit():
                errors.append(
                    {"fila": row_number, "campo": "telefono", "error": f"solo se permiten números. Recibido: '{telefono}'. Ej: '3001234567'"}
                )
            elif len(telefono) < 7:
                errors.append(
                    {"fila": row_number, "campo": "telefono", "error": f"mínimo 7 dígitos. Recibido: '{telefono}' ({len(telefono)} chars). Ej: '3001234567'"}
                )
            elif len(telefono) > 15:
                errors.append(
                    {"fila": row_number, "campo": "telefono", "error": f"máximo 15 dígitos. Recibido: '{telefono}' ({len(telefono)} chars). Ej: '3001234567'"}
                )

        # sede: optional, must be one of valid sedes if provided
        sede = row.get("sede", "").strip().upper()
        if sede and sede not in SEDES:
            errors.append(
                {"fila": row_number, "campo": "sede", "error": f"debe ser una de: {', '.join(sorted(SEDES))}. Recibido: '{sede}'. Ej: 'PAMPLONA'"}
            )

        # procedencia (ciudad origen): max 100 chars if provided
        procedencia = row.get("procedencia", "").strip()
        if procedencia and len(procedencia) > 100:
            errors.append(
                {"fila": row_number, "campo": "procedencia", "error": f"máximo 100 caracteres. Recibido: {len(procedencia)} chars"}
            )

        return errors

    def _upsert_student(
        self, row: dict, usuario_id: str, ip: str
    ) -> bool:
        """insert or update a student from row data.

        returns True if updated, False if inserted.
        """
        documento = row.get("documento", "").strip()
        codigo = row.get("codigo", documento).strip()
        existing = (
            self.db.query(Estudiante)
            .filter(Estudiante.codigo == codigo)
            .first()
        )

        nombres = row.get("nombres", "").strip()
        apellidos = row.get("apellidos", "").strip()
        programa = row.get("programa", "").strip()
        semestre = int(row.get("semestre", "1").strip())
        estado_str = row.get("estado", "").strip().upper() or "ACTIVO"
        email = row.get("email", "").strip() or None
        telefono = row.get("telefono", "").strip() or None
        sede = (row.get("sede", "").strip().upper()) or None
        estado = EstadoEstudiante(estado_str)

        if email:
            email_hash = hash_data(email)
            duplicado = self.db.query(Estudiante).filter(Estudiante.email_hash == email_hash).first()
            if duplicado and duplicado.codigo != codigo:
                raise ValidationError(f"El email '{email}' ya está registrado para el estudiante {duplicado.codigo}")
        else:
            email_hash = None

        if existing:
            # update existing student
            existing.nombres = encrypt_data(nombres)
            existing.apellidos = encrypt_data(apellidos)
            existing.programa = programa
            existing.semestre = semestre
            existing.estado = estado
            if email:
                existing.email = encrypt_data(email)
                existing.email_hash = email_hash
            if documento:
                existing.documento = encrypt_data(documento)
            if telefono:
                existing.telefono = encrypt_data(telefono)
            existing.sede = sede
            return True
        else:
            # insert new student
            nuevo = Estudiante(
                codigo=codigo,
                nombres=encrypt_data(nombres),
                apellidos=encrypt_data(apellidos),
                programa=programa,
                semestre=semestre,
                estado=estado,
                email=encrypt_data(email) if email else None,
                email_hash=email_hash,
                documento=encrypt_data(documento) if documento else None,
                telefono=encrypt_data(telefono) if telefono else None,
                sede=sede,
            )
            self.db.add(nuevo)
            return False
