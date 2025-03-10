import motor.motor_asyncio
from pymongo.errors import ConnectionFailure
import asyncio
from typing import Optional, Any


class MongoDBConnection:
    """
    Manages the connection to MongoDB.

    This class handles connection lifecycle, session management,
    and transactions for MongoDB operations.
    """

    def __init__(self, connection_string: str, db_name: str):
        """
        Initialize the MongoDB connection.

        Args:
            connection_string: MongoDB connection string
            db_name: Name of the database
        """
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None

    async def connect(self) -> None:
        """
        Establish connection to MongoDB.

        Raises:
            ConnectionFailure: If connection fails
        """
        try:
            # Create a Motor client instance
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )

            # Ping the server to verify connection
            await self.client.admin.command('ping')

            # Get database
            self.db = self.client[self.db_name]

        except Exception as e:
            self.client = None
            self.db = None
            raise ConnectionFailure(
                f"Failed to connect to MongoDB: {str(e)}") from e

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    def get_collection(self,
                       collection_name: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """
        Get a MongoDB collection.

        Args:
            collection_name: Name of the collection

        Returns:
            The MongoDB collection object

        Raises:
            ValueError: If not connected or invalid collection name
        """
        if not self.db:
            raise ValueError("Not connected to MongoDB")

        if not collection_name:
            raise ValueError("Invalid collection name")

        return self.db[collection_name]

    async def start_transaction(self) -> Any:
        """
        Start a MongoDB transaction.

        Returns:
            A session object for the transaction

        Raises:
            ValueError: If not connected
            RuntimeError: If transactions are not supported
        """
        if not self.client:
            raise ValueError("Not connected to MongoDB")

        # Create a client session
        session = await self.client.start_session()

        # Start a transaction
        session.start_transaction()

        return session

    async def commit_transaction(self, session: Any) -> None:
        """
        Commit a MongoDB transaction.

        Args:
            session: Session object from start_transaction

        Raises:
            ValueError: If session is None
        """
        if not session:
            raise ValueError("Invalid session")

        try:
            await session.commit_transaction()
        finally:
            await session.end_session()

    async def abort_transaction(self, session: Any) -> None:
        """
        Abort a MongoDB transaction.

        Args:
            session: Session object from start_transaction

        Raises:
            ValueError: If session is None
        """
        if not session:
            raise ValueError("Invalid session")

        try:
            await session.abort_transaction()
        finally:
            await session.end_session()

    async def create_indexes(self, collection_name: str, indexes: list) -> None:
        """
        Create indexes in a collection.

        Args:
            collection_name: Name of the collection
            indexes: List of index specifications

        Raises:
            ValueError: If not connected or invalid collection name
        """
        if not self.db:
            raise ValueError("Not connected to MongoDB")

        if not collection_name:
            raise ValueError("Invalid collection name")

        if not indexes:
            return

        collection = self.db[collection_name]
        for index_spec in indexes:
            await collection.create_index(**index_spec)