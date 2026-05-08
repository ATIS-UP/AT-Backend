"""Modelos SQLAlchemy"""
from app.models.user import User, Permiso, RolEnum
from app.models.estudiante import Estudiante, Materia, Inscripcion
from app.models.alerta import Alerta, Actividad
from app.models.sistema import Parametrizacion