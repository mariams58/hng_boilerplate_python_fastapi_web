from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    HTTPException, Response, Request, Query
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import Annotated, List, Optional
from datetime import datetime
from sqlalchemy import and_, or_, cast, String

from api.db.database import get_db
from api.utils.pagination import paginated_response
from api.utils.success_response import success_response
from api.v1.models.user import User
from api.v1.models.blog import Blog
from api.v1.schemas.blog import (
    BlogCreate,
    BlogPostResponse,
    BlogRequest,
    BlogUpdateResponseModel,
    BlogLikeDislikeResponse,
    CommentRequest,
    CommentUpdateResponseModel,
    BlogSearchResponse
)
from api.v1.services.blog import BlogService, BlogDislikeService, BlogLikeService
from api.v1.services.user import user_service
from api.v1.schemas.comment import CommentCreate, CommentSuccessResponse
from api.v1.services.comment import comment_service
from api.v1.services.comment import CommentService
from api.utils.client_helpers import get_ip_address

blog = APIRouter(prefix="/blogs", tags=["Blog"])


@blog.post("/", response_model=success_response)
def create_blog(
    blog: BlogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_super_admin),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="You are not Authorized")
    blog_service = BlogService(db)
    new_blogpost = blog_service.create(db=db, schema=blog, author_id=current_user.id)

    return success_response(
        message="Blog created successfully!",
        status_code=200,
        data=jsonable_encoder(new_blogpost),
    )


@blog.get("/", response_model=success_response)
def get_all_blogs(db: Session = Depends(get_db), limit: int = 10, skip: int = 0):
    """Endpoint to get all blogs"""

    return paginated_response(
        db=db,
        model=Blog,
        limit=limit,
        skip=skip,
        filters={"is_deleted": False} #filter out soft-deleted blogs
    )

# blog search endpoint
@blog.get("/search", response_model=BlogSearchResponse)
def search_blogs(
    db: Session = Depends(get_db),
    keyword: Optional[str] = Query(None, description="Search in title and content"),
    category: Optional[str] = Query(None, description="Filter by blog category"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    start_date: Optional[str] = Query(None, description="Start date for date range filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for date range filter (YYYY-MM-DD)"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """
    Search and filter blogs based on different parameters.
    """
    blog_service = BlogService(db)
    
    # Build the filters
    filters = []
    
    if keyword:
        filters.append(or_(
            Blog.title.ilike(f"%{keyword}%"),
            Blog.content.ilike(f"%{keyword}%"),
            Blog.excerpt.ilike(f"%{keyword}%")
        ))
    
    if category:
        # Assuming category might be stored in tags or as a separate field
        filters.append(or_(
            cast(Blog.tags, String).ilike(f"%{category}%")
        ))
    
    if author:
        query = blog_service.db.query(User.id).filter(
            or_(
                User.first_name.ilike(f"%{author}%"),
                User.last_name.ilike(f"%{author}%"),
            )
        ).all()

        author_ids = [user_id[0] for user_id in query]
        if author_ids:
            filters.append(Blog.author_id.in_(author_ids))
        else:
            # No matching authors, return empty result
            return {
                "status_code": 200,
                "total_results": 0,
                "blogs": []
            }
    
    # Rest of the function remains the same
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            filters.append(Blog.created_at >= start_date_obj)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid start_date format. Use YYYY-MM-DD."
            )
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            # Add 1 day to include the end date
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            filters.append(Blog.created_at <= end_date_obj)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid end_date format. Use YYYY-MM-DD."
            )
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        for tag in tag_list:
            filters.append(cast(Blog.tags, str).ilike(f"%{tag}%"))
    
    # Get total count and paginated results
    search_results = blog_service.search_blogs(
        filters=filters,
        page=page,
        per_page=per_page
    )
    
    # Fix the tags format in the returned blogs
    processed_blogs = []
    for blog in search_results["items"]:
        blog_dict = blog
        # Convert PostgreSQL array format to Python list
        if "tags" in blog_dict and blog_dict["tags"]:
            # Check if tags is in PostgreSQL array format
            if isinstance(blog_dict["tags"], str) and blog_dict["tags"].startswith('{') and blog_dict["tags"].endswith('}'):
                # Remove curly braces and split by commas
                tags_str = blog_dict["tags"][1:-1]
                # Simple split for basic cases
                import re
                # This regex handles both quoted and unquoted elements in the array
                tags_list = re.findall(r'"([^"]*)"|\s*([^,]+)', tags_str)
                # Extract the matched groups and clean them
                blog_dict["tags"] = [t[0] or t[1].strip() for t in tags_list if t[0] or t[1].strip()]
        processed_blogs.append(blog_dict)
    
    return {
        "status_code": 200,
        "total_results": search_results["total"],
        "blogs": processed_blogs
    }

@blog.get("/{id}", response_model=BlogPostResponse)
def get_blog_by_id(id: str, db: Session = Depends(get_db)):
    """
    Retrieve a blog post by its Id.

    Args:
        id (str): The ID of the blog post.
        db (Session): The database session.

    Returns:
        BlogPostResponse: The blog post data.

    Raises:
        HTTPException: If the blog post is not found.
    """
    blog_service = BlogService(db)

    # Fetch blog and increment view count
    blog_post = blog_service.fetch_and_increment_view(id)

    return success_response(
        message="Blog post retrieved successfully!",
        status_code=200,
        data=jsonable_encoder(blog_post),
    )


@blog.put("/{id}", response_model=BlogUpdateResponseModel)
async def update_blog(
    id: str,
    blogPost: BlogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_super_admin),
):
    """Endpoint to update a blog post"""

    blog_service = BlogService(db)
    updated_blog_post = blog_service.update(
        blog_id=id,
        title=blogPost.title,
        content=blogPost.content,
        current_user=current_user,
    )

    return success_response(
        message="Blog post updated successfully",
        status_code=200,
        data=jsonable_encoder(updated_blog_post),
    )


