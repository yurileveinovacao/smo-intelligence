# Deploy — SMO Intelligence

## URLs de Producao
- **API:** `https://smo-intelligence-rutww5ppqq-rj.a.run.app`
- **Swagger:** `https://smo-intelligence-rutww5ppqq-rj.a.run.app/docs`
- **Painel Admin SMO:** https://admin.santamariaoutlet.com.br

## Recursos GCP (projeto smo-ia)

| Recurso | Nome | Regiao |
|---|---|---|
| Cloud Run | smo-intelligence | southamerica-east1 |
| Cloud SQL | smo-db-1 → banco `smo_intelligence` | southamerica-east1 |
| Artifact Registry | smo-docker | southamerica-east1 |
| Secret Manager | smo-intelligence-db-url | automatica |
| VPC Connector | smo-serverless-connector | southamerica-east1 |
| Cloud Scheduler | smo-intelligence-coleta-trimestral | southamerica-east1 |
| Service Account | smo-ia@appspot.gserviceaccount.com | — |

## Deploy automatico

Cada push na branch `main` do repositorio `smo-intelligence` dispara o Cloud Build
que executa o pipeline definido em `cloudbuild.yaml`:

1. **Build** — constroi imagem Docker e aplica tags (SHA + latest)
2. **Push** — envia imagem para Artifact Registry `smo-docker`
3. **Deploy** — atualiza Cloud Run `smo-intelligence` com a nova imagem

Logs de build: https://console.cloud.google.com/cloud-build/builds?project=smo-ia

## Configuracao Cloud Run

| Parametro | Valor |
|---|---|
| Memoria | 512Mi |
| CPU | 1 |
| Min instances | 0 (scale to zero) |
| Max instances | 3 |
| Timeout | 300s |
| Autenticacao | `--no-allow-unauthenticated` (requer identity token) |
| VPC Egress | private-ranges-only |
| Secrets | DATABASE_URL via Secret Manager |

## Comandos de manutencao

```bash
# Definir variaveis
export PROJECT_ID="smo-ia"
export REGION="southamerica-east1"
export SERVICE_NAME="smo-intelligence"

# Ver logs do servico
gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}

# Ver status do servico
gcloud run services describe ${SERVICE_NAME} --region=${REGION}

# Obter URL do servico
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)'

# Deploy manual (sem trigger — direto do codigo local)
gcloud builds submit --region=${REGION} --config=cloudbuild.yaml .

# Disparar coleta manual
INTEL_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
curl -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  ${INTEL_URL}/api/v1/coleta/disparar \
  -H "Content-Type: application/json" \
  -d '{"grupos": null, "forcar": false}'

# Rodar seed novamente (se necessario)
gcloud run jobs execute smo-intelligence-seed --region=${REGION} --wait

# Verificar scheduler
gcloud scheduler jobs list --location=${REGION}

# Executar scheduler manualmente (teste)
gcloud scheduler jobs run smo-intelligence-coleta-trimestral --location=${REGION}
```

## Testes end-to-end

```bash
TOKEN=$(gcloud auth print-identity-token)
INTEL_URL=$(gcloud run services describe smo-intelligence --region=southamerica-east1 --format='value(status.url)')

# Health check
curl -H "Authorization: Bearer ${TOKEN}" ${INTEL_URL}/health

# Listar grupos (esperado: 4)
curl -s -H "Authorization: Bearer ${TOKEN}" ${INTEL_URL}/api/v1/grupos | python3 -m json.tool

# Concorrentes Ribeirao Preto
curl -s -H "Authorization: Bearer ${TOKEN}" ${INTEL_URL}/api/v1/resultados/concorrentes-rp | python3 -m json.tool

# Comparativo trimestral
curl -s -H "Authorization: Bearer ${TOKEN}" ${INTEL_URL}/api/v1/resultados/comparativo | python3 -m json.tool

# Status coleta
curl -s -H "Authorization: Bearer ${TOKEN}" ${INTEL_URL}/api/v1/coleta/status | python3 -m json.tool
```

## Scheduler — Coleta automatica trimestral

O Cloud Scheduler dispara coleta no dia 15 de janeiro, abril, julho e outubro
as 9h (horario de Brasilia), ~2 semanas apos o fechamento do trimestre,
quando os releases ja estao publicados.

Cron: `0 9 15 1,4,7,10 *`

## Integracao com Painel Admin

A VM `smo-analise-vm` (34.151.247.17) roda o painel admin que consome esta API.

Requisitos:
1. Variavel `INTELLIGENCE_API_URL` configurada no `.env` do painel
2. Service account da VM com `roles/run.invoker` no Cloud Run
3. Arquivos de referencia em `docs/painel_integration/`

## Estrutura do projeto

```
smo-intelligence/
├── app/
│   ├── api/v1/          # Rotas FastAPI
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Logica de negocio
│   ├── config.py        # Configuracao (env-aware)
│   ├── database.py      # Engine + session
│   └── main.py          # FastAPI app + CORS
├── migrations/          # Alembic migrations
├── scripts/
│   └── seed_db.py       # Seed com dados extraidos
├── docs/
│   ├── extracted/       # 24 JSONs com metricas
│   ├── painel_integration/  # Referencia para smo-admin-panel
│   ├── INVENTARIO.md    # 87 documentos catalogados
│   └── COBERTURA.md     # 190/288 metricas (66%)
├── Dockerfile           # Imagem producao (port 8080)
├── cloudbuild.yaml      # Pipeline CI/CD
├── requirements.txt     # Dependencias Python
└── DEPLOY.md            # Este arquivo
```
