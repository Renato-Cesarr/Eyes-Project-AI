# Relatórios rastreáveis da CI — REN-40

A pipeline existente conserva uv/Python fixados, lint, aquisição com hash,
contrato executável e testes. Adiciona JUnit e relatório com commit real,
contratos/lock hashados, smoke do EfficientDet-Lite0 e medição sintética no
host de build. Não treina modelo e não usa dados pessoais ou corpus físico.

Em checkout limpo, Python 3.11/uv 0.12.5:

```powershell
uv sync --locked --no-build --all-groups
uv run --locked --no-build ruff check .
uv run --locked --no-build python -m eyes_project_ai.acquire_model
uv run --locked --no-build pytest --junitxml=artifacts/ci/tests.xml
uv run --locked --no-build python -m eyes_project_ai.ci_report
```

A CI exige lock também em cada uv run e impede execução de builds de dependências.
A CLI valida hash/labels/tensores, executa smoke real com LiteRT 2.2.0, depois
3 warmups e 20 invocações com tensor RGB preto 320×320, quatro threads. Guarda
amostras, p50/p95 de inferência e ambiente. O relatório recusa checkout sujo,
fonte mudada durante a medição e arquivo de output já existente. Para nova
execução usar --output com caminho novo, de preferência em artifacts/.

O tempo corresponde exclusivamente a invoke no host. Não mede pré-processamento,
câmera, Android, TTS, bateria, detecção em sala ou métricas de precisão/recall.
Não aplicar os gates físicos a estes 20 valores. O relatório marca explicitamente
physical_device_executed=false e scientific_acceptance=false; REN-34/35/37/69
continuam responsáveis pelas evidências experimentais. Resultado do CI não
aprova automaticamente a experiência assistiva do produto.

Após todos os passos passarem, upload-artifact fixado por SHA guarda
artifacts/ci, com nome eyes-ai-checks-CHECKOUT_SHA-RUN_ATTEMPT por 14 dias.
tests.xml identifica os casos; model-smoke-host-benchmark.json identifica o
commit, modelo, runtime e entradas. Em PR o checkout pode ser merge sintético.

```powershell
gh run download RUN_ID --repo Renato-Cesarr/Eyes-Project-AI --name NOME_ARTIFACT --dir PASTA_NOVA
```

Conferir commit e hash do modelo com o pacote Mobile e incluir hashes destes
relatórios no manifesto conjunto da REN-74. Não versionar modelos, outputs ou
segredos. Não confundir artifacts temporários com release publicada, nem
reprodutibilidade do procedimento com amostras de latência idênticas.