@blog.post("/{blog_id}/like", response_model=BlogLikeDislikeResponse)
def like_blog_post(
    blog_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_user),
):
    """Endpoint to add `like` to a blog post.
    Existing `dislike` by the `current_user` is automatically deleted.

    args:
        blog_id: `str` The ID of the blog post.
        request: `default` Request.
        db: `default` Session.

    return:
        In the `data` returned, `"object"` represents details of the 
        BlogLike obj and the `"objects_count"` represents the number 
        of BlogLike for the blog post
    """
    blog_service = BlogService(db)

    # get blog post
    blog_p = blog_service.fetch(blog_id)

    # confirm current user has NOT liked before
    blog_service.check_user_already_liked_blog(blog_p, current_user)

    # check for BlogDislike by current user and delete it
    blog_service.delete_opposite_blog_like_or_dislike(blog_p, current_user, "like")

    # update likes
    new_like = blog_service.create_blog_like(
        db, blog_p.id, current_user.id, ip_address=get_ip_address(request))

    # Return success response
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Like recorded successfully.",
        data={
            'object': new_like.to_dict(), 
            'objects_count': blog_service.num_of_likes(blog_id)
        },
    )


@blog.post("/{blog_id}/dislike", response_model=BlogLikeDislikeResponse)
def dislike_blog_post(
    blog_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_user),
):
    """Endpoint to add `dislike` to a blog post.
    Existing `like` by the `current_user` is automatically deleted.

    args:
        blog_id: `str` The ID of the blog post.
        request: `default` Request.
        db: `default` Session.

    return:
        In the `data` returned, `"object"` represents details of the 
        BlogDislike obj and the `"objects_count"` represents the number 
        of BlogDislike for the blog post
    """
    blog_service = BlogService(db)

    # get blog post
    blog_p = blog_service.fetch(blog_id)

    # confirm current user has NOT disliked before
    blog_service.check_user_already_disliked_blog(blog_p, current_user)

    # check for BlogLike by current user and delete it
    blog_service.delete_opposite_blog_like_or_dislike(blog_p, current_user, "dislike")

    # update disikes
    new_dislike = blog_service.create_blog_dislike(
        db, blog_p.id, current_user.id, ip_address=get_ip_address(request))

    # Return success response
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Dislike recorded successfully.",
        data={
            'object': new_dislike.to_dict(), 
            'objects_count': blog_service.num_of_dislikes(blog_id)
        },
    )


@blog.get("/{post_id}/likes-dislikes")
def get_likes_dislikes_count(
    post_id: str,
    db: Session = Depends(get_db),
):
    """Fetch total number of likes and dislikes for a blog post."""
    blog_service = BlogService(db)
    
    # Validate if blog post exists
    blog_service.fetch(post_id)
    
    # Fetch like and dislike counts
    likes_count = blog_service.num_of_likes(post_id)
    dislikes_count = blog_service.num_of_dislikes(post_id)
    
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Likes and dislikes retrieved successfully",
        data={
            "post_id": post_id,
            "likes": likes_count,
            "dislikes": dislikes_count,
        }
    )


@blog.delete("/{id}", status_code=204)
async def delete_blog_post(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_super_admin),
):
    """Endpoint to delete a blog post"""

    blog_service = BlogService(db=db)
    blog_service.delete(blog_id=id)

@blog.put("/{blog_id}/soft_delete")
async def archive_blog_post(
    blog_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_super_admin),
):
    
    """Endpoint to archive/soft-delete a blog post"""

    blog_service = BlogService(db=db)
    blog_post = blog_service.fetch(blog_id=id)
    if not blog_post:
        raise HTTPException(status_code=404, detail="Post not found")
    #check if admin/ authorized user
    if not (blog_post.author_id != current_user.id or current_user.is_superadmin):
        raise HTTPException(status_code=403, detail="You don't have permission to perform this action")
    
    blog_post.is_deleted = True
    db.commit()
    db.refresh(blog_post)

    return success_response(
        message="Blog post archived successfully!",
        status_code=200,
        data=jsonable_encoder(blog_post),
    )



# Post a comment to a blog
@blog.post("/{blog_id}/comments", response_model=CommentSuccessResponse)
async def add_comment_to_blog(
    blog_id: str,
    current_user: Annotated[User, Depends(user_service.get_current_user)],
    comment: CommentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Post endpoint for authenticated users to add comments to a blog.

    Args:
        blog_id (str): the id of the blog to be commented on
        current_user: the current authenticated user
        comment (CommentCreate): the body of the request
        db: the database session object

    Returns:
        Response: a response object containing the comment details if successful or appropriate errors if not
    """

    user_id = current_user.id
    new_comment = comment_service.create(
        db=db, schema=comment, user_id=user_id, blog_id=blog_id
    )

    return success_response(
        message="Comment added successfully!",
        status_code=201,
        data=jsonable_encoder(new_comment),
    )


@blog.get("/{blog_id}/comments")
async def comments(
    db: Annotated[Session, Depends(get_db)],
    blog_id: str,
    page: int = 1,
    per_page: int = 20,
) -> object:
    """
    Retrieves all comments associated with a blog

    Args:
        db: Database Session object
        blog_id: the blog associated with the comments
        page: the number of the current page
        per_page: the page size for a current page
    Returns:
        Response: An exception if error occurs
        object: Response object containing the comments
    """
    comment_services = CommentService()
    comments_response = comment_services.validate_params(blog_id, page, per_page, db)
    if comments_response == 'Blog not found':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Blog not found")
    return comments_response

# Update a blog comment
@blog.put("/{blog_id}/comments/{comment_id}", response_model=CommentUpdateResponseModel)
async def update_blog_comment(
    blog_id: str,
    comment_id: str,
    blogComment: CommentRequest,
    current_user: Annotated[User, Depends(user_service.get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Updates a blog comment

    Args:
        - blog_id (str): the ID of the blog
        - comment_id (str): the ID of the comment
        - blogComment: the new comment to update to
        - current_user: the current authenticated user
        - db: the database session

    Returns:
        dict: updated comment body
    """

    blog_service = BlogService(db)
    updated_blog_comment = blog_service.update_blog_comment(
        blog_id=blog_id,
        comment_id=comment_id,
        content=blogComment.content,
        current_user=current_user,
    )

    return success_response(
        message="Blog comment updated successfully",
        status_code=200,
        data=jsonable_encoder(updated_blog_comment)
    )


@blog.delete("/likes/{blog_like_id}", 
             status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog_like(
    blog_like_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_user),
):
    """Endpoint to delete `BlogLike`

    args:
        blog_like_id: `str` The ID of the BlogLike object.
        request: `default` Request.
        db: `default` Session.
    """
    
    # Validate User
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    
    blog_like_service = BlogLikeService(db)
    
    blog_like = blog_like_service.fetch(blog_like_id)
    
    # Check if blogLike exist
    if not blog_like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BlogLike does not exist"
        )
    
    # Check if current user is the owner of blogLike
    if blog_like.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Insufficient permission"
        )
    
    db.delete(blog_like)
    db.commit()
    
    return Response(
        status_code=204
    )

@blog.delete("/dislikes/{blog_dislike_id}", 
             status_code=status.HTTP_204_NO_CONTENT)
def delete_blog_dislike(
    blog_dislike_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_service.get_current_user),
):
    """Endpoint to delete `BlogDislike`

    args:
        blog_dislike_id: `str` The ID of the BlogDislike object.
        request: `default` Request.
        db: `default` Session.
    """
    blog_dislike_service = BlogDislikeService(db)

    # delete blog dislike
    return blog_dislike_service.delete(blog_dislike_id, current_user.id)
