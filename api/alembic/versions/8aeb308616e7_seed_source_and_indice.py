"""seed_source_and_indice

Revision ID: 8aeb308616e7
Revises: 781b140b7936
Create Date: 2026-11-16 14:48:30.155500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aeb308616e7'
down_revision: Union[str, None] = '781b140b7936'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insertion de la Source NOAA
    op.execute(
        """
        INSERT INTO sources (name, url, version, extracted_at) 
        VALUES ('NOAA CPC', 'https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt', 'v6', NOW())
        ON CONFLICT DO NOTHING;
        """
    )
    
    # Insertion de l'Indice ONI
    op.execute(
        """
        INSERT INTO indices (code, label, unit) 
        VALUES ('ONI', 'Oceanic Niño Index', '°C anomaly')
        ON CONFLICT (code) DO NOTHING;
        """
    )

def downgrade() -> None:
    # Suppression des données insérées
    op.execute("DELETE FROM indices WHERE code = 'ONI';")
    op.execute("DELETE FROM sources WHERE name = 'NOAA CPC';")