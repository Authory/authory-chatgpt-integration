from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


# Copy of authory's source type enum.
class Source(str, Enum):
  Web = "Web",
  Offline = "Offline",
  Linkedin = "Linkedin",
  Facebook = "Facebook",
  Instagram = "Instagram",
  Twitter = "Twitter",
  PodcastRssFeed = "PodcastRssFeed",
  RssFeed = "RssFeed",
  Youtube = "Youtube",
  EntireInternet = "EntireInternet",
  Sitemap = "Sitemap"


class DocumentMetadata(BaseModel):
    source: Source = Source.Web
    source_id: str = ''
    source_name: str = ''
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: str = ''
    # Used for internal filtering, always required.
    author_id: str = ''


class DocumentChunkMetadata(DocumentMetadata):
    document_id: Optional[str] = None


class DocumentChunk(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: DocumentChunkMetadata
    embedding: Optional[List[float]] = None


class DocumentChunkWithScore(DocumentChunk):
    score: float


class Document(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[DocumentMetadata] = None


class DocumentWithChunks(Document):
    chunks: List[DocumentChunk]


class DocumentMetadataFilter(BaseModel):
    document_id: Optional[str] = None
    source: Optional[Source] = None
    source_name: Optional[str] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    start_date: Optional[str] = None  # any date string format
    end_date: Optional[str] = None  # any date string format
    # Used for internal filtering, overriden during request according to auth information
    author_id: Optional[str] = None


class Query(BaseModel):
    query: str
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 3


class QueryWithEmbedding(Query):
    embedding: List[float]


class QueryResult(BaseModel):
    query: str
    results: List[DocumentChunkWithScore]
