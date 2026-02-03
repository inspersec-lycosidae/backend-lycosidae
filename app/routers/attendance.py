from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.attendance import AttendanceReadDTO, AttendanceCreateDTO
from app.schemas.auth import AuthToken
from app.middleware import get_current_user
from app.services.interpreter_client import interpreter
from app.logger import get_logger

# Inicialização do logger para este router
logger = get_logger("attendance_router")
router = APIRouter(tags=["attendance"])

@router.get("/", response_model=List[AttendanceReadDTO])
async def get_all_attendances(user: AuthToken = Depends(get_current_user)):
    """Retorna todas as presenças do sistema (Admin apenas)."""
    if user.role != "admin":
        logger.warning("Tentativa de acesso não autorizado a todas as presenças", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso restrito a administradores."
        )
    
    try:
        attendances = await interpreter.get_all_attendances()
        logger.info("Consulta global de presenças realizada", admin_id=user.id, count=len(attendances))
        return attendances
    except Exception as e:
        logger.error("Erro ao buscar todas as presenças no interpretador", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao processar consulta.")

@router.get("/user/{user_id}", response_model=List[AttendanceReadDTO])
async def get_user_attendance(user_id: str, user: AuthToken = Depends(get_current_user)):
    """Retorna o histórico de um utilizador (Admin ou Próprio)."""
    if user.role != "admin" and user.id != user_id:
        logger.warning("Tentativa de acesso negado a histórico de terceiros", requester_id=user.id, target_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso negado ao histórico de terceiros."
        )
    
    try:
        attendances = await interpreter.get_user_attendance(user_id)
        logger.info("Consulta de presenças por usuário realizada", requester_id=user.id, target_user=user_id, count=len(attendances))
        return attendances
    except Exception as e:
        logger.error("Erro ao buscar presenças do usuário no interpretador", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao recuperar histórico.")

@router.get("/competition/{competition_id}", response_model=List[AttendanceReadDTO])
async def get_competition_attendance(competition_id: str, user: AuthToken = Depends(get_current_user)):
    """Retorna presenças de uma competição específica (Admin apenas)."""
    if user.role != "admin":
        logger.warning("Tentativa de acesso não autorizado a presenças por competição", user_id=user.id, competition_id=competition_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso restrito a administradores."
        )
    
    try:
        attendances = await interpreter.get_competition_attendance(competition_id)
        logger.info("Consulta de presenças por competição realizada", admin_id=user.id, competition_id=competition_id, count=len(attendances))
        return attendances
    except Exception as e:
        logger.error("Erro ao buscar presenças da competição no interpretador", competition_id=competition_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro ao recuperar registros da competição.")

@router.post("/", response_model=AttendanceReadDTO, status_code=201)
async def record_attendance(payload: AttendanceCreateDTO, user: AuthToken = Depends(get_current_user)):
    """
    Regista presença. 
    Verifica se o utilizador já não possui registo para a competição especificada.
    """
    target_user_id = payload.users_id if (user.role == "admin" and payload.users_id) else user.id
    
    logger.info("Iniciando registro de presença", requester_id=user.id, target_user=target_user_id, competition_id=payload.competitions_id)

    try:
        user_history = await interpreter.get_user_attendance(target_user_id)
        if any(att["competitions_id"] == payload.competitions_id for att in user_history):
            logger.warning("Tentativa de registro duplicado de presença", user_id=target_user_id, competition_id=payload.competitions_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Presença já registrada para este usuário nesta competição."
            )
        
        result = await interpreter.record_attendance(payload, target_user_id)
        logger.info("Presença registrada com sucesso", user_id=target_user_id, competition_id=payload.competitions_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Falha ao registrar presença no interpretador", user_id=target_user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao registrar presença.")