#!/usr/bin/env python3
"""The Blog Post Model."""

from sqlalchemy import Column, String, Text, ForeignKey, Boolean, text, Index, Integer
from sqlalchemy.orm import relationship
from api.v1.models.base_model import BaseTableModel


class Blog(BaseTableModel):
    __tablename__ = "blogs"

    author_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    is_deleted = Column(Boolean, server_default=text("false"))
    excerpt = Column(Text, nullable=True)
    tags = Column(
        Text, nullable=True
    )  # Assuming tags are stored as a comma-separated string

    author = relationship("User", back_populates="blogs")
    comments = relationship(
        "Comment", back_populates="blog", cascade="all, delete-orphan"
    )
    likes = relationship(
        "BlogLike", back_populates="blog", cascade="all, delete-orphan"
    )
    dislikes = relationship(
        "BlogDislike", back_populates="blog", cascade="all, delete-orphan"
    )
    views = Column(Integer, nullable=False, server_default=text("0"))  # add views column to track views

    # Indexes
    __table_args__ = (
        Index('ix_blogs_author_id', author_id),
        Index('ix_blogs_title', title),
        Index('ix_blogs_tags', tags),
        Index('ix_blogs_is_deleted', is_deleted),
    )

class BlogDislike(BaseTableModel):
    __tablename__ = "blog_dislikes"

    blog_id = Column(String, ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String, nullable=True)

    # Relationships
    blog = relationship("Blog", back_populates="dislikes")
    user = relationship("User", back_populates="blog_dislikes")

    # Indexes
    __table_args__ = (
        Index('ix_blog_dislikes_blog_id', blog_id),
        Index('ix_blog_dislikes_user_id', user_id),
        # Composite index for unique constraint and faster lookups
        Index('ix_blog_dislikes_blog_user', blog_id, user_id, unique=True),
    )


class BlogLike(BaseTableModel):
    __tablename__ = "blog_likes"

    blog_id = Column(String, ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String, nullable=True)

    blog = relationship("Blog", back_populates="likes")
    user = relationship("User", back_populates="blog_likes")

    # Indexes
    __table_args__ = (
        Index('ix_blog_likes_blog_id', blog_id),
        Index('ix_blog_likes_user_id', user_id),
        # Composite index for unique constraint and faster lookups
        Index('ix_blog_likes_blog_user', blog_id, user_id, unique=True),
    )
