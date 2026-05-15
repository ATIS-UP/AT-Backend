"""Modelos SQLAlchemy"""
from app.models.user import User, Permiso, RolEnum
from app.models.estudiante import Estudiante, Materia, Inscripcion
from app.models.alerta import Alerta, Actividad
from app.models.sistema import Parametrizacion
from app.models.caso_especial import RegistroCasoEspecial, HistorialRegistro
from app.models.actividad_institucional import ActividadInstitucional
from app.models.anexo_actividad import AnexoActividad