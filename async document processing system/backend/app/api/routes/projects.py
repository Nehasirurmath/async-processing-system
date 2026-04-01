from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.run import Run
from app.workers.tasks import process_run


router = APIRouter()
uploads_dir = Path("uploads")


class ProjectCreateResponse(BaseModel):
    id: str
    name: str
    description: str
    original_filename: str
    stored_filename: str
    stored_path: str
    file_type: str
    file_size: int
    status: str
    created_at: str


class MessageResponse(BaseModel):
    message: str


class RunCreateResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    progress: int
    current_stage: str
    created_at: str


@router.get("", response_model=list[ProjectCreateResponse])
def list_projects(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> list[ProjectCreateResponse]:
    query = db.query(Project)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Project.name.ilike(pattern),
                Project.description.ilike(pattern),
                Project.original_filename.ilike(pattern),
            )
        )

    if status_filter:
        query = query.filter(Project.status == status_filter)

    sortable_columns = {
        "created_at": Project.created_at,
        "name": Project.name,
        "status": Project.status,
    }
    sort_column = sortable_columns.get(sort_by, Project.created_at)
    query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())

    projects = query.all()
    return [
        ProjectCreateResponse(
            id=str(project.id),
            name=project.name,
            description=project.description or "",
            original_filename=project.original_filename,
            stored_filename=project.stored_filename,
            stored_path=project.stored_path,
            file_type=project.file_type or "text/csv",
            file_size=project.file_size,
            status=project.status,
            created_at=project.created_at.isoformat(),
        )
        for project in projects
    ]


@router.get("/{project_id}", response_model=ProjectCreateResponse)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectCreateResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectCreateResponse(
        id=str(project.id),
        name=project.name,
        description=project.description or "",
        original_filename=project.original_filename,
        stored_filename=project.stored_filename,
        stored_path=project.stored_path,
        file_type=project.file_type or "text/csv",
        file_size=project.file_size,
        status=project.status,
        created_at=project.created_at.isoformat(),
    )


@router.post("", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ProjectCreateResponse:
    original_filename = file.filename or ""
    if not original_filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    uploads_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}.csv"
    destination = uploads_dir / stored_filename
    content = await file.read()
    destination.write_bytes(content)

    project_id = uuid4()
    project = Project(
        id=project_id,
        name=name.strip(),
        description=description.strip() or None,
        original_filename=original_filename,
        stored_filename=stored_filename,
        stored_path=str(destination),
        file_type=file.content_type or "text/csv",
        file_size=len(content),
        status="queued",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectCreateResponse(
        id=str(project.id),
        name=project.name,
        description=project.description or "",
        original_filename=project.original_filename,
        stored_filename=project.stored_filename,
        stored_path=project.stored_path,
        file_type=project.file_type or "text/csv",
        file_size=project.file_size,
        status=project.status,
        created_at=project.created_at.isoformat(),
    )


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> MessageResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path = Path(project.stored_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(project)
    db.commit()

    return MessageResponse(message="Deleted successfully")


@router.post("/{project_id}/run", response_model=RunCreateResponse, status_code=status.HTTP_201_CREATED)
def create_run(project_id: str, db: Session = Depends(get_db)) -> RunCreateResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = Run(
        id=uuid4(),
        project_id=project.id,
        status="queued",
        progress=0,
        current_stage="queued",
        error_message=None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    process_run.delay(str(run.id))

    return RunCreateResponse(
        run_id=str(run.id),
        project_id=str(run.project_id),
        status=run.status,
        progress=run.progress,
        current_stage=run.current_stage,
        created_at=run.created_at.isoformat(),
    )
