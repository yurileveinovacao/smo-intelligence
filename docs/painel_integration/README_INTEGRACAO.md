# Integracao Painel Admin ↔ SMO Intelligence

## Visao Geral

Estes arquivos sao **referencias** para integrar o painel admin (smo-admin-panel)
com a API do SMO Intelligence rodando no Cloud Run.

## Arquivos para copiar no smo-admin-panel

```
app/services/intelligence_client.py   → Cliente HTTP que chama a API
app/api/inteligencia.py               → Rotas do painel (dashboard, comparativo)
```

## Configuracao necessaria

### 1. Variavel de ambiente na VM

```bash
# No .env da VM smo-analise-vm:
INTELLIGENCE_API_URL=https://smo-intelligence-xxxx-rj.a.run.app
```

Substituir `xxxx` pela URL real gerada pelo Cloud Run.

### 2. Autenticacao VM → Cloud Run

A autenticacao usa **Identity Token** do Compute Engine metadata server.
A VM precisa ter o papel `roles/run.invoker` no servico Cloud Run:

```bash
gcloud run services add-iam-policy-binding smo-intelligence \
    --region=southamerica-east1 \
    --member="serviceAccount:SERVICE_ACCOUNT_DA_VM" \
    --role="roles/run.invoker"
```

### 3. Registrar rotas no painel

No router principal do smo-admin-panel:

```python
from app.api.inteligencia import router as inteligencia_router
app.include_router(inteligencia_router)
```

### 4. Dependencia necessaria

Adicionar ao `requirements.txt` do painel:

```
httpx>=0.27
```

## Endpoints disponíveis na API SMO Intelligence

| Metodo | Caminho                              | Descricao                        |
|--------|--------------------------------------|----------------------------------|
| GET    | /api/v1/resultados                   | Todos os resultados (filtros)    |
| GET    | /api/v1/resultados/concorrentes-rp   | Concorrentes de Ribeirao Preto   |
| GET    | /api/v1/resultados/comparativo       | Serie historica por shopping     |
| GET    | /api/v1/coleta/status                | Status do ultimo ciclo de coleta |
| POST   | /api/v1/coleta/disparar              | Dispara nova coleta              |
| GET    | /api/v1/grupos                       | Lista grupos economicos          |
| GET    | /api/v1/shoppings                    | Lista shoppings monitorados      |
