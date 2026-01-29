from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timezone

from app.schemas.exercise import ExerciseCreateDTO, ExerciseReadDTO, ExerciseUpdateDTO, ExerciseAdminReadDTO
from app.schemas.solve import SolveSubmitDTO, SolveResponseDTO, SolveReadDTO
from app.schemas.tag import TagReadDTO, TagCreateDTO
from app.schemas.competition import CompetitionReadDTO
from app.schemas.container import ContainerInternalDTO, ContainerRequestDTO
from app.schemas.auth import AuthToken
from app.middleware import get_current_user
from app.services.interpreter_client import interpreter
from app.services.orchester_client import orchester
from app.logger import get_logger


logger = get_logger(__name__)
router = APIRouter(tags=["exercises"])

@router.get("/", response_model=List[ExerciseReadDTO])
async def list_all_exercises(user: AuthToken = Depends(get_current_user)):
    """Apenas admins podem ver a biblioteca global de exercícios."""
    return await interpreter.list_all_exercises()

@router.get("/{ex_id}/connection")
async def get_connection_info(ex_id: str, comp_id: str, user: AuthToken = Depends(get_current_user)):
    """
    Retorna os dados de conexão de um container.
    """
    container = await interpreter.get_container_by_exercise(ex_id)
    if not container or not container.get("is_active"):
        raise HTTPException(status_code=404, detail="A infraestrutura deste desafio não está ativa")
    
    return {
        "connection": container["connection"],
        "port": container["port"]
    }

@router.get("/my-solves", response_model=List[SolveReadDTO])
async def get_my_solves(user: AuthToken = Depends(get_current_user)):
    """Retorna o histórico de resoluções do utilizador logado."""
    return await interpreter.get_user_solves(user.id)

@router.post("/submit", response_model=SolveResponseDTO)
async def submit_flag(payload: SolveSubmitDTO, user: AuthToken = Depends(get_current_user)):
    """
    Ponto central de validação de submissão.
    Validações:
    1. A competição existe e está ativa.
    2. O exercício faz parte da competição.
    """
    
    # 1. Validação da Competição e Janela Temporal
    comp = await interpreter.get_competition(payload.competitions_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competição não encontrada")
    
    now = datetime.now(timezone.utc)

    def ensure_utc(dt_val):
        if isinstance(dt_val, str):
            dt_val = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        
        return dt_val.astimezone(timezone.utc)

    try:
        start_date = ensure_utc(comp["start_date"])
        end_date = ensure_utc(comp["end_date"])
    except Exception as e:
        logger.error(f"Erro ao processar datas da competição {payload.competitions_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar datas da competição")

    if now < start_date:
        raise HTTPException(status_code=400, detail="A competição ainda não começou")
    if now > end_date:
        raise HTTPException(status_code=400, detail="A competição já terminou")

    # 3. Verificar se o exercício pertence à competição
    comp_exercises = await interpreter.get_competition_exercises(payload.competitions_id)
    if not any(ex["id"] == payload.exercises_id for ex in comp_exercises):
        raise HTTPException(status_code=400, detail="Este exercício não pertence a esta competição")

    # 4. Enviar para o Interpreter para validação final da flag e persistência
    logger.info(f"Submissão validada pelo Backend. Enviando para o Interpreter: User {user.username}")
    return await interpreter.submit_flag(payload, user.id)

@router.post("/", response_model=ExerciseReadDTO, status_code=201)
async def create_exercise(payload: ExerciseCreateDTO, user: AuthToken = Depends(get_current_user)):
    """Cria um exercício (Apenas Admin)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.create_exercise(payload)

@router.get("/{ex_id}/admin", response_model=ExerciseAdminReadDTO)
async def get_exercise_admin(ex_id: str, user: AuthToken = Depends(get_current_user)):
    """Ver detalhes completos, incluindo a FLAG (Apenas Admin)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    ex = await interpreter.get_exercise(ex_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    return ex

@router.post("/{ex_id}/link-competition/{comp_id}")
async def link_to_competition(ex_id: str, comp_id: str, user: AuthToken = Depends(get_current_user)):
    """Vincula o exercício a uma competição específica."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.link_exercise_to_competition(ex_id, comp_id)

@router.post("/{ex_id}/tags/{tag_id}")
async def link_to_tag(ex_id: str, tag_id: str, user: AuthToken = Depends(get_current_user)):
    """Vincula uma etiqueta ao exercício."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.link_exercise_to_tag(ex_id, tag_id)

@router.patch("/{ex_id}", response_model=ExerciseReadDTO)
async def update_exercise(ex_id: str, payload: ExerciseUpdateDTO, user: AuthToken = Depends(get_current_user)):
    """Atualiza dados do exercício."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.update_exercise(ex_id, payload)

@router.delete("/{ex_id}", status_code=204)
async def delete_exercise(ex_id: str, user: AuthToken = Depends(get_current_user)):
    """Remove o exercício do sistema."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.delete_exercise(ex_id)

@router.get("/{ex_id}/competitions", response_model=List[CompetitionReadDTO])
async def get_exercise_competitions(ex_id: str, user: AuthToken = Depends(get_current_user)):
    """Retorna as competições vinculadas a um exercício (Para o estado do Modal)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.get_exercise_competitions(ex_id)

@router.delete("/{ex_id}/competition/{comp_id}")
async def unlink_from_competition(ex_id: str, comp_id: str, user: AuthToken = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.unlink_exercise_from_competition(ex_id, comp_id)

@router.delete("/{ex_id}/tags/{tag_id}")
async def unlink_from_tag(ex_id: str, tag_id: str, user: AuthToken = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return await interpreter.unlink_exercise_from_tag(ex_id, tag_id)

@router.post("/{ex_id}/deploy")
async def deploy_exercise_infrastructure(ex_id: str, payload: ContainerRequestDTO, user: AuthToken = Depends(get_current_user)):
    """
    Aciona o Orchester para subir o container do exercício e regista-o no Interpreter.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    # 1. Busca os dados do exercício e da competição
    exercise = await interpreter.get_exercise(ex_id)
    
    if not exercise or not exercise.get("docker_image"):
        raise HTTPException(status_code=400, detail="Exercício sem imagem Docker configurada")

    # 2. Prepara o pedido para o Orchester
    orchester_payload = {
        "image_link": exercise["docker_image"],
        "time_alive": payload.time_alive,
        "exercise_name": exercise["name"],
        "callback_url": "http://backend:8000/containers/callback"
    }

    # 3. Chama o Orchester
    logger.info(f"Solicitando deploy ao Orchester: {exercise['name']}")
    orchestrator_resp = await orchester.start_container(orchester_payload)

    # 4. Regista o container no Interpreter para que fique disponível para os alunos
    container_data = ContainerInternalDTO(
        docker_id=orchestrator_resp["container_id"],
        image_tag=exercise["docker_image"],
        port=orchestrator_resp["host_port"],
        connection=orchestrator_resp["service_url"]
    )

    return await interpreter.register_container(container_data, ex_id)