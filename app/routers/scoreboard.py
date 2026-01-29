from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemas.scoreboard import ScoreboardEntryDTO
from app.schemas.auth import AuthToken
from app.middleware import get_current_user
from app.services.interpreter_client import interpreter
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["scoreboard"])

@router.get("/global", response_model=List[ScoreboardEntryDTO])
async def get_global_scoreboard(user: AuthToken = Depends(get_current_user)):
    """
    Retorna o placar global de todos os usuários do sistema.
    Acessível por qualquer usuário logado.
    """
    logger.info(f"Usuário {user.username} acessando o scoreboard global.")
    return await interpreter.get_global_scoreboard()

@router.get("/{comp_id}", response_model=List[ScoreboardEntryDTO])
async def get_competition_scoreboard(comp_id: str, user: AuthToken = Depends(get_current_user)):
    """
    Retorna o placar de uma competição específica ordenado por pontuação.
    
    Regras de Negócio:
    1. Administradores podem visualizar qualquer placar.
    2. Alunos só podem visualizar o placar de competições onde estão inscritos.
    """
    
    if user.role != "admin":
        participants = await interpreter.get_competition_participants(comp_id)
        is_registered = any(p["id"] == user.id for p in participants)
        
        if not is_registered:
            logger.warning(f"Usuário {user.username} tentou acessar o scoreboard da competição {comp_id} sem estar inscrito.")
            raise HTTPException(status_code=403, detail="Você precisa estar inscrito nesta competição para ver o placar.")

    logger.info(f"Usuário {user.username} acessando scoreboard da competição {comp_id}")
    
    return await interpreter.get_scoreboard(comp_id)