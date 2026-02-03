import httpx
import os
from typing import List, Optional, Any, Dict
from fastapi import HTTPException, status

INTERPRETER_URL = os.getenv("INTERPRETER_URL", "http://interpreter:8000")

class InterpreterClient:
    def __init__(self):
        self.base_url = INTERPRETER_URL
        self.timeout = httpx.Timeout(20.0, connect=5.0)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            try:
                response = await client.request(method, endpoint, **kwargs)
                if response.status_code == 404: return None
                if response.status_code == 204: return None
                if 400 <= response.status_code < 500:
                    detail = response.json().get("detail", "Erro na requisição ao Interpreter")
                    raise HTTPException(status_code=response.status_code, detail=detail)
                if response.status_code >= 500:
                    raise HTTPException(status_code=502, detail="Erro interno no Interpreter.")
                return response.json()
            except httpx.RequestError as exc:
                raise HTTPException(status_code=503, detail=f"Falha de conexão: {exc}")

    def _dump(self, data: Any):
        """Helper para serializar Pydantic models para JSON (com suporte a datetime)."""
        if hasattr(data, "model_dump"):
            return data.model_dump(mode='json', exclude_unset=True)
        return data

    # --- 1. AUTH & USERS ---
    async def list_users(self) -> List[Dict]:
        return await self._request("GET", "/auth/users")

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        return await self._request("GET", f"/auth/profile/{user_id}")

    async def get_user_internal(self, email: str) -> Optional[Dict]:
        return await self._request("GET", f"/auth/user/{email}")

    async def register_user(self, user_data: Any) -> Dict:
        return await self._request("POST", "/auth/register", json=self._dump(user_data))

    async def update_user(self, user_id: str, update_data: Any) -> Dict:
        return await self._request("PUT", f"/auth/profile/{user_id}", json=self._dump(update_data))

    async def delete_user(self, user_id: str) -> Dict:
        return await self._request("DELETE", f"/auth/profile/{user_id}")

    # --- 2. COMPETITIONS ---
    async def list_competitions(self) -> List[Dict]:
        return await self._request("GET", "/competitions/")

    async def get_competition(self, comp_id: str) -> Optional[Dict]:
        return await self._request("GET", f"/competitions/{comp_id}")

    async def get_competition_participants(self, comp_id: str) -> List[Dict]:
        return await self._request("GET", f"/competitions/{comp_id}/participants")

    async def get_competition_exercises(self, comp_id: str) -> List[Dict]:
        return await self._request("GET", f"/competitions/{comp_id}/exercises")

    async def create_competition(self, comp_data: Any) -> Dict:
        return await self._request("POST", "/competitions/", json=self._dump(comp_data))

    async def join_competition(self, invite_code: Any, user_id: str) -> Dict:
        return await self._request("POST", f"/competitions/join", json=self._dump(invite_code), params={"user_id": user_id})

    async def update_competition(self, comp_id: str, update_data: Any) -> Dict:
        return await self._request("PATCH", f"/competitions/{comp_id}", json=self._dump(update_data))

    async def delete_competition(self, comp_id: str) -> Dict:
        return await self._request("DELETE", f"/competitions/{comp_id}")

    # --- 4. EXERCISES ---
    async def list_all_exercises(self) -> List[Dict]:
        return await self._request("GET", "/exercises/")
        
    async def get_exercise(self, ex_id: str) -> Optional[Dict]:
        return await self._request("GET", f"/exercises/{ex_id}")

    async def create_exercise(self, ex_data: Any) -> Dict:
        return await self._request("POST", "/exercises/", json=self._dump(ex_data))

    async def update_exercise(self, ex_id: str, update_data: Any) -> Dict:
        return await self._request("PATCH", f"/exercises/{ex_id}", json=self._dump(update_data))

    async def delete_exercise(self, ex_id: str) -> Dict:
        return await self._request("DELETE", f"/exercises/{ex_id}")

    async def link_exercise_to_competition(self, ex_id: str, comp_id: str) -> Dict:
        return await self._request("POST", f"/exercises/{ex_id}/competition/{comp_id}")

    async def link_exercise_to_tag(self, ex_id: str, tag_id: str) -> Dict:
        return await self._request("POST", f"/exercises/{ex_id}/tags/{tag_id}")

    async def get_exercise_competitions(self, ex_id: str) -> List[Dict]:
        return await self._request("GET", f"/exercises/{ex_id}/competitions")

    async def unlink_exercise_from_competition(self, ex_id: str, comp_id: str) -> Dict:
        return await self._request("DELETE", f"/exercises/{ex_id}/competition/{comp_id}")

    async def unlink_exercise_from_tag(self, ex_id: str, tag_id: str) -> Dict:
        return await self._request("DELETE", f"/exercises/{ex_id}/tags/{tag_id}")

    # --- 5. CONTAINERS ---
    async def list_containers(self) -> List[Dict]:
        return await self._request("GET", "/containers/")

    async def get_container(self, container_id: str) -> Optional[Dict]:
        return await self._request("GET", f"/containers/{container_id}")

    async def get_container_by_exercise(self, ex_id: str) -> Optional[Dict]:
        return await self._request("GET", f"/containers/exercise/{ex_id}")

    async def register_container(self, container_data: Any, exercises_id: str) -> Dict:
        return await self._request("POST", "/containers/", json=self._dump(container_data), params={"exercises_id": exercises_id})

    async def remove_container(self, container_id: str) -> Dict:
        return await self._request("DELETE", f"/containers/{container_id}")

    # --- 6. SOLVES & SCOREBOARD ---
    async def get_user_solves(self, user_id: str) -> List[Dict]:
        return await self._request("GET", f"/solves/{user_id}")

    async def submit_flag(self, solve_data: Any, user_id: str) -> Dict:
        return await self._request("POST", "/solves/submit", json=self._dump(solve_data), params={"users_id": user_id})

    async def get_scoreboard(self, comp_id: str) -> List[Dict]:
        return await self._request("GET", f"/scoreboard/{comp_id}")

    async def get_global_scoreboard(self) -> List[Dict]:
        return await self._request("GET", "/scoreboard/global")

    # --- 7. TAGS ---
    async def list_tags(self) -> List[Dict]:
        return await self._request("GET", "/tags/")

    async def create_tag(self, tag_data: Any) -> Dict:
        return await self._request("POST", "/tags/", json=self._dump(tag_data))

    async def delete_tag(self, tag_id: str) -> Dict:
        return await self._request("DELETE", f"/tags/{tag_id}")

    async def update_tag(self, tag_id: str, tag_data: Any) -> Dict:
        return await self._request("PATCH", f"/tags/{tag_id}", json=self._dump(tag_data))

    # --- 8. ATTENDANCE ---
    async def record_attendance(self, attendance_data: Any, user_id: str) -> Dict:
        return await self._request("POST", "/attendance/", json=self._dump(attendance_data), params={"users_id": user_id})

    async def get_all_attendances(self) -> List[Dict]:
        return await self._request("GET", "/attendance/")

    async def get_user_attendance(self, user_id: str) -> List[Dict]:
        return await self._request("GET", f"/attendance/user/{user_id}")

    async def get_competition_attendance(self, comp_id: str) -> List[Dict]:
        return await self._request("GET", f"/attendance/competition/{comp_id}")

interpreter = InterpreterClient()