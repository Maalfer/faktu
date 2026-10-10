"""Export completo de los datos del usuario (ZIP de CSVs)."""
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import User
from app.services.export import build_export_zip

router = APIRouter(tags=["meta"])


@router.get("/export")
async def export_all(user: CurrentUser, db: DbSession) -> Response:
    """Descarga el 100% de los datos del usuario en un ZIP de CSVs."""
    # `user` ya está validado por get_current_user; lo resolvemos para asegurar
    # que user_id está en la fila (necesario para los joins de la query).
    db_user = await db.scalar(select(User).where(User.id == user.id))
    zip_bytes = await build_export_zip(db, db_user.id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"faktu-export-{stamp}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )
