from api.core.base.services import Service
from api.v1.models.bookmark import Bookmark
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

class BookmarkService(Service):
    """Bookmark Job service functionality"""
    
    @staticmethod
    def bookmark_exist(db: Session, user_id: str, job_id: str):
        bookmark = db.query(Bookmark).filter(
            Bookmark.user_id == user_id,
            Bookmark.job_id == job_id
            ).first()
        if bookmark:
            return True
        return False


    def create(self, db: Session, job_id: str, user_id: str) -> Bookmark:
        if self.bookmark_exist(db, user_id, job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job already saved"
                )

        new_bookmark = Bookmark(
            user_id=user_id,
            job_id=job_id
        )

        db.add(new_bookmark)
        db.commit()
        db.refresh(new_bookmark)
        return new_bookmark
    


    def fetch_all(self, db: Session, user_id: str) -> List[Bookmark]:
        """
        Fetches all bookmarks for the specified user.
        
        Args:
            db (Session): SQLAlchemy database session.
            user_id (str): The id of the user.
            
        Returns:
            List[Bookmark]: A list of Bookmarked job objects.
        """
        bookmarks = db.query(Bookmark).filter(Bookmark.user_id == user_id).all()
        jobs = [bookmark.job for bookmark in bookmarks if bookmark.job]
        return jobs

bookmark_service = BookmarkService()