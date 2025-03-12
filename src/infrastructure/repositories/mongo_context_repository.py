import pymongo
from pymongo.errors import DuplicateKeyError, PyMongoError
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import logging

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.context_repository import ContextRepository
from src.infrastructure.adapters.mongodb_connection import MongoDBConnection


class MongoContextRepository(ContextRepository):
    """MongoDB implementation of the ContextRepository interface."""

    def __init__(
            self,
            connection: Optional[MongoDBConnection] = None,
            db_name: Optional[str] = None,
            collection_name: str = "context_items",
            vector_collection_name: str = "context_vectors"
    ):
        """
        Initialize the MongoDB context repository.

        Args:
            connection: MongoDB connection (optional)
            db_name: Name of the database (optional, if connection is provided)
            collection_name: Name of the collection for context items
            vector_collection_name: Name of the collection for vector embeddings
        """
        self.connection = connection
        self.db_name = db_name
        self.collection_name = collection_name
        self.vector_collection_name = vector_collection_name
        self._collection = None
        self._vector_collection = None
        self.logger = logging.getLogger(__name__)

    def _ensure_connection(self) -> None:
        """Ensure MongoDB connection is established."""
        if self.connection and not self.connection.client:
            self.connection.connect()

        if self._collection is None or self._vector_collection is None:
            if self.connection:
                self._collection = self.connection.get_collection(
                    self.collection_name)
                self._vector_collection = self.connection.get_collection(
                    self.vector_collection_name)
            else:
                # Create a new connection if one wasn't provided
                client = pymongo.MongoClient()
                db = client[self.db_name or "walk"]
                self._collection = db[self.collection_name]
                self._vector_collection = db[self.vector_collection_name]

        # Create indexes if they don't exist
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create necessary indexes in MongoDB collections."""
        try:
            # Context items collection indexes
            self._collection.create_index("id", unique=True)
            self._collection.create_index("content_type")
            self._collection.create_index("source")

            # Vector collection indexes
            self._vector_collection.create_index("id", unique=True)
            self._vector_collection.create_index([("vector", "2dsphere")])
        except PyMongoError as e:
            self.logger.warning(f"Failed to create indexes: {str(e)}")

    def _entity_to_document(self, entity: ContextItem) -> Dict[str, Any]:
        """
        Convert a ContextItem entity to a MongoDB document.

        Args:
            entity: ContextItem to convert

        Returns:
            MongoDB document representation
        """
        return {
            "id": entity.id,
            "source": entity.source,
            "content": entity.content,
            "content_type": entity.content_type,
            "metadata": entity.metadata,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at
        }

    def _document_to_entity(self, document: Dict[str, Any]) -> ContextItem:
        """
        Convert a MongoDB document to a ContextItem entity.

        Args:
            document: MongoDB document

        Returns:
            ContextItem entity
        """
        if not document:
            return None

        # Handle the ObjectId
        if "_id" in document:
            document.pop("_id")

        # Convert content_type string to enum if it's a string
        content_type = document["content_type"]
        if isinstance(content_type, str):
            content_type = ContentType(content_type)

        return ContextItem(
            id=document["id"],
            source=document["source"],
            content=document["content"],
            content_type=content_type,
            metadata=document.get("metadata", {}),
            embedding=None,  # Embeddings are stored separately
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at")
        )

    def add(self, context_item: ContextItem) -> ContextItem:
        """
        Add a context item to the repository.

        Args:
            context_item: The context item to add

        Returns:
            The added context item

        Raises:
            DuplicateKeyError: If an item with the same ID already exists
            PyMongoError: For other MongoDB errors
        """
        self._ensure_connection()

        try:
            # Store the main document
            document = self._entity_to_document(context_item)
            self._collection.insert_one(document)

            # Store the vector separately for efficient similarity search
            if context_item.embedding:
                vector_document = {
                    "id": context_item.id,
                    "vector": context_item.embedding
                }
                self._vector_collection.insert_one(vector_document)

            return context_item

        except DuplicateKeyError:
            self.logger.error(f"Item with ID {context_item.id} already exists")
            raise
        except PyMongoError as e:
            self.logger.error(f"Failed to add context item: {str(e)}")
            raise

    def get_by_id(self, context_id: str) -> Optional[ContextItem]:
        """
        Get a context item by ID.

        Args:
            context_id: ID of the context item to retrieve

        Returns:
            The context item, or None if not found

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Get the main document
            document = self._collection.find_one({"id": context_id})
            if not document:
                return None

            # Get the vector
            vector_document = self._vector_collection.find_one(
                {"id": context_id})

            # Create the entity
            entity = self._document_to_entity(document)
            if vector_document:
                entity.embedding = vector_document.get("vector")

            return entity

        except PyMongoError as e:
            self.logger.error(
                f"Failed to get context item {context_id}: {str(e)}")
            raise

    def update(self, context_item: ContextItem) -> ContextItem:
        """
        Update a context item in the repository.

        Args:
            context_item: The context item to update

        Returns:
            The updated context item

        Raises:
            KeyError: If the context item does not exist
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Check if the item exists
            existing = self._collection.find_one({"id": context_item.id})
            if not existing:
                raise KeyError(
                    f"Context item with ID {context_item.id} not found")

            # Update the main document
            context_item.updated_at = datetime.now()
            document = self._entity_to_document(context_item)

            result = self._collection.update_one(
                {"id": context_item.id},
                {"$set": document}
            )

            # Update the vector
            if context_item.embedding:
                self._vector_collection.update_one(
                    {"id": context_item.id},
                    {"$set": {"vector": context_item.embedding}},
                    upsert=True
                )

            return context_item

        except KeyError:
            raise
        except PyMongoError as e:
            self.logger.error(
                f"Failed to update context item {context_item.id}: {str(e)}")
            raise

    def delete(self, context_id: str) -> bool:
        """
        Delete a context item from the repository.

        Args:
            context_id: ID of the context item to delete

        Returns:
            True if the item was deleted, False otherwise

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Delete the main document
            result = self._collection.delete_one({"id": context_id})

            # Delete the vector
            self._vector_collection.delete_one({"id": context_id})

            return result.deleted_count > 0

        except PyMongoError as e:
            self.logger.error(
                f"Failed to delete context item {context_id}: {str(e)}")
            raise

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[
        ContextItem]:
        """
        List context items matching the given filters.

        Args:
            filters: Optional filters for the query

        Returns:
            List of context items matching the filters

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Prepare query
            query = {}
            if filters:
                for key, value in filters.items():
                    # Handle special case for content_type enum
                    if key == "content_type" and isinstance(value, ContentType):
                        query[key] = value.value
                    else:
                        query[key] = value

            # Execute query
            cursor = self._collection.find(query)
            documents = cursor.to_list(length=100)  # Limit to 100 items

            # Convert to entities
            items = []
            for document in documents:
                entity = self._document_to_entity(document)

                # Get the vector if available
                vector_document = self._vector_collection.find_one(
                    {"id": entity.id})
                if vector_document:
                    entity.embedding = vector_document.get("vector")

                items.append(entity)

            return items

        except PyMongoError as e:
            self.logger.error(f"Failed to list context items: {str(e)}")
            raise

    def search_by_vector(self, query_vector: List[float],
                       limit: int = 10) -> List[
        Tuple[ContextItem, float]]:
        """
        Search for context items by vector similarity.

        Args:
            query_vector: Query vector for similarity search
            limit: Maximum number of results to return

        Returns:
            List of tuples containing context items and their similarity scores

        Raises:
            PyMongoError: For MongoDB errors
        """
        self._ensure_connection()

        try:
            # Use MongoDB's $vectorSearch aggregation (MongoDB 5.0+) or fall back to manual calculation
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "queryVector": query_vector,
                        "path": "vector",
                        "numCandidates": limit * 10,
                        "limit": limit
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "id": 1,
                        "vector": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            try:
                # Try using $vectorSearch if available
                cursor = self._vector_collection.aggregate(pipeline)
                results = list(cursor)
            except PyMongoError:
                # Fall back to manual calculation
                self.logger.warning(
                    "Vector search not available, falling back to manual calculation")
                results = self._manual_vector_search(query_vector, limit)

            # Fetch the full items for each result
            items_with_scores = []
            for result in results:
                item_id = result["id"]
                score = result.get("score", 0.0)

                # Get the full item
                document = self._collection.find_one({"id": item_id})
                if document:
                    entity = self._document_to_entity(document)
                    entity.embedding = result.get("vector")
                    items_with_scores.append((entity, score))

            return items_with_scores

        except PyMongoError as e:
            self.logger.error(f"Failed to search by vector: {str(e)}")
            raise

    def _manual_vector_search(self, query_vector: List[float],
                            limit: int) -> List[Dict[str, Any]]:
        """
        Perform manual vector similarity search.

        This is a fallback for MongoDB versions that don't support $vectorSearch.

        Args:
            query_vector: Query vector
            limit: Maximum number of results

        Returns:
            List of results with id, vector, and score
        """
        import numpy as np

        # Get all vectors
        cursor = self._vector_collection.find({},
                                              {"_id": 0, "id": 1, "vector": 1})
        all_vectors = cursor.to_list(length=1000)  # Limit to 1000 items

        # Convert query vector to numpy array
        query_array = np.array(query_vector)

        # Calculate cosine similarity for each vector
        results = []
        for item in all_vectors:
            if "vector" not in item or not item["vector"]:
                continue

            vector_array = np.array(item["vector"])

            # Calculate cosine similarity
            dot_product = np.dot(query_array, vector_array)
            query_norm = np.linalg.norm(query_array)
            vector_norm = np.linalg.norm(vector_array)

            if query_norm == 0 or vector_norm == 0:
                similarity = 0
            else:
                similarity = dot_product / (query_norm * vector_norm)

            results.append({
                "id": item["id"],
                "vector": item["vector"],
                "score": float(similarity)
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)

        # Return top results
        return results[:limit]