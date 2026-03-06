# SMO Intelligence

Sistema de inteligencia competitiva para o Santa Maria Outlet (SMO).
Fase 1: Download automatico dos releases trimestrais de resultados dos grupos concorrentes listados na B3.

## Grupos monitorados

| Grupo | Ticker | Site RI |
|-------|--------|---------|
| Multiplan | MULT3 | ri.multiplan.com.br |
| Iguatemi S.A. | IGTI11 | ri.iguatemi.com.br |
| Allos | ALOS3 | ri.allos.com.br |
| General Shopping | GSHP3 | ri.generalshopping.com.br |

## Setup local

```bash
# 1. Copiar variaveis de ambiente
cp .env.example .env

# 2. Subir PostgreSQL
docker-compose up -d db

# 3. Instalar dependencias
pip install -r requirements.txt -r requirements-dev.txt

# 4. Rodar migrations
alembic upgrade head

# 5. Popular dados iniciais
python scripts/seed_db.py

# 6. Iniciar API
uvicorn app.main:app --reload
```

Acesse: http://localhost:8000/docs (Swagger UI)

## CLI

```bash
# Baixar releases de todos os grupos
python -m cli.main download

# Baixar releases de um grupo especifico
python -m cli.main download --grupo multiplan

# Listar releases disponiveis (dry-run)
python -m cli.main listar

# Relatorio de cobertura de downloads
python -m cli.main relatorio

# Comandos de banco
python -m cli.main db seed
python -m cli.main db migrate
```

## API Endpoints

### Health
- `GET /health` - Status da aplicacao

### Grupos
- `GET /api/v1/grupos` - Lista grupos ativos
- `GET /api/v1/grupos/{id}` - Detalhe do grupo com shoppings

### Shoppings
- `GET /api/v1/shoppings` - Lista com filtros: `?grupo_id=&concorrente_direto=&cidade=`
- `GET /api/v1/shoppings/{id}` - Detalhe com resultados

### Resultados
- `GET /api/v1/resultados` - Filtros: `?shopping_id=&ano=&trimestre=&grupo_id=`
- `GET /api/v1/resultados/comparativo` - Serie historica por shopping
- `GET /api/v1/resultados/concorrentes-rp` - Concorrentes de Ribeirao Preto

### Coleta
- `POST /api/v1/coleta/disparar` - Dispara download
- `GET /api/v1/coleta/status` - Status da coleta

## Deploy GCP Cloud Run

```bash
# Build e push para Artifact Registry
gcloud builds submit --tag gcr.io/PROJECT/smo-intelligence

# Deploy
gcloud run deploy smo-intelligence \
  --image gcr.io/PROJECT/smo-intelligence \
  --region southamerica-east1 \
  --set-env-vars DATABASE_URL=... \
  --service-account smo-sa@PROJECT.iam.gserviceaccount.com
```

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy 2.x async + asyncpg (PostgreSQL)
- requests + BeautifulSoup4 + lxml (scraping)
- Typer + Rich (CLI)
- Alembic (migrations)
- Docker + docker-compose
