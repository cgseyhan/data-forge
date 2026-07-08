import sys
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.infrastructure.database.session import engine, init_db, get_session
from src.infrastructure.database.models import Base, Tenant

async def main():
    print("Dropping existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("Creating tables...")
    await init_db()
    
    print("Inserting mock tenant...")
    async with get_session() as session:
        mock_tenant = Tenant(
            api_key="test-api-key-123",
            company_name="Test Company LLC",
            is_active=True
        )
        session.add(mock_tenant)
        await session.commit()
        print(f"Inserted Mock Tenant: {mock_tenant.company_name} (API Key: {mock_tenant.api_key})")

if __name__ == "__main__":
    asyncio.run(main())
