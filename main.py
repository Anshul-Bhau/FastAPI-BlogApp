from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from schemas import PostCreate, PostResponse, UserCreate, UserResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from typing import Annotated

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse

# from fastapi.responses import HTMLResponse

# DATA FLOW
# REQUEST COMES
# PYDANTIC VALIDATES IT
# SQLALCHEMY STORES OR RETRIEVES THE DATA
# PYDANTIC FORMATS THE DATA
# RESPONSE GOES OUT

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

# posts : list[dict] = [
#     {
#         "id": 1,
#         "author": "Corey Schafer",
#         "title": "FastAPI is Awesome",
#         "content": "This framework is really easy to use and super fast",
#         "date_posted": "April 20, 2025"
#     },
#     {
#         "id": 2,
#         "author": "Sober",
#         "title": "Python",
#         "content": "Stupid Snake",
#         "date_posted": "April 21, 2025"
#     }

# ]

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request):
    return templates.TemplateResponse(request,
                                    "home.html", 
                                    {"posts":posts,
                                    "title" : "Home"})

@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request:Request, post_id : int):
    for post in posts:
        if post.get("id") == post_id:
            title = post['title'][:50]
            return templates.TemplateResponse(request,
                                    "post.html", 
                                    {"post":post,
                                    "title" : title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.post(
        "/api/users",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED
)
def create_user(user: UserCreate, db:Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.user).where(models.User.username == user.username)
        )
    
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    result = db.execute(
        select(models.user).where(models.User.email == user.email)
        )
    
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    new_user = models.User(
        username = user.username,
        email = user.email
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.get("api/users/{user_id}", response_model=UserResponse)
def get_user(user_id : int, db:Annotated[Session, Depends(get_db)]):
    result = db.execute(
        select(models.user).where(models.User.id == user_id)
        )
    user = result.scalars().first()

    if user:
        return user
    
    raise HTTPException(
        status_code= status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

@app.get("api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = db.execute(select(models.Post).where(models.user_id == user_id))
    posts = result.scalars().first()
    return posts

@app.get("/api/posts", response_model=list[PostResponse])
def get_posts():
    return posts

@app.post(
        "/api/posts",
        response_model=PostResponse,
        status_code=status.HTTP_201_CREATED
)
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id" : new_id,
        "author" : post.author,
        "title" : post.title,
        "content" : post.content,
        "date_posted" : "April 23, 2025",
    }
    posts.append(new_post)
    return new_post

@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id : int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

# Starlette Exception Handler
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request : Request, exception : StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occured. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail":message}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message
        },
        status_code=exception.status_code
    )

# RequestValidationError Handler
@app.exception_handler(RequestValidationError)
def validation_execption_handler(request : Request, exception:Exception):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code" : status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again."
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )

