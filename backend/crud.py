import json
import logging
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
import redis.asyncio as aioredis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import Post, User, Session
from backend.schemas import PostCreate, PostResponse, UserCreate
from backend.config import settings

logger = logging.getLogger(__name__)

# Redis Client Setup
redis_client: Optional[aioredis.Redis] = None

def get_redis_client() -> Optional[aioredis.Redis]:
    global redis_client
    if redis_client is None:
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            logger.info("Connected to Redis successfully for caching.")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}. Running without Redis cache.")
            redis_client = None
    return redis_client

# Helper functions for serialization
def serialize_post(post: Post) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.author,
        "tags": post.tags,
        "created_at": post.created_at.isoformat()
    }

async def get_posts(db: AsyncSession) -> List[dict]:
    cache_key = "all_posts"
    client = get_redis_client()
    
    # 1. Attempt to fetch from Redis Cache (Read Path)
    if client:
        try:
            cached_data = await client.get(cache_key)
            if cached_data:
                logger.info("Cache HIT: Retrieved posts from Redis.")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}. Falling back to Database.")

    # 2. Cache MISS: Fetch from PostgreSQL database asynchronously
    logger.info("Cache MISS: Querying PostgreSQL database.")
    result = await db.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()
    serialized_posts = [serialize_post(post) for post in posts]
    
    # 3. Populate Redis Cache asynchronously (Write Path)
    if client and serialized_posts:
        try:
            await client.setex(
                cache_key,
                settings.CACHE_TTL,
                json.dumps(serialized_posts)
            )
            logger.info("Successfully cached posts in Redis.")
        except Exception as e:
            logger.warning(f"Redis set failed: {e}.")
            
    return serialized_posts

async def create_post(db: AsyncSession, post_in: PostCreate) -> Post:
    # 1. Insert new post into DB asynchronously
    new_post = Post(
        title=post_in.title,
        content=post_in.content,
        author=post_in.author,
        tags=post_in.tags
    )
    db.add(new_post)
    await db.flush()  # assign ID
    await db.refresh(new_post)  # load default database attributes (like created_at)
    
    # 2. Invalidate Redis Cache so clients get fresh data instantly
    client = get_redis_client()
    if client:
        try:
            await client.delete("all_posts")
            logger.info("Cache Invalidated: Deleted 'all_posts' key.")
        except Exception as e:
            logger.warning(f"Redis cache invalidation failed: {e}.")
            
    return new_post

# --- Custom Password Hashing & Verification ---
def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with a unique salt."""
    salt = os.urandom(16)
    # Using 100,000 iterations for secure hashing
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(stored_hashed: str, provided_password: str) -> bool:
    """Verify a password against stored PBKDF2 hash."""
    try:
        salt_hex, key_hex = stored_hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return secrets.compare_digest(expected_key, key)
    except Exception:
        return False

# --- User Helpers ---
async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    hashed = hash_password(user_in.password)
    new_user = User(
        username=user_in.username,
        hashed_password=hashed
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

# --- Session Helpers ---
async def create_session(db: AsyncSession, user_id: int) -> Session:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    new_session = Session(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(new_session)
    await db.flush()
    await db.refresh(new_session)
    return new_session

async def get_session_user(db: AsyncSession, token: str) -> Optional[User]:
    now = datetime.utcnow()
    result = await db.execute(
        select(Session)
        .where(Session.token == token)
        .where(Session.expires_at > now)
    )
    session = result.scalars().first()
    if not session:
        return None
        
    return await get_user_by_id(db, session.user_id)

async def delete_session(db: AsyncSession, token: str) -> bool:
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalars().first()
    if session:
        await db.delete(session)
        await db.flush()
        return True
    return False

